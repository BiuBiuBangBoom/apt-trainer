import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Question:
    text: str
    answer: str
    meta: dict = field(default_factory=dict)


class QuestionType(ABC):
    type_name: str = ""

    @abstractmethod
    def generate_question(self) -> Question:
        ...

    def check_answer(self, question: Question, response: str) -> bool:
        return response == question.answer


# ---- Concrete question types ----

class TwoDigitsTimesOneDigit(QuestionType):
    type_name = "两位数乘一位数"

    def generate_question(self) -> Question:
        a = random.randint(11, 99)
        b = random.randint(2, 9)
        return Question(text=f"{a} * {b}", answer=str(a * b))


class OneDigitPlusOneDigit(QuestionType):
    type_name = "一位数加一位数"

    def generate_question(self) -> Question:
        a = random.randint(2, 9)
        b = random.randint(11 - a, 9)
        return Question(text=f"{a} + {b}", answer=str(a + b))


class OneDigitTimesOneDigit(QuestionType):
    type_name = "一位数乘一位数"

    def generate_question(self) -> Question:
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        return Question(text=f"{a} * {b}", answer=str(a * b))


class ThreeDigitsDivideTwoDigits(QuestionType):
    type_name = "三位数除以两位数"

    def generate_question(self) -> Question:
        divisor = random.randint(10, 99)
        dividend = random.randint(100, 999)
        if divisor == 0:
            answer = "0"
        else:
            result = dividend / divisor
            answer = "0"
            for c in str(result):
                if c in "123456789":
                    answer = c
                    break
        return Question(text=f"{divisor} 厂 {dividend}", answer=answer)


class FractionCompare(QuestionType):
    type_name = "分数比较"

    def generate_question(self) -> Question:
        digits_gap_nd = random.randint(0, 2)
        digits_gap_frac = random.randint(0, 2)

        d1 = random.randint(10000, 100000)
        d2 = random.randint(10000, 100000)
        d2 //= 10 ** digits_gap_frac

        if digits_gap_nd == 0:
            n1 = random.randint(10000, d1 - 1)
            lo = 10000 // (10 ** digits_gap_frac)
            n2 = random.randint(lo, d2 - 1)
        else:
            n1 = random.randint(10000, 100000) // (10 ** digits_gap_nd)
            n2 = random.randint(10000, 100000) // (10 ** (digits_gap_nd + digits_gap_frac))

        r1 = n1 / d1
        r2 = n2 / d2
        if r1 > r2:
            symbol = ">"
        elif r1 < r2:
            symbol = "<"
        else:
            symbol = "="

        text = (
            f"{n1:<10}        {n2:<10}\n"
            f"{'------':<10}   ?   {'------':<10}\n"
            f"{d1:<10}        {d2:<10}"
        )
        answer = f"({symbol}) {r1} {symbol} {r2}"
        return Question(text=text, answer=answer)

    def check_answer(self, question: Question, response: str) -> bool:
        return len(response) > 0 and len(question.answer) > 1 and response[0] == question.answer[1]


class PercentageConvertToFraction(QuestionType):
    type_name = "最近百化分"

    def __init__(self) -> None:
        super().__init__()
        self._fractions: list[float] = [i / 2 for i in range(10, 41)]

    def generate_question(self) -> Question:
        percentage = random.randint(500, 2000) / 100.0
        target = 100 / percentage
        best = min(self._fractions, key=lambda x: abs(x - target))
        return Question(
            text=f"{percentage}%",
            answer=f"{best} true value: {target}",
        )

    def check_answer(self, question: Question, response: str) -> bool:
        try:
            user_val = float(response.split()[0])
            correct_val = float(question.answer.split()[0])
            return user_val == correct_val
        except (ValueError, IndexError):
            return False


class ThreeDigitsTimesOneDigit(QuestionType):
    type_name = "三位数乘一位数"

    def generate_question(self) -> Question:
        a = random.randint(100, 999)
        b = random.randint(2, 9)
        return Question(text=f"{a} * {b}", answer=str(a * b))


class EstimateGrowth(QuestionType):
    type_name = "现期增长率估算增长量"

    def __init__(self) -> None:
        super().__init__()
        self._threshold = 0.01

    def generate_question(self) -> Question:
        base = random.randint(1000, 100000)
        rate = random.randint(50, 100) / 10.0
        result = base / (1 + rate / 100) * (rate / 100)
        return Question(
            text=f"A: {base}  r: {rate:.2f}",
            answer=f"{result:.2f}",
            meta={"value": result},
        )

    def check_answer(self, question: Question, response: str) -> bool:
        try:
            resp = float(response)
        except ValueError:
            return False
        expected = question.meta["value"]
        error = abs(expected - resp) / expected if expected != 0 else 0
        print(f"error rate: {error * 100:.2f}%")
        return error <= self._threshold


class TwoDigitsSubOneDigit(QuestionType):
    type_name = "两位数减一位数"

    def generate_question(self) -> Question:
        a = random.randint(11, 18)
        b = random.randint(a - 9, 9)
        return Question(text=f"(){a % 10} - {b}", answer=str(a - b))


class PowerNumber(QuestionType):
    type_name = "幂次数"

    def generate_question(self) -> Question:
        base = random.randint(1, 19)
        exp = 3 if base < 10 else 2
        return Question(text=str(base ** exp), answer=f"{base} {exp}")


MODE_REGISTRY: dict[int, tuple[type[QuestionType], str]] = {
    1: (TwoDigitsTimesOneDigit, "两位数乘一位数 : 12 × 3"),
    2: (OneDigitPlusOneDigit, "一位数加一位数 : 8 + 7"),
    3: (OneDigitTimesOneDigit, "一位数乘一位数 : 7 × 8"),
    4: (ThreeDigitsDivideTwoDigits, "三位数除以两位数 : 123 ÷ 45"),
    5: (FractionCompare, "分数比较 : 1/2 ? 1/3"),
    6: (PercentageConvertToFraction, "最近百化分 : 12.5%"),
    7: (ThreeDigitsTimesOneDigit, "三位数乘一位数 : 123 × 7"),
    8: (EstimateGrowth, "估算增长量 : A=1234 r=5.6%"),
    9: (TwoDigitsSubOneDigit, "两位数减一位数 : 17 − 9"),
    10: (PowerNumber, "幂次数 : 256 = 4⁴"),
}


def create_question_type(selection: int) -> Optional[QuestionType]:
    entry = MODE_REGISTRY.get(selection)
    if entry is None:
        return None
    return entry[0]()


def question_type_for_name(type_name: str) -> Optional[QuestionType]:
    for cls, _ in MODE_REGISTRY.values():
        instance = cls()
        if instance.type_name == type_name:
            return instance
    return None
