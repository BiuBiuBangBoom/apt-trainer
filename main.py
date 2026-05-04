#!/usr/bin/env python3
"""Administrative Aptitude Test Assistant — mental math training tool."""

import os
import sys
from typing import Optional

from config import Config
from context import Context
from data_store import DataStore, Record
from mode import (
    MODE_REGISTRY,
    Question,
    create_question_type,
    question_type_for_name,
)
from strategy import ExamMode, PracticeAndTestMode, PracticeMode
from analyzer import WeaknessAnalyzer, Weakness, CrossWeakness
from llm_analyzer import analyze_with_llm, _load_api_key
from common import (
    bold, dim,
    c_header, c_success, c_error, c_warning, c_accent, c_info, c_border, c_dim,
    box_top, box_bottom, box_sep, box_line,
    colored_accuracy, fmt_time_ms,
    wrap_text,
    ARROW, WIDTH,
)


def parse_args() -> Config:
    config = Config()
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "-n" and i + 1 < len(args):
            config.max_questions = int(args[i + 1])
            i += 2
        elif args[i] == "-t" and i + 1 < len(args):
            config.time_limit_seconds = int(args[i + 1])
            i += 2
        else:
            i += 1
    return config


# ---- Menu functions ----

def print_welcome() -> None:
    print()
    print(box_top("APT 心算训练助手"))
    print(box_line("行政能力测验 — 心算练习工具", align="center"))
    print(box_bottom())


def print_main_menu() -> None:
    print()
    print(box_top("主 菜 单"))
    print(box_line(""))
    print(box_line(f"{bold('[1]')}  练习模式      {dim('边练边看答案')}"))
    print(box_line(f"{bold('[2]')}  练习测验      {dim('每题即时判断对错')}"))
    print(box_line(f"{bold('[3]')}  考试模式      {dim('结束统一出分')}"))
    print(box_line(""))
    print(box_sep())
    print(box_line(""))
    print(box_line(f"{bold('[0]')}  历史统计      {dim('查看历史练习数据')}"))
    print(box_line(f"{bold('[R]')}  错题回顾      {dim('重新练习所有错题')}"))
    print(box_line(f"{bold('[W]')}  智能薄弱分析  {dim('发现弱点并针对性训练')}"))
    print(box_line(""))
    print(box_sep())
    print(box_line(f"{bold('[Q]')}  退出程序"))
    print(box_bottom())


def print_calculation_menu() -> None:
    print()
    print(box_top("题 型 选 择"))
    print(box_line(""))
    for num in sorted(MODE_REGISTRY):
        _, display = MODE_REGISTRY[num]
        name = display.split(":")[0].strip()
        example = display.split(":")[-1].strip() if ":" in display else ""
        line = f"{bold(f'[{num:>2}]')}  {name}"
        if example:
            line += f"  {dim(f'(例: {example})')}"
        print(box_line(line))
    print(box_line(""))
    print(box_sep())
    print(box_line(f"{bold('[ 0]')}  返回主菜单"))
    print(box_bottom())


# ---- Feature screens ----

def show_stats(data_store: DataStore) -> None:
    stats = data_store.get_type_stats()
    if not stats:
        print()
        print(box_top("暂无历史记录"))
        print(box_line("还没有任何练习记录", align="center"))
        print(box_bottom())
        return

    print()
    print(box_top("历 史 统 计"))
    print(box_sep())

    for s in stats:
        acc_str = colored_accuracy(s.accuracy)
        time_str = fmt_time_ms(int(s.avg_time_ms))
        print(box_line(""))
        print(box_line(f"{bold('题型:')} {s.type_name}"))
        print(box_line(
            f"    练习次数: {s.total_count:<6}  "
            f"正确率: {acc_str}  "
            f"平均耗时: {time_str}"))
        print(box_line(""))

    print(box_bottom())

    inp = input(f"\n  {c_accent(ARROW)} 输入 C 清空全部记录，或按回车返回: ").strip()
    if inp.upper() == "C":
        confirm = input(f"  {c_warning('确认清空全部记录？(y/N):')} ").strip()
        if confirm.upper() == "Y":
            data_store.clear_all()
            print(f"  {c_success('记录已清空')}")


