#!/usr/bin/env python3
"""Administrative Aptitude Test Assistant — mental math training tool."""

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
from common import (
    bold, dim,
    c_header, c_success, c_error, c_warning, c_accent, c_info, c_border, c_dim,
    box_top, box_bottom, box_sep, box_line,
    colored_accuracy, fmt_time_ms,
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
    print(box_line(f"{bold('[W]')}  薄弱训练      {dim('针对性强化薄弱题型')}"))
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


def do_weak_training(data_store: DataStore) -> None:
    stats = data_store.get_type_stats()
    weak = [s for s in stats if s.accuracy < 0.7 and s.total_count >= 5]

    if not weak:
        print(f"\n  {c_success('暂无薄弱题型（正确率均 >= 70% 或练习次数不足）')}")
        return

    print()
    print(box_top("薄 弱 训 练"))
    print(box_line(""))
    for i, s in enumerate(weak, 1):
        acc = colored_accuracy(s.accuracy)
        print(box_line(
            f"  {bold(f'[{i}]')}  {s.type_name}  "
            f"正确率: {acc}  ({s.total_count} 次)"))
    print(box_line(f"  {bold('[0]')}  全部训练"))
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
        to_train = weak
    elif 1 <= sel <= len(weak):
        to_train = [weak[sel - 1]]
    else:
        print(f"  {c_error('无效选择')}")
        return

    train_config = Config(max_questions=30)

    for ts in to_train:
        qt = question_type_for_name(ts.type_name)
        if qt is None:
            continue

        print()
        print(box_top(f"开始训练: {ts.type_name}"))
        print(box_line(f"共 {train_config.max_questions} 题", align="center"))
        print(box_bottom())

        ctx = Context(train_config, data_store)
        ctx.set_strategy(PracticeAndTestMode())
        assert ctx.strategy is not None
        ctx.strategy.set_question_type(qt)
        ctx.execute_strategy()


# ---- Main loop ----

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
            do_weak_training(data_store)
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
