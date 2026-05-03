# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Run

```bash
conda activate python313
python main.py            # normal run
python main.py -n 20      # limit to 20 questions
python main.py -t 30      # time limit 30s per question

python -m unittest test_all -v   # run tests
```

No external dependencies. Standard library only (Python 3.13).

## Architecture

This is an interactive terminal app for practicing rapid mental math (administrative aptitude test training). It was reconstructed from a C++ project at `../Administrative-Aptitude-Test-Assistant/`.

Uses the **Strategy pattern** with two levels of dispatch:

### Level 1 — Execution mode (how answers are evaluated)

`Context` holds an `ExamStrategy` (strategy.py). User picks one at startup:

- **PracticeMode** (`1`) — show answer after each question, no correctness check
- **PracticeAndTestMode** (`2`) — show answer + correct/wrong per question, summary stats on quit
- **ExamMode** (`3`) — no feedback until quit, then full summary with stats

### Level 2 — Calculation type (what kind of math)

Each `ExamStrategy` holds a `QuestionType` (mode.py). 10 calculation types:

| # | Class | Display |
|---|-------|---------|
| 1 | TwoDigitsTimesOneDigit | 两位数乘一位数 |
| 2 | OneDigitPlusOneDigit | 一位数加一位数 |
| 3 | OneDigitTimesOneDigit | 一位数乘一位数 |
| 4 | ThreeDigitsDivideTwoDigits | 三位数除以两位数 |
| 5 | FractionCompare | 分数比较 |
| 6 | PercentageConvertToFraction | 最近百化分 |
| 7 | ThreeDigitsTimesOneDigit | 三位数乘一位数 |
| 8 | EstimateGrowth | 现期增长率估算增长量 |
| 9 | TwoDigitsSubOneDigit | 两位数减一位数 |
| 10 | PowerNumber | 幂次数 |

### Data flow

1. `main.py` → `process()`: two-level menu (execution mode, then calculation type)
2. `QuestionType.generate_question()` returns a `Question` dataclass (text + answer + optional meta), no side effects
3. `Session` manages question generation and response recording via `Session.records: list[SessionRecord]`
4. User input via `ExamStrategy.process_input()`, which records response + timing into the session
5. `QuestionType.check_answer(question, response)` compares response to answer (FractionCompare checks only the symbol character, EstimateGrowth checks within 1% threshold)
6. `Session.print_statistics()` outputs per-question results and aggregate stats

### Key conventions

- `Question` dataclass bundles question text, answer, and optional metadata (e.g. `EstimateGrowth` stores full-precision value in `meta`)
- `Session` holds a single list of `SessionRecord` (question + response + timing), replacing the old parallel-list design
- `Session.save_records()` persists to `DataStore`
- For review mode: preload `Question` objects into `Session` via the `preloaded` parameter; `next_question()` returns `None` when exhausted
- `common.py` provides ANSI color helpers (`green_str`, `red_str`, `cyan_str`, etc.)
- `DataStore` persists records to `records.tsv` (tab-separated) with newline/tab escaping
- `MODE_REGISTRY` in `mode.py` is the single source of truth for mapping selection numbers to type classes and display names
- `question_type_for_name()` matches by exact `type_name` comparison (not prefix)
- When adding a new calculation type: subclass `QuestionType`, implement `generate_question()` → `Question`, optionally override `check_answer()`, and add an entry to `MODE_REGISTRY`

## Ground rules

- 遇到不确定的需求时，不要自己猜测和决定实现方案，必须先向用户确认。宁可多问一句，也不要自作主张加一个用户不需要的功能。