def do_review(data_store: DataStore) -> None:
    wrong = data_store.get_wrong_records()
    if not wrong:
        print(f"\n  {c_success('没有错题记录！')}")
        return

    type_names: list[str] = []
    grouped: list[list[Record]] = []
    for r in wrong:
        if r.type_name in type_names:
            idx = type_names.index(r.type_name)
            grouped[idx].append(r)
        else:
            type_names.append(r.type_name)
            grouped.append([r])

    print()
    print(box_top("错 题 回 顾"))
    print(box_line(""))
    print(box_line(f"{bold('错题分布:')}"))
    for i, (tn, g) in enumerate(zip(type_names, grouped), 1):
        print(box_line(f"  {bold(f'[{i}]')}  {tn}  ({len(g)} 题)"))
    print(box_line(f"  {bold('[0]')}  全部回顾 ({len(wrong)} 题)"))
    print(box_line(""))
    print(box_bottom())

    inp = input(f"  {c_accent(ARROW)} 请选择 [输入 Q 返回]: ").strip()
    if inp.upper() == "Q":
        return

    try:
        sel = int(inp)
    except ValueError:
        print(f"  {c_error('无效选择')}")
        return

    if sel == 0:
        to_review = wrong
    elif 1 <= sel <= len(grouped):
        to_review = grouped[sel - 1]
    else:
        print(f"  {c_error('无效选择')}")
        return

    if not to_review:
        return

    qt = question_type_for_name(to_review[0].type_name)
    if qt is None:
        return

    questions = [Question(text=r.question, answer=r.answer) for r in to_review]
    review_config = Config(max_questions=len(to_review))

    ctx = Context(review_config, None)
    ctx.set_strategy(PracticeAndTestMode())
    assert ctx.strategy is not None
    ctx.strategy.set_question_type(qt)
    ctx.strategy.set_preloaded(questions)
    ctx.execute_strategy()


# ---- Smart training helpers ----

def _llm_analyze(
    type_weaknesses: list[Weakness],
    cross_weaknesses: list[CrossWeakness],
    records: list[Record],
) -> tuple[list[dict], list[dict], str]:
    llm_display: list[dict] = []
    llm_trainable: list[dict] = []
    llm_suggestions = ""
    if not _load_api_key():
        return llm_display, llm_trainable, llm_suggestions

    print(f"\n  {c_dim('正在调用 DeepSeek 进行深度分析...')}")
    try:
        llm_result = analyze_with_llm(type_weaknesses, cross_weaknesses, records)
        for v in llm_result.get("rule_validation", []):
            if v.get("judgment") == "confirmed":
                llm_display.append({
                    "description": v.get("comment", ""),
                    "scope": f"{v.get('type_name', '')} - {v.get('feature_name', '')}={v.get('feature_value', '')}",
                })
        for f in llm_result.get("additional_findings", []):
            desc = f.get("description", "")
            tn = f.get("type_name", "")
            sfs = f.get("suggested_features")
            llm_display.append({"description": desc, "scope": tn})
            if sfs and isinstance(sfs, dict) and len(sfs) > 0 and tn:
                llm_trainable.append({
                    "type_name": tn,
                    "features": sfs,
                    "description": desc,
                })
        llm_suggestions = llm_result.get("training_suggestions", "")
    except Exception as e:
        print(f"  {c_error(f'DeepSeek 分析失败: {e}')}")
    return llm_display, llm_trainable, llm_suggestions


