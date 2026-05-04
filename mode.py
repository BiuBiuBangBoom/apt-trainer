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

    def extract_features(self, question: Question) -> dict[str, str]:
        return {}

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        return {"involved_digits": []}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        if "involved_digits" in features:
            target = features["involved_digits"]
            for _ in range(200):
                q = self.generate_question()
                cross = self.extract_cross_features(q)
                if target in cross.get("involved_digits", []):
                    return q
        return self.generate_question()


# ---- Concrete question types ----

class TwoDigitsTimesOneDigit(QuestionType):
    type_name = "两位数乘一位数"

    def generate_question(self) -> Question:
        a = random.randint(11, 99)
        b = random.randint(2, 9)
        return Question(text=f"{a} * {b}", answer=str(a * b), meta={"a": a, "b": b})

    def extract_features(self, question: Question) -> dict[str, str]:
        a = question.meta["a"]
        b = question.meta["b"]
        ones_carry = 1 if (a % 10) * b >= 10 else 0
        tens_result = (a // 10) * b + ones_carry
        tens_carry = 1 if tens_result >= 10 else 0
        carries = ones_carry + tens_carry
        product = a * b
        return {
            "乘数": str(b),
            "进位次数": str(carries),
            "十位数": str(a // 10),
            "个位数": str(a % 10),
            "结果位数": str(len(str(product))),
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        a = question.meta["a"]
        b = question.meta["b"]
        return {"involved_digits": [str(a // 10), str(a % 10), str(b)]}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        b_target = features.get("乘数")
        carries_target = features.get("进位次数")
        tens_target = features.get("十位数")
        ones_target = features.get("个位数")
        digits_target = features.get("结果位数")
        has_local = any(k in features for k in
                        {"乘数", "进位次数", "十位数", "个位数", "结果位数"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            a = random.randint(11, 99)
            b = int(b_target) if b_target else random.randint(2, 9)
            if tens_target and str(a // 10) != tens_target:
                continue
            if ones_target and str(a % 10) != ones_target:
                continue
            q = Question(text=f"{a} * {b}", answer=str(a * b), meta={"a": a, "b": b})
            feats = self.extract_features(q)
            if carries_target and feats["进位次数"] != carries_target:
                continue
            if digits_target and feats["结果位数"] != digits_target:
                continue
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


class OneDigitPlusOneDigit(QuestionType):
    type_name = "一位数加一位数"

    def generate_question(self) -> Question:
        a = random.randint(2, 9)
        b = random.randint(11 - a, 9)
        return Question(text=f"{a} + {b}", answer=str(a + b), meta={"a": a, "b": b})

    def extract_features(self, question: Question) -> dict[str, str]:
        a = question.meta["a"]
        b = question.meta["b"]
        return {
            "加数": str(a),
            "被加数": str(b),
            "和的个位": str((a + b) % 10),
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        a = question.meta["a"]
        b = question.meta["b"]
        return {"involved_digits": [str(a), str(b)]}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        a_target = features.get("加数")
        b_target = features.get("被加数")
        sum_ones_target = features.get("和的个位")
        has_local = any(k in features for k in {"加数", "被加数", "和的个位"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            a = int(a_target) if a_target else random.randint(2, 9)
            if b_target:
                b = int(b_target)
                if a + b < 11:
                    continue
            else:
                b = random.randint(11 - a, 9)
            q = Question(text=f"{a} + {b}", answer=str(a + b), meta={"a": a, "b": b})
            feats = self.extract_features(q)
            if sum_ones_target and feats["和的个位"] != sum_ones_target:
                continue
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


class OneDigitTimesOneDigit(QuestionType):
    type_name = "一位数乘一位数"

    def generate_question(self) -> Question:
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        return Question(text=f"{a} * {b}", answer=str(a * b), meta={"a": a, "b": b})

    def extract_features(self, question: Question) -> dict[str, str]:
        a = question.meta["a"]
        b = question.meta["b"]
        return {
            "乘数": str(max(a, b)),
            "被乘数": str(min(a, b)),
            "积的位数": str(len(str(a * b))),
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        a = question.meta["a"]
        b = question.meta["b"]
        return {"involved_digits": [str(a), str(b)]}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        a_target = features.get("乘数")
        b_target = features.get("被乘数")
        digits_target = features.get("积的位数")
        has_local = any(k in features for k in {"乘数", "被乘数", "积的位数"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            big = max(a, b)
            small = min(a, b)
            if a_target and str(big) != a_target:
                continue
            if b_target and str(small) != b_target:
                continue
            q = Question(text=f"{a} * {b}", answer=str(a * b), meta={"a": a, "b": b})
            feats = self.extract_features(q)
            if digits_target and feats["积的位数"] != digits_target:
                continue
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


class ThreeDigitsDivideTwoDigits(QuestionType):
    type_name = "三位数除以两位数"

    def generate_question(self) -> Question:
        divisor = random.randint(10, 99)
        dividend = random.randint(100, 999)
        answer = self._quotient_first_digit(divisor, dividend)
        return Question(text=f"{divisor} 厂 {dividend}", answer=answer,
                        meta={"divisor": divisor, "dividend": dividend})

    def _quotient_first_digit(self, divisor: int, dividend: int) -> str:
        result = dividend / divisor
        for c in str(result):
            if c in "123456789":
                return c
        return "0"

    def extract_features(self, question: Question) -> dict[str, str]:
        d = question.meta["divisor"]
        dd = question.meta["dividend"]
        if d <= 29:
            dr = "10-29"
        elif d <= 59:
            dr = "30-59"
        else:
            dr = "60-99"
        if dd <= 399:
            ddr = "100-399"
        elif dd <= 699:
            ddr = "400-699"
        else:
            ddr = "700-999"
        return {
            "除数范围": dr,
            "商的首位": self._quotient_first_digit(d, dd),
            "被除数范围": ddr,
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        d = question.meta["divisor"]
        dd = question.meta["dividend"]
        digits = []
        for c in str(d):
            digits.append(c)
        for c in str(dd):
            digits.append(c)
        return {"involved_digits": digits}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        dr_target = features.get("除数范围")
        qd_target = features.get("商的首位")
        ddr_target = features.get("被除数范围")
        has_local = any(k in features for k in {"除数范围", "商的首位", "被除数范围"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            divisor = random.randint(10, 99)
            dividend = random.randint(100, 999)
            if dr_target:
                lo, hi = {"10-29": (10, 29), "30-59": (30, 59), "60-99": (60, 99)}[dr_target]
                divisor = random.randint(lo, hi)
            if ddr_target:
                lo, hi = {"100-399": (100, 399), "400-699": (400, 699), "700-999": (700, 999)}[ddr_target]
                dividend = random.randint(lo, hi)
            qd = self._quotient_first_digit(divisor, dividend)
            if qd_target and qd != qd_target:
                continue
            q = Question(text=f"{divisor} 厂 {dividend}", answer=qd,
                         meta={"divisor": divisor, "dividend": dividend})
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


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
        return Question(text=text, answer=answer,
                        meta={"n1": n1, "n2": n2, "d1": d1, "d2": d2, "symbol": symbol})

    def check_answer(self, question: Question, response: str) -> bool:
        return len(response) > 0 and len(question.answer) > 1 and response[0] == question.answer[1]

    def extract_features(self, question: Question) -> dict[str, str]:
        d1 = len(str(question.meta["d1"]))
        d2 = len(str(question.meta["d2"]))
        denom_gap = str(abs(d1 - d2))
        n1 = question.meta["n1"]
        n2 = question.meta["n2"]
        d1_val = question.meta["d1"]
        d2_val = question.meta["d2"]
        diff = abs(n1 / d1_val - n2 / d2_val)
        return {
            "分母位数差": denom_gap,
            "数值差距": "接近" if diff < 0.05 else "明显",
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        digits = []
        for key in ("n1", "n2", "d1", "d2"):
            for c in str(question.meta[key]):
                digits.append(c)
        return {"involved_digits": digits}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        denom_gap_target = features.get("分母位数差")
        gap_target = features.get("数值差距")
        has_local = any(k in features for k in {"分母位数差", "数值差距"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            q = self.generate_question()
            feats = self.extract_features(q)
            if denom_gap_target and feats["分母位数差"] != denom_gap_target:
                continue
            if gap_target and feats["数值差距"] != gap_target:
                continue
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


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
            meta={"percentage": percentage},
        )

    def check_answer(self, question: Question, response: str) -> bool:
        try:
            user_val = float(response.split()[0])
            correct_val = float(question.answer.split()[0])
            return user_val == correct_val
        except (ValueError, IndexError):
            return False

    def extract_features(self, question: Question) -> dict[str, str]:
        p = question.meta["percentage"]
        if p <= 9.9:
            pr = "5.0-9.9"
        elif p <= 14.9:
            pr = "10.0-14.9"
        else:
            pr = "15.0-20.0"
        return {"百分比范围": pr}

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        p = question.meta["percentage"]
        digits = [c for c in f"{p:.1f}" if c.isdigit()]
        return {"involved_digits": digits}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        pr_target = features.get("百分比范围")
        has_local = "百分比范围" in features
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            if pr_target == "5.0-9.9":
                p = random.randint(500, 990) / 100.0
            elif pr_target == "10.0-14.9":
                p = random.randint(1000, 1490) / 100.0
            else:
                p = random.randint(1500, 2000) / 100.0
            target = 100 / p
            best = min(self._fractions, key=lambda x: abs(x - target))
            q = Question(text=f"{p}%", answer=f"{best} true value: {target}",
                         meta={"percentage": p})
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


class ThreeDigitsTimesOneDigit(QuestionType):
    type_name = "三位数乘一位数"

    def generate_question(self) -> Question:
        a = random.randint(100, 999)
        b = random.randint(2, 9)
        return Question(text=f"{a} * {b}", answer=str(a * b), meta={"a": a, "b": b})

    def extract_features(self, question: Question) -> dict[str, str]:
        a = question.meta["a"]
        b = question.meta["b"]
        hundreds = a // 100
        tens = (a // 10) % 10
        ones = a % 10
        c1 = 1 if ones * b >= 10 else 0
        c2 = 1 if tens * b + c1 >= 10 else 0
        c3 = 1 if hundreds * b + c2 >= 10 else 0
        carries = c1 + c2 + c3
        product = a * b
        return {
            "乘数": str(b),
            "进位次数": str(carries),
            "百位数": str(hundreds),
            "结果位数": str(len(str(product))),
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        a = question.meta["a"]
        b = question.meta["b"]
        digits = [str(a // 100), str((a // 10) % 10), str(a % 10), str(b)]
        return {"involved_digits": digits}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        b_target = features.get("乘数")
        carries_target = features.get("进位次数")
        hundreds_target = features.get("百位数")
        digits_target = features.get("结果位数")
        has_local = any(k in features for k in
                        {"乘数", "进位次数", "百位数", "结果位数"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            a = random.randint(100, 999)
            b = int(b_target) if b_target else random.randint(2, 9)
            if hundreds_target and str(a // 100) != hundreds_target:
                continue
            q = Question(text=f"{a} * {b}", answer=str(a * b), meta={"a": a, "b": b})
            feats = self.extract_features(q)
            if carries_target and feats["进位次数"] != carries_target:
                continue
            if digits_target and feats["结果位数"] != digits_target:
                continue
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


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
            meta={"base": base, "rate": rate, "value": result},
        )

    def check_answer(self, question: Question, response: str) -> bool:
        try:
            resp = float(response)
        except ValueError:
            return False
        expected = question.meta["value"]
        error = abs(expected - resp) / expected if expected != 0 else 0
        return error <= self._threshold

    def extract_features(self, question: Question) -> dict[str, str]:
        base = question.meta["base"]
        rate = question.meta["rate"]
        if base < 10000:
            br = "1k-10k"
        elif base < 100000:
            br = "10k-100k"
        else:
            br = "100k+"
        if rate <= 6.9:
            rr = "5.0-6.9"
        elif rate <= 8.5:
            rr = "7.0-8.5"
        else:
            rr = "8.6-10.0"
        return {"基数范围": br, "增长率": rr}

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        base = question.meta["base"]
        rate = question.meta["rate"]
        digits = [c for c in str(base)]
        for c in f"{rate:.1f}":
            if c.isdigit():
                digits.append(c)
        return {"involved_digits": digits}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        br_target = features.get("基数范围")
        rr_target = features.get("增长率")
        has_local = any(k in features for k in {"基数范围", "增长率"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            if br_target == "1k-10k":
                base = random.randint(1000, 9999)
            elif br_target == "10k-100k":
                base = random.randint(10000, 99999)
            elif br_target == "100k+":
                base = random.randint(100000, 200000)
            else:
                base = random.randint(1000, 100000)
            if rr_target == "5.0-6.9":
                rate = random.randint(50, 69) / 10.0
            elif rr_target == "7.0-8.5":
                rate = random.randint(70, 85) / 10.0
            elif rr_target == "8.6-10.0":
                rate = random.randint(86, 100) / 10.0
            else:
                rate = random.randint(50, 100) / 10.0
            result = base / (1 + rate / 100) * (rate / 100)
            q = Question(text=f"A: {base}  r: {rate:.2f}",
                         answer=f"{result:.2f}",
                         meta={"base": base, "rate": rate, "value": result})
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


class TwoDigitsSubOneDigit(QuestionType):
    type_name = "两位数减一位数"

    def generate_question(self) -> Question:
        a = random.randint(11, 18)
        b = random.randint(a - 9, 9)
        return Question(text=f"(){a % 10} - {b}", answer=str(a - b),
                        meta={"a": a, "b": b})

    def extract_features(self, question: Question) -> dict[str, str]:
        a = question.meta["a"]
        b = question.meta["b"]
        return {
            "个位数": str(a % 10),
            "减数": str(b),
            "是否退位": "是" if (a % 10) < b else "否",
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        a = question.meta["a"]
        b = question.meta["b"]
        return {"involved_digits": [str(a // 10), str(a % 10), str(b)]}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        ones_target = features.get("个位数")
        b_target = features.get("减数")
        borrow_target = features.get("是否退位")
        has_local = any(k in features for k in {"个位数", "减数", "是否退位"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            a = random.randint(11, 18)
            if ones_target and str(a % 10) != ones_target:
                continue
            b = int(b_target) if b_target else random.randint(a - 9, 9)
            q = Question(text=f"(){a % 10} - {b}", answer=str(a - b),
                         meta={"a": a, "b": b})
            feats = self.extract_features(q)
            if borrow_target and feats["是否退位"] != borrow_target:
                continue
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


class PowerNumber(QuestionType):
    type_name = "幂次数"

    def generate_question(self) -> Question:
        base = random.randint(1, 19)
        exp = 3 if base < 10 else 2
        return Question(text=str(base ** exp), answer=f"{base} {exp}",
                        meta={"base": base, "exp": exp})

    def extract_features(self, question: Question) -> dict[str, str]:
        base = question.meta["base"]
        exp = question.meta["exp"]
        return {
            "底数范围": "1-9" if base < 10 else "10-19",
            "指数": str(exp),
            "结果位数": str(len(question.text)),
        }

    def extract_cross_features(self, question: Question) -> dict[str, list[str]]:
        base = question.meta["base"]
        exp = question.meta["exp"]
        digits = [c for c in str(base)]
        digits.append(str(exp))
        return {"involved_digits": digits}

    def generate_question_with_features(self, features: dict[str, str]) -> Question:
        base_range_target = features.get("底数范围")
        exp_target = features.get("指数")
        digits_target = features.get("结果位数")
        has_local = any(k in features for k in {"底数范围", "指数", "结果位数"})
        if not has_local:
            return super().generate_question_with_features(features)

        for _ in range(200):
            if base_range_target == "1-9":
                base = random.randint(1, 9)
            elif base_range_target == "10-19":
                base = random.randint(10, 19)
            else:
                base = random.randint(1, 19)
            exp = 3 if base < 10 else 2
            if exp_target and str(exp) != exp_target:
                continue
            q = Question(text=str(base ** exp), answer=f"{base} {exp}",
                         meta={"base": base, "exp": exp})
            if digits_target and str(len(q.text)) != digits_target:
                continue
            if "involved_digits" in features:
                cross = self.extract_cross_features(q)
                if features["involved_digits"] not in cross.get("involved_digits", []):
                    continue
            return q
        return self.generate_question()


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
