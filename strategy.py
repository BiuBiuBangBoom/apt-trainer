import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from config import Config
from common import (
    RESET,
    bold, dim,
    c_header, c_success, c_error, c_warning, c_accent, c_info, c_border, c_dim,
    box_top, box_bottom, box_sep, box_line,
    fmt_time_ms, colored_time_ms, colored_accuracy,
    success_mark, failure_mark, progress_tag,
    CHECK, CLOCK, ARROW,
    WIDTH,
)
from data_store import DataStore, Record
from mode import Question, QuestionType


@dataclass
class SessionRecord:
    question: Question
    response: str
    cost_time_ms: int


class Session:
    def __init__(self, question_type: QuestionType, preloaded: list[Question] | None = None):
        self.question_type = question_type
        self.records: list[SessionRecord] = []
        self._gen = self._generator(preloaded)

    def _generator(self, preloaded):
        if preloaded is not None:
            yield from preloaded
            return
        while True:
            yield self.question_type.generate_question()

    def next_question(self) -> Question | None:
        try:
            return next(self._gen)
        except StopIteration:
            return None

    def record_response(self, question: Question, response: str, cost_ms: int) -> None:
        self.records.append(SessionRecord(question=question, response=response, cost_time_ms=cost_ms))

    def is_correct(self, index: int) -> bool:
        r = self.records[index]
        return self.question_type.check_answer(r.question, r.response)

    def save_records(self, ds: DataStore, type_name: str, mode_name: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for r in self.records:
            ds.save_record(Record(
                date=now,
                type_name=type_name,
                mode_name=mode_name,
                question=r.question.text,
                response=r.response,
                answer=r.question.answer,
                cost_time_ms=r.cost_time_ms,
                is_correct=self.question_type.check_answer(r.question, r.response),
            ))

    def print_statistics(self) -> None:
        if not self.records:
            return

        correct = sum(1 for i in range(len(self.records)) if self.is_correct(i))
        total = len(self.records)
        ratio = correct / total if total > 0 else 0
        avg_ms = sum(r.cost_time_ms for r in self.records) / total if total > 0 else 0

        print()
        print(box_top("答题详情"))
        print(box_sep())

        for i, r in enumerate(self.records, 1):
            is_c = self.question_type.check_answer(r.question, r.response)
            mark = success_mark() if is_c else failure_mark()
            time_str = colored_time_ms(r.cost_time_ms)

            q_text = r.question.text.split("\n")[0]
            if len(q_text) > 18:
                q_text = q_text[:17] + "…"

            print(box_line(""))
            print(box_line(f"#{i:02d}  {q_text}"))
            print(box_line(
                f"     你的: {c_accent(r.response):<6}  "
                f"答案: {bold(r.question.answer):<6}  "
                f"{c_info(CLOCK)} {time_str}  {mark}"))

        print(box_line(""))
        print(box_sep())
        print(box_top("成绩汇总"))
        print(box_sep())
        print(box_line(""))
        print(box_line(
            f"{c_success(f'正确: {correct}')}    "
            f"{c_error(f'错误: {total - correct}')}    "
            f"总计: {total}"))
        print(box_line(
            f"正确率: {colored_accuracy(ratio)}        "
            f"平均耗时: {fmt_time_ms(int(avg_ms))}"))
        print(box_line(""))
        print(box_bottom())


# ---- Question display helpers ----

def _print_question_frame_head(type_name: str, current: int, total: int) -> None:
    print()
    print(box_top(style="single"))
    print(box_line(
        f"{bold('题型:')} {type_name}    {c_accent(progress_tag(current, total))}",
        style="single"))
    print(box_sep(style="single"))


def _print_question_body(question_text: str) -> None:
    for line in question_text.split("\n"):
        print(box_line(line, align="center", style="single"))
    print(box_sep(style="single"))


def _print_result_line(answer: str, time_ms: int, is_correct: bool,
                       user_answer: str = "") -> None:
    print(box_line(
        f"{dim('正确答案:')} {bold(answer)}    {c_info(CLOCK)} {colored_time_ms(time_ms)}",
        style="single"))
    if is_correct:
        print(box_line(success_mark(), style="single"))
    else:
        print(box_line(failure_mark(user_answer), style="single"))
    print(box_bottom(style="single"))


# ---- Strategy classes ----

class ExamStrategy(ABC):
    def __init__(self) -> None:
        self._question_type: Optional[QuestionType] = None
        self._preloaded: list[Question] | None = None

    def set_question_type(self, qt: QuestionType) -> None:
        self._question_type = qt
        self._preloaded = None

    def set_preloaded(self, questions: list[Question]) -> None:
        self._preloaded = questions

    @abstractmethod
    def execute(self, config: Config, data_store: Optional[DataStore]) -> None:
        ...

    def process_input(self, session: Session, question: Question) -> bool:
        sys.stdout.write(f"{c_border('│')} {c_accent(ARROW)} 请输入答案: ")
        sys.stdout.flush()
        start = time.time()
        try:
            s = sys.stdin.readline()
        except EOFError:
            return False
        end = time.time()
        if not s:
            return False
        s = s.rstrip("\n").rstrip("\r")
        if s.lower() == "quit":
            return False
        cost_ms = int((end - start) * 1000)
        session.record_response(question, s, cost_ms)
        return True


class PracticeMode(ExamStrategy):
    def execute(self, config: Config, data_store: Optional[DataStore]) -> None:
        assert self._question_type is not None
        session = Session(self._question_type, preloaded=self._preloaded)
        index = 0
        total = config.max_questions
        while True:
            q = session.next_question()
            if q is None:
                break

            _print_question_frame_head(self._question_type.type_name, index + 1, total)
            _print_question_body(q.text)

            if not self.process_input(session, q):
                break

            print(box_line(
                f"{dim('正确答案:')} {bold(q.answer)}    "
                f"{c_info(CLOCK)} {colored_time_ms(session.records[-1].cost_time_ms)}",
                style="single"))
            print(box_bottom(style="single"))

            if 0 < total <= index + 1:
                break
            index += 1

        if data_store:
            session.save_records(data_store, self._question_type.type_name, "练习模式")


class PracticeAndTestMode(ExamStrategy):
    def execute(self, config: Config, data_store: Optional[DataStore]) -> None:
        assert self._question_type is not None
        session = Session(self._question_type, preloaded=self._preloaded)
        index = 0
        total = config.max_questions
        while True:
            q = session.next_question()
            if q is None:
                break

            _print_question_frame_head(self._question_type.type_name, index + 1, total)
            _print_question_body(q.text)

            if not self.process_input(session, q):
                break

            is_correct = session.is_correct(index)
            _print_result_line(
                q.answer,
                session.records[-1].cost_time_ms,
                is_correct,
                session.records[-1].response,
            )

            if 0 < total <= index + 1:
                break
            index += 1

        if data_store:
            session.save_records(data_store, self._question_type.type_name, "练习测验模式")
        session.print_statistics()


class ExamMode(ExamStrategy):
    def execute(self, config: Config, data_store: Optional[DataStore]) -> None:
        assert self._question_type is not None
        session = Session(self._question_type, preloaded=self._preloaded)
        index = 0
        total = config.max_questions
        while True:
            q = session.next_question()
            if q is None:
                break

            _print_question_frame_head(self._question_type.type_name, index + 1, total)
            _print_question_body(q.text)

            if not self.process_input(session, q):
                break

            print(box_bottom(style="single"))

            if 0 < total <= index + 1:
                break
            index += 1

        if data_store:
            session.save_records(data_store, self._question_type.type_name, "考试模式")
        session.print_statistics()