def _render_weakness_report(
    type_weaknesses: list[Weakness],
    cross_weaknesses: list[CrossWeakness],
    llm_display: list[dict],
    llm_trainable: list[dict],
    llm_suggestions: str,
) -> tuple[int, int] | None:
    has_content = bool(type_weaknesses) or bool(cross_weaknesses) or bool(llm_display) or bool(llm_suggestions)
    if not has_content:
        print(f"\n  {c_success('未发现明显薄弱项（数据不足或表现均衡）')}")
        return None

    print()
    print(box_top("智能薄弱分析报告"))
    print(box_sep())

    idx = 0
    if type_weaknesses:
        print(box_line(""))
        print(box_line("规则发现 — 题型专项弱点", align="center"))
        for i, w in enumerate(type_weaknesses, 1):
            idx = i
            acc_str = colored_accuracy(w.accuracy)
            time_str = fmt_time_ms(int(w.avg_time_ms))
            base_acc_str = colored_accuracy(w.baseline_accuracy)
            base_time_str = fmt_time_ms(int(w.baseline_time_ms))
            print(box_line(""))
            print(box_line(
                f"  {bold(f'[{i}]')}  {w.type_name}  {w.feature_name}={bold(w.feature_value)}"))
            print(box_line(
                f"      正确率: {acc_str} / 均值 {base_acc_str}"))
            print(box_line(
                f"      耗时: {time_str} / 均值 {base_time_str}  样本 {w.total_count}题"))

    type_weakness_count = idx

    if cross_weaknesses:
        print(box_line(""))
        print(box_sep())
        print(box_line(""))
        print(box_line("跨题型弱点", align="center"))
        for w in cross_weaknesses:
            idx += 1
            acc_str = colored_accuracy(w.accuracy)
            time_str = fmt_time_ms(int(w.avg_time_ms))
            print(box_line(""))
            print(box_line(
                f"  {bold(f'[{idx}]')}  数字 {bold(w.feature_value)} 敏感度低"))
            print(box_line(
                f"      正确率: {acc_str}  耗时: {time_str}  样本 {w.total_count}题"))
            types_str = ', '.join(w.affected_types)
            for line in wrap_text(f"      涉及: {types_str}", 44):
                print(box_line(line))

    cross_weakness_count = idx - type_weakness_count

    if llm_trainable:
        print(box_line(""))
        print(box_sep())
        print(box_line(""))
        print(box_line("AI 发现 — 可训练项目", align="center"))
        for lt in llm_trainable:
            idx += 1
            feats_str = ', '.join(f"{k}={v}" for k, v in lt["features"].items())
            print(box_line(""))
            print(box_line(
                f"  {bold(f'[{idx}]')}  {lt['type_name']}  {feats_str}"))
            for line in wrap_text(f"      {lt['description']}", 44):
                print(box_line(line))

    if llm_display:
        print(box_line(""))
        print(box_sep())
        print(box_line(""))
        print(box_line("AI 深度分析", align="center"))
        for f in llm_display:
            print(box_line(""))
            for line in wrap_text(f["description"], 44):
                print(box_line(f"  {line}"))
            if f.get("scope"):
                for line in wrap_text(dim('范围: ' + f["scope"]), 44):
                    print(box_line(f"  {line}"))
    if llm_suggestions:
        print(box_line(""))
        print(box_line("训练建议"))
        for line in wrap_text(llm_suggestions, 44):
            print(box_line(f"  {line}"))

    print(box_line(""))
    print(box_sep())
    if type_weaknesses or llm_trainable:
        print(box_line(f"  {bold('[0]')}  全部训练"))
    print(box_line(f"  {bold('[Q]')}  返回主菜单"))
    print(box_bottom())

    return (type_weakness_count, cross_weakness_count)


def _parse_smart_selection(
    inp: str,
    type_weaknesses: list[Weakness],
    report_meta: tuple[int, int],
    llm_trainable: list[dict],
) -> list[tuple[str, dict[str, str]]] | None:
    try:
        sel = int(inp)
    except ValueError:
        return None

    type_weakness_count, cross_weakness_count = report_meta
    train_items: list[tuple[str, dict[str, str]]] = []

    if sel == 0:
        for w in type_weaknesses:
            train_items.append((w.type_name, {w.feature_name: w.feature_value}))
        for lt in llm_trainable:
            train_items.append((lt["type_name"], lt["features"]))
    elif 1 <= sel <= type_weakness_count:
        w = type_weaknesses[sel - 1]
        train_items.append((w.type_name, {w.feature_name: w.feature_value}))
    else:
        llm_start = type_weakness_count + cross_weakness_count + 1
        lt_idx = sel - llm_start
        if 0 <= lt_idx < len(llm_trainable):
            lt = llm_trainable[lt_idx]
            train_items.append((lt["type_name"], lt["features"]))
        else:
            return None

    return train_items if train_items else None


