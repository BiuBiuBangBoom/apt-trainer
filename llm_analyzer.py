import json
import os
import random
import urllib.request

from analyzer import Weakness, CrossWeakness
from data_store import Record
from mode import Question, question_type_for_name

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
你是一个数学能力分析专家，擅长从练习数据中发现细微的数字敏感度规律。

你会收到用户的规则分析结果和抽样练习记录。请：
1. 验证规则分析的发现是否合理（judgment: "confirmed"/"questionable"/"false_positive"）
2. 补充规则分析可能遗漏的规律（如特定的数字组合、顺序效应等）
3. 给出具体的训练建议（中文，简洁实用）

注意：补充发现的规律需要用 suggested_features 表达，其中只能使用下文列出的可用特征维度名称，
不能自创特征名。suggested_features 是一个 dict，可以包含多个特征约束（它们之间是 AND 关系）。

只返回 JSON，不要任何其他文字。"""


def _build_feature_catalog() -> str:
    """Build a catalog of available feature dimensions per question type."""
    from mode import MODE_REGISTRY
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

    # Let the user know the prompt size
    prompt_bytes = len(prompt.encode("utf-8"))
    print(f"\n  DeepSeek 模型: {_load_model()}")
    print(f"  Prompt 大小: {prompt_bytes} 字节 (~{prompt_bytes // 4} tokens)")

    body = json.dumps({
        "model": _load_model(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "stream": False,
        "thinking": {"type": "disabled"},
    }).encode("utf-8")

    req = urllib.request.Request(DEEPSEEK_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    print("  正在连接 API...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"  已连接, 状态码: {resp.status}, 正在读取响应...")
            raw = bytearray()
            chunk_size = 4096
            last_report = 0
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) - last_report >= 8192:
                    print(f"  已接收: {len(raw)} 字节...")
                    last_report = len(raw)
            print(f"  响应接收完成, 共 {len(raw)} 字节")
            result = json.loads(raw)
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

    content = result["choices"][0]["message"]["content"]
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
      "type_name": "...",
      "feature_name": "...",
      "feature_value": "...",
      "judgment": "confirmed|questionable|false_positive",
      "comment": "简短评语"
    }
  ],
  "additional_findings": [
    {
      "description": "发现的规律描述（中文）",
      "type_name": "该规律对应的题型名称（必须与上方数据统计中的题型名完全一致）",
      "suggested_features": {"特征名1": "特征值1", "特征名2": "特征值2"}
    }
  ],
  "training_suggestions": "训练建议（中文，简洁实用，不超过200字）"
}

注意：suggested_features 中的 key 必须来自上方"可用特征维度"中列出的特征名，
value 必须是该特征可能的取值。可以包含多个特征约束（AND 关系）。
如果规律不便于用现有特征表达，可以省略 suggested_features。""")

    return "\n".join(parts)
