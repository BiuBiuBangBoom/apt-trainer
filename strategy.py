import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from config import Config
from common import cyan_str, green_str, red_str
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
        correct = 0
        for i, r in enumerate(self.records):
            print("************************************")
            print(f"question {i + 1}")
            print(f"question:       {r.question.text}")
            print(f"your answer:    {r.response}")
            print(f"correct answer: {r.question.answer}")
            print(f"cost time:      {r.cost_time_ms / 1000:.3f}s")

            if self.question_type.check_answer(r.question, r.response):
                print(green_str("correct"))
                correct += 1
            else:
                print(red_str("wrong"))

        total = len(self.records)
        ratio = correct / total if total > 0 else 0
        avg_time = sum(r.cost_time_ms for r in self.records) / total / 1000 if total > 0 else 0

        print("-------------------------------------------")
        print(cyan_str("STATISTICS"))
        print(f"correct count:   {green_str(str(correct))}")
        print(f"wrong count:     {red_str(str(total - correct))}")
        print(f"total count:     {total}")
        print(f"correct ratio:   {ratio * 100:.2f}%")
        print(f"equal cost time: {avg_time:.3f}s")
        print("-------------------------------------------")


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
        start = time.time()
        try:
            s = input("input:")
        except EOFError:
            return False
        end = time.time()

        if s == "quit":
            return False

        cost_ms = int((end - start) * 1000)
        session.record_response(question, s, cost_ms)
        return True


class PracticeMode(ExamStrategy):
    def execute(self, config: Config, data_store: Optional[DataStore]) -> None:
        assert self._question_type is not None
        session = Session(self._question_type, preloaded=self._preloaded)
        index = 0
        while True:
            q = session.next_question()
            if q is None:
                break

            print("-------------------------------------------")
            print(f"question {index + 1}")
            print(q.text)

            if not self.process_input(session, q):
                break

            print(f"correct answer: {q.answer}")
            print(f"cost time:      {session.records[-1].cost_time_ms / 1000:.3f}s")

            if 0 < config.max_questions <= index + 1:
                break
            index += 1

        if data_store:
            session.save_records(data_store, self._question_type.type_name, "跑图模式")


class PracticeAndTestMode(ExamStrategy):
    def execute(self, config: Config, data_store: Optional[DataStore]) -> None:
        assert self._question_type is not None
        session = Session(self._question_type, preloaded=self._preloaded)
        index = 0
        while True:
            q = session.next_question()
            if q is None:
                break

            print("-------------------------------------------")
            print(f"question {index + 1}")
            print(q.text)

            if not self.process_input(session, q):
                break

            print(f"correct answer: {q.answer}")
            print(f"cost time:      {session.records[-1].cost_time_ms / 1000:.3f}s")

            if session.is_correct(index):
                print(green_str("correct"))
            else:
                print(red_str("wrong"))

            if 0 < config.max_questions <= index + 1:
                break
            index += 1

        if data_store:
            session.save_records(data_store, self._question_type.type_name, "跑测模式")
        session.print_statistics()


class ExamMode(ExamStrategy):
    def execute(self, config: Config, data_store: Optional[DataStore]) -> None:
        assert self._question_type is not None
        session = Session(self._question_type, preloaded=self._preloaded)
        index = 0
        while True:
            q = session.next_question()
            if q is None:
                break

            print(f"question {index + 1}")
            print(q.text)

            if not self.process_input(session, q):
                break

            print("-------------------------------------------")

            if 0 < config.max_questions <= index + 1:
                break
            index += 1

        if data_store:
            session.save_records(data_store, self._question_type.type_name, "测试模式")
        session.print_statistics()