def _run_targeted_training(
    train_items: list[tuple[str, dict[str, str]]],
    data_store: DataStore,
) -> None:
    train_config = Config(max_questions=20)
    for type_name, features in train_items:
        qt = question_type_for_name(type_name)
        if qt is None:
            continue

        feats_label = ', '.join(f"{k}={v}" for k, v in features.items())
        print()
        print(box_top(f"针对性训练: {type_name}"))
        print(box_line(f"{feats_label}", align="center"))
        print(box_line(f"共 {train_config.max_questions} 题", align="center"))
        print(box_bottom())

        questions: list[Question] = []
        for _ in range(train_config.max_questions):
            q = qt.generate_question_with_features(features)
            questions.append(q)

        ctx = Context(train_config, data_store)
        ctx.set_strategy(PracticeAndTestMode())
        assert ctx.strategy is not None
        ctx.strategy.set_question_type(qt)
        ctx.strategy.set_preloaded(questions)
        ctx.execute_strategy()


def do_smart_training(data_store: DataStore) -> None:
    records = data_store.get_all_records()
    if not records:
        print(f"\n  {c_success('暂无练习记录')}")
        return

    analyzer = WeaknessAnalyzer(records, min_samples=3)
    type_weaknesses = analyzer.analyze()
    cross_weaknesses = analyzer.analyze_cross()

    llm_display, llm_trainable, llm_suggestions = _llm_analyze(
        type_weaknesses, cross_weaknesses, records)

    report_meta = _render_weakness_report(
        type_weaknesses, cross_weaknesses, llm_display, llm_trainable, llm_suggestions)
    if report_meta is None:
        return

    inp = input(f"  {c_accent(ARROW)} 请选择: ").strip()
    if inp.upper() == "Q":
        return

    train_items = _parse_smart_selection(inp, type_weaknesses, report_meta, llm_trainable)
    if train_items is None:
        print(f"  {c_error('无效选择')}")
        return

    _run_targeted_training(train_items, data_store)


# ---- Main loop helpers ----

def _run_strategy_session(ctx: Context) -> None:
    while True:
        print_calculation_menu()
        sub = input(f"  {c_accent(ARROW)} 请选择题型 [1-10, 0/Q 返回]: ").strip()

        if sub == "0" or sub.upper() == "Q" or sub.lower() == "quit":
            break

        try:
            sel = int(sub)
        except ValueError:
            print(f"  {c_error('无效选择')}")
            continue

        qt = create_question_type(sel)
        if qt is None:
            print(f"  {c_error('无效选择')}")
            continue

        assert ctx.strategy is not None
        ctx.strategy.set_question_type(qt)
        ctx.execute_strategy()


def process(config: Config, data_store: DataStore) -> None:
    print_welcome()

    while True:
        print_main_menu()
        inp = input(f"  {c_accent(ARROW)} 请选择: ").strip()

        if inp.upper() == "Q" or inp.lower() == "quit":
            print(f"\n  {c_info('感谢使用，再见！')}\n")
            break

        if inp == "0":
            show_stats(data_store)
            continue

        if inp.upper() == "R":
            do_review(data_store)
            continue

        if inp.upper() == "W":
            do_smart_training(data_store)
            continue

        ctx = Context(config, data_store)

        if inp == "1":
            ctx.set_strategy(PracticeMode())
        elif inp == "2":
            ctx.set_strategy(PracticeAndTestMode())
        elif inp == "3":
            ctx.set_strategy(ExamMode())
        else:
            print(f"  {c_error('无效选择')}")
            continue

        _run_strategy_session(ctx)


def main() -> None:
    config = parse_args()
    data_store = DataStore("data/records.tsv")

    if config.max_questions > 0 or config.time_limit_seconds > 0:
        print()
        parts = []
        if config.max_questions > 0:
            parts.append(f"题目数: {config.max_questions}")
        if config.time_limit_seconds > 0:
            parts.append(f"时限: {config.time_limit_seconds}s")
        print(f"  {c_dim(' | '.join(parts))}")


    process(config, data_store)


if __name__ == "__main__":
    main()
