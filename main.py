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
from common import green_str, cyan_str, red_str, yellow_str


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


def print_calculation_menu() -> None:
    print("mode list:")
    for num in sorted(MODE_REGISTRY):
        _, display = MODE_REGISTRY[num]
        print(f"{num}.  {display}")


def show_stats(data_store: DataStore) -> None:
    """Show statistics, with option to reset."""
    stats = data_store.get_type_stats()
    if not stats:
        print(yellow_str("暂无历史记录"))
        return

    print(f"\n{cyan_str('========== 历史统计 ==========')}\n")

    for s in stats:
        if s.accuracy >= 0.85:
            color = "\033[32m"
        elif s.accuracy >= 0.7:
            color = "\033[33m"
        else:
            color = "\033[31m"

        print(f"题型: {s.type_name}")
        print(f"  练习次数: {s.total_count}")
        print(f"  正确率:   {color}{s.accuracy * 100:.1f}%\033[0m")
        print(f"  平均耗时: {s.avg_time_ms / 1000:.2f}s\n")

    print(f"{cyan_str('================================')}")

    inp = input("\n输入 C 清空全部记录，或按回车返回: ").strip()
    if inp.upper() == "C":
        confirm = input("确认清空全部记录？(y/N): ").strip()
        if confirm.upper() == "Y":
            data_store.clear_all()
            print(green_str("记录已清空"))


def do_review(data_store: DataStore) -> None:
    wrong = data_store.get_wrong_records()
    if not wrong:
        print(green_str("没有错题记录"))
        return

    # Group by type
    type_names: list[str] = []
    grouped: list[list[Record]] = []
    for r in wrong:
        if r.type_name in type_names:
            idx = type_names.index(r.type_name)
            grouped[idx].append(r)
        else:
            type_names.append(r.type_name)
            grouped.append([r])

    print("\n错题分布:")
    for i, (tn, g) in enumerate(zip(type_names, grouped), 1):
        print(f"{i}. {tn} ({len(g)} 题)")
    print("0. 全部回顾")

    inp = input("请选择 (输入 'quit' 返回): ").strip()
    if inp == "quit":
        return

    try:
        sel = int(inp)
    except ValueError:
        print("invalid selection")
        return

    if sel == 0:
        to_review = wrong
    elif 1 <= sel <= len(grouped):
        to_review = grouped[sel - 1]
    else:
        print("invalid selection")
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
    ctx.strategy.set_question_type(qt)
    ctx.strategy.set_preloaded(questions)
    ctx.execute_strategy()


def do_weak_training(data_store: DataStore) -> None:
    stats = data_store.get_type_stats()
    weak = [s for s in stats if s.accuracy < 0.7 and s.total_count >= 5]

    if not weak:
        print(green_str("暂无薄弱题型（正确率均 ≥70% 或练习次数不足）"))
        return

    print("\n薄弱题型:")
    for i, s in enumerate(weak, 1):
        print(f"{i}. {s.type_name} (正确率: {s.accuracy * 100:.1f}%, {s.total_count} 次练习)")
    print("0. 全部训练")

    inp = input("请选择 (输入 'quit' 返回): ").strip()
    if inp == "quit":
        return

    try:
        sel = int(inp)
    except ValueError:
        print("invalid selection")
        return

    if sel == 0:
        to_train = weak
    elif 1 <= sel <= len(weak):
        to_train = [weak[sel - 1]]
    else:
        print("invalid selection")
        return

    train_config = Config(max_questions=30)

    for ts in to_train:
        qt = question_type_for_name(ts.type_name)
        if qt is None:
            continue

        print(f"\n{cyan_str('>>> 开始训练: ')}{ts.type_name} ({train_config.max_questions} 题)")

        ctx = Context(train_config, data_store)
        ctx.set_strategy(PracticeAndTestMode())
        ctx.strategy.set_question_type(qt)
        ctx.execute_strategy()


def process(config: Config, data_store: DataStore) -> None:
    print("hello!")

    while True:
        print("\nmode list:")
        print("1. 跑图模式")
        print("2. 跑测模式")
        print("3. 测试模式")
        print("0. 查看历史统计")
        print("R. 错题回顾")
        print("W. 薄弱项专项训练")
        inp = input("please input mode (1 - 3 / 0 / R / W), or input 'quit' to exit: ").strip()

        if inp == "quit":
            print("Bye~")
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
            print("invalid mode")
            continue

        while True:
            print_calculation_menu()
            sub = input("please input mode (1 - 10), or input 'quit' to exit: ").strip()

            if sub == "quit":
                break

            try:
                sel = int(sub)
            except ValueError:
                print("invalid mode")
                continue

            qt = create_question_type(sel)
            if qt is None:
                print("invalid mode")
                continue

            assert ctx.strategy is not None
            ctx.strategy.set_question_type(qt)
            ctx.execute_strategy()


def main() -> None:
    config = parse_args()
    data_store = DataStore("records.tsv")

    if config.max_questions > 0:
        print(f"题目数量限制: {config.max_questions}")
    if config.time_limit_seconds > 0:
        print(f"每题时限: {config.time_limit_seconds}s")

    process(config, data_store)


if __name__ == "__main__":
    main()
