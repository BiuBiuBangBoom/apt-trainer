import json
import os
import random
import time
import urllib.request

from analyzer import Weakness, CrossWeakness
from data_store import Record
from mode import Question, question_type_for_name, MODE_REGISTRY

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_settings() -> dict:
    settings_path = os.path.join(_PROJECT_DIR, "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            return json.loads(f.read())
    return {}


def _load_api_key() -> str:
    key = _load_settings().get("api_key", "")
    if key:
        return key
    return os.environ.get("DEEPSEEK_API_KEY", "")


def _load_model() -> str:
    model = _load_settings().get("model", "")
    if model:
        return model
    return DEFAULT_MODEL


SYSTEM_PROMPT = """\
你是一个数学能力分析专家。你会收到一份完整的用户练习数据集（不是抽样）和基于该数据集的规则分析结果。

你的任务：
1. 快速验证规则分析的发现与数据是否一致，不要逐条重新计算——规则分析已做了统计，
   你只需判断这些发现在数据中是否明显成立。简单判断即可，不要纠结精确数字。
2. 从数据中找出 1-2 条规则分析可能遗漏的数字敏感度规律。
3. 给出 1-2 句简洁的训练建议（中文，不超过150字）。

重要约束：
- 下文列出的数据就是全部数据，不存在"更大的全量数据集"。不要猜测还有更多数据。
- suggested_features 只能使用下文"可用特征维度"中列出的特征名，值也必须是该特征的典型取值。
- 如果规律不便于用现有特征表达，可以省略 suggested_features。
- 保持简洁，不要在脑中展开长推理。这是结构化 JSON 生成任务，不是深度分析任务。

只返回 JSON，不要任何其他文字。"""


def _build_feature_catalog() -> str:
    """Build a catalog of available feature dimensions per question type."""
    lines = ["## 可用特征维度（suggested_features 只能使用以下特征名）\n"]
    for num in sorted(MODE_REGISTRY):
        cls, display = MODE_REGISTRY[num]
        qt = cls()
        # Generate a sample question to extract feature names
        q = qt.generate_question()
        feats = qt.extract_features(q)
        if not feats:
            continue
        lines.append(f"### {qt.type_name}")
        for fname, fval in feats.items():
            lines.append(f"- {fname}: 示例值 \"{fval}\"")
        lines.append("")
    return "\n".join(lines)


def _parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response, handling markdown fences and stray text."""
    content = content.strip()
    if not content:
        raise RuntimeError("LLM 返回了空响应")
    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    # Try to find JSON object boundaries
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        content = content[start:end + 1]
    return json.loads(content)


def analyze_with_llm(
    rule_weaknesses: list[Weakness],
    rule_cross: list[CrossWeakness],
    records: list[Record],
) -> dict:
    api_key = _load_api_key()
    if not api_key:
        return {"error": "API key not configured", "findings": [], "suggestions": ""}

    prompt = _build_prompt(rule_weaknesses, rule_cross, records)

    prompt_bytes = len(prompt.encode("utf-8"))
    model = _load_model()

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "stream": True,
        "reasoning_effort": "high",
        "thinking": {"type": "enabled"},
    }).encode("utf-8")

    req = urllib.request.Request(DEEPSEEK_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        resp = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"DeepSeek API 返回 {e.code} {e.reason}\n响应: {error_body}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"DeepSeek API 连接失败: {e.reason}\n"
            f"请检查网络连接和 API 端点: {DEEPSEEK_URL}"
        ) from e

    content = ""
    thinking_tokens = 0
    output_tokens = 0
    start_time = time.time()
    try:
        for line in resp:
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str or not line_str.startswith("data: "):
                continue
            data = line_str[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            msg_content = delta.get("content", "")
            reasoning = delta.get("reasoning_content", "")
            if reasoning:
                thinking_tokens += len(reasoning) // 2
            if msg_content:
                output_tokens += len(msg_content) // 2
                content += msg_content
            if reasoning or msg_content:
                elapsed = int(time.time() - start_time)
                status = f"  {elapsed}s  |  thinking: {thinking_tokens} tokens  |  output: {output_tokens} tokens"
                print(f"\r{status}\033[K", end="", flush=True)
    finally:
        resp.close()

    print()  # final newline
    if not content:
        raise RuntimeError("LLM 返回了空响应")

    return _parse_json_response(content)


def _build_prompt(
    rule_weaknesses: list[Weakness],
    rule_cross: list[CrossWeakness],
    records: list[Record],
) -> str:
    parts: list[str] = []

    # 0. Feature catalog
    parts.append(_build_feature_catalog())

    # 1. Data summary per type
    typed: dict[str, list[Record]] = {}
    for r in records:
        typed.setdefault(r.type_name, []).append(r)

    parts.append("## 数据统计\n")
    for tn, recs in typed.items():
        total = len(recs)
        correct = sum(1 for r in recs if r.is_correct)
        acc = correct / total * 100 if total > 0 else 0
        avg_ms = sum(r.cost_time_ms for r in recs) / total if total > 0 else 0
        parts.append(f"- {tn}: {total}题, 正确率 {acc:.1f}%, 平均耗时 {avg_ms:.0f}ms")

    # 2. Rule analysis findings
    parts.append("\n## 规则分析发现\n")
    if rule_weaknesses:
        for i, w in enumerate(rule_weaknesses, 1):
            parts.append(
                f"{i}. [{w.type_name}] {w.feature_name}={w.feature_value}  "
                f"正确率 {w.accuracy*100:.1f}% (题型均值 {w.baseline_accuracy*100:.1f}%)  "
                f"耗时 {w.avg_time_ms:.0f}ms (题型均值 {w.baseline_time_ms:.0f}ms)  "
                f"样本 {w.total_count}题")
    else:
        parts.append("（无发现）")

    if rule_cross:
        parts.append("\n### 跨题型弱点\n")
        for i, w in enumerate(rule_cross, 1):
            parts.append(
                f"{i}. 数字 {w.feature_value}: 正确率 {w.accuracy*100:.1f}%  "
                f"涉及: {', '.join(w.affected_types)}  "
                f"样本 {w.total_count}题")

    # 3. Sampled records
    parts.append("\n## 抽样原始数据\n")
    for tn, recs in typed.items():
        qt = question_type_for_name(tn)
        if qt is None:
            continue
        # Prioritize wrong and slow records
        wrong = [r for r in recs if not r.is_correct]
        slow = sorted([r for r in recs if r.is_correct],
                      key=lambda r: r.cost_time_ms, reverse=True)
        sampled = wrong + slow
        sample = sampled[:30]
        if len(sample) < 5:
            sample = recs[:30]

        parts.append(f"\n### {tn} (抽样{len(sample)}条)\n")
        parts.append("| 题目 | 用户答案 | 正确答案 | 耗时(ms) | 对/错 | 特征 |")
        parts.append("|------|---------|---------|----------|-------|------|")
        for r in sample:
            features_str = ""
            if r.meta_json:
                try:
                    meta = json.loads(r.meta_json)
                    q = Question(text=r.question, answer=r.answer, meta=meta)
                    feats = qt.extract_features(q)
                    features_str = ", ".join(f"{k}={v}" for k, v in feats.items())
                except (json.JSONDecodeError, TypeError):
                    pass
            mark = "对" if r.is_correct else "错"
            # Truncate long question text
            q_short = r.question.replace("\n", " ")[:30]
            parts.append(
                f"| {q_short} | {r.response} | {r.answer} | "
                f"{r.cost_time_ms} | {mark} | {features_str} |")

    parts.append("""
## 输出格式

请返回 JSON：
{
  "rule_validation": [
    {
      "type_name": "题型名",
      "feature_name": "特征名",
      "feature_value": "特征值",
      "judgment": "confirmed|questionable|false_positive",
      "comment": "一句话"
    },
    {
      "type_name": "跨题型",
      "feature_name": "数字敏感度",
      "feature_value": "7",
      "judgment": "confirmed|questionable|false_positive",
      "comment": "一句话"
    }
  ],
  "additional_findings": [
    {
      "description": "发现的规律描述（中文，简洁）",
      "type_name": "题型名",
      "suggested_features": {"特征名": "特征值"}
    }
  ],
  "training_suggestions": "训练建议（中文，不超过150字）"
}

注意：
- 跨题型弱点用 type_name="跨题型", feature_name="数字敏感度" 的格式
- 不要重新计算精确统计，判断是否"明显成立"即可
- suggested_features 可选，不便于表达时可以省略""")

    return "\n".join(parts)
