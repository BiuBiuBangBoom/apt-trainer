import random
import unittest

from mode import (
    Question,
    TwoDigitsTimesOneDigit,
    OneDigitPlusOneDigit,
    OneDigitTimesOneDigit,
    ThreeDigitsDivideTwoDigits,
    FractionCompare,
    PercentageConvertToFraction,
    ThreeDigitsTimesOneDigit,
    EstimateGrowth,
    TwoDigitsSubOneDigit,
    PowerNumber,
    create_question_type,
    question_type_for_name,
    MODE_REGISTRY,
)
from strategy import Session


class TestModeRegistry(unittest.TestCase):
    def test_all_10_types_registered(self):
        self.assertEqual(len(MODE_REGISTRY), 10)
        for num in range(1, 11):
            self.assertIn(num, MODE_REGISTRY)

    def test_create_question_type_valid(self):
        for num in range(1, 11):
            qt = create_question_type(num)
            self.assertIsNotNone(qt)
            self.assertTrue(len(qt.type_name) > 0)

    def test_create_question_type_invalid(self):
        self.assertIsNone(create_question_type(0))
        self.assertIsNone(create_question_type(11))
        self.assertIsNone(create_question_type(-1))

    def test_question_type_for_name_exact_match(self):
        for num in sorted(MODE_REGISTRY):
            qt = create_question_type(num)
            found = question_type_for_name(qt.type_name)
            self.assertIsNotNone(found)
            self.assertEqual(found.type_name, qt.type_name)

    def test_question_type_for_name_unknown(self):
        self.assertIsNone(question_type_for_name("不存在的题型"))


class TestTwoDigitsTimesOneDigit(unittest.TestCase):
    def setUp(self):
        self.qt = TwoDigitsTimesOneDigit()

    def test_type_name(self):
        self.assertEqual(self.qt.type_name, "两位数乘一位数")

    def test_generate_question(self):
        q = self.qt.generate_question()
        self.assertIsInstance(q, Question)
        parts = q.text.split(" * ")
        a = int(parts[0])
        b = int(parts[1])
        self.assertGreaterEqual(a, 11)
        self.assertLessEqual(a, 99)
        self.assertGreaterEqual(b, 2)
        self.assertLessEqual(b, 9)
        self.assertEqual(q.answer, str(a * b))

    def test_check_answer_correct(self):
        q = self.qt.generate_question()
        self.assertTrue(self.qt.check_answer(q, q.answer))

    def test_check_answer_wrong(self):
        q = Question(text="12 * 3", answer="36")
        self.assertFalse(self.qt.check_answer(q, "35"))


class TestOneDigitPlusOneDigit(unittest.TestCase):
    def setUp(self):
        self.qt = OneDigitPlusOneDigit()

    def test_generate_question_valid_range(self):
        for _ in range(20):
            q = self.qt.generate_question()
            parts = q.text.split(" + ")
            a, b = int(parts[0]), int(parts[1])
            self.assertGreaterEqual(a + b, 11)
            self.assertLessEqual(a + b, 18)
            self.assertEqual(q.answer, str(a + b))


class TestOneDigitTimesOneDigit(unittest.TestCase):
    def setUp(self):
        self.qt = OneDigitTimesOneDigit()

    def test_generate_question(self):
        q = self.qt.generate_question()
        parts = q.text.split(" * ")
        a, b = int(parts[0]), int(parts[1])
        self.assertGreaterEqual(a, 1)
        self.assertLessEqual(a, 9)
        self.assertGreaterEqual(b, 1)
        self.assertLessEqual(b, 9)
        self.assertEqual(q.answer, str(a * b))


class TestThreeDigitsDivideTwoDigits(unittest.TestCase):
    def setUp(self):
        self.qt = ThreeDigitsDivideTwoDigits()

    def test_generate_question(self):
        q = self.qt.generate_question()
        parts = q.text.split(" 厂 ")
        divisor = int(parts[0])
        dividend = int(parts[1])
        self.assertGreaterEqual(divisor, 10)
        self.assertLessEqual(divisor, 99)
        self.assertGreaterEqual(dividend, 100)
        self.assertLessEqual(dividend, 999)
        # Answer should be first non-zero digit of result
        expected = dividend / divisor
        for c in str(expected):
            if c in "123456789":
                self.assertEqual(q.answer, c)
                return
        self.assertEqual(q.answer, "0")


class TestFractionCompare(unittest.TestCase):
    def setUp(self):
        self.qt = FractionCompare()

    def test_generate_question_has_correct_format(self):
        q = self.qt.generate_question()
        self.assertIn("?", q.text)
        self.assertIn("------", q.text)
        # answer format: "(symbol) value1 symbol value2"
        self.assertIn(q.answer[1], "><=")

    def test_check_answer_by_symbol(self):
        q = self.qt.generate_question()
        symbol = q.answer[1]
        self.assertTrue(self.qt.check_answer(q, symbol))
        # Wrong symbol
        wrong = "=" if symbol != "=" else "<"
        self.assertFalse(self.qt.check_answer(q, wrong))


class TestPercentageConvertToFraction(unittest.TestCase):
    def setUp(self):
        self.qt = PercentageConvertToFraction()

    def test_generate_question(self):
        q = self.qt.generate_question()
        self.assertIn("%", q.text)

    def test_check_answer(self):
        q = self.qt.generate_question()
        correct_first = q.answer.split()[0]
        self.assertTrue(self.qt.check_answer(q, correct_first))
        self.assertFalse(self.qt.check_answer(q, "999.0"))
        self.assertFalse(self.qt.check_answer(q, "notanumber"))


class TestThreeDigitsTimesOneDigit(unittest.TestCase):
    def setUp(self):
        self.qt = ThreeDigitsTimesOneDigit()

    def test_generate_question(self):
        q = self.qt.generate_question()
        parts = q.text.split(" * ")
        a, b = int(parts[0]), int(parts[1])
        self.assertGreaterEqual(a, 100)
        self.assertLessEqual(a, 999)
        self.assertGreaterEqual(b, 2)
        self.assertLessEqual(b, 9)
        self.assertEqual(q.answer, str(a * b))


class TestEstimateGrowth(unittest.TestCase):
    def setUp(self):
        self.qt = EstimateGrowth()

    def test_generate_question(self):
        q = self.qt.generate_question()
        self.assertIn("A:", q.text)
        self.assertIn("r:", q.text)
        self.assertIn("value", q.meta)
        self.assertGreater(q.meta["value"], 0)

    def test_check_answer_exact(self):
        q = self.qt.generate_question()
        self.assertTrue(self.qt.check_answer(q, q.answer))

    def test_check_answer_within_1_percent(self):
        # Create a question where we know the exact value
        q = Question(text="A: 1000  r: 10.00", answer="90.91", meta={"value": 90.9090909090909})
        # Within 1%
        self.assertTrue(self.qt.check_answer(q, "90.0"))
        self.assertTrue(self.qt.check_answer(q, "91.8"))
        # Outside 1%
        self.assertFalse(self.qt.check_answer(q, "100.0"))

    def test_check_answer_invalid(self):
        q = Question(text="A: 1000  r: 10.00", answer="90.91", meta={"value": 90.9090909090909})
        self.assertFalse(self.qt.check_answer(q, "notanumber"))


class TestTwoDigitsSubOneDigit(unittest.TestCase):
    def setUp(self):
        self.qt = TwoDigitsSubOneDigit()

    def test_generate_question(self):
        q = self.qt.generate_question()
        # Format: "()X - Y"
        self.assertIn(" - ", q.text)
        self.assertTrue(q.text.startswith("()"))
        a = int(q.text[2:].split(" - ")[0]) + 10  # reconstruct full number
        b = int(q.text.split(" - ")[1])
        self.assertGreaterEqual(a, 11)
        self.assertLessEqual(a, 18)
        self.assertEqual(q.answer, str(a - b))


class TestPowerNumber(unittest.TestCase):
    def setUp(self):
        self.qt = PowerNumber()

    def test_generate_question(self):
        q = self.qt.generate_question()
        parts = q.answer.split(" ")
        base = int(parts[0])
        exp = int(parts[1])
        self.assertGreaterEqual(base, 1)
        self.assertLessEqual(base, 19)
        self.assertIn(exp, [2, 3])
        self.assertEqual(q.text, str(base ** exp))


class TestSession(unittest.TestCase):
    def setUp(self):
        self.qt = TwoDigitsTimesOneDigit()

    def test_normal_generation(self):
        session = Session(self.qt)
        q = session.next_question()
        self.assertIsInstance(q, Question)
        self.assertTrue(len(q.text) > 0)

    def test_record_response_and_check(self):
        session = Session(self.qt)
        q = Question(text="12 * 3", answer="36")
        session.record_response(q, "36", 1000)
        self.assertEqual(len(session.records), 1)
        self.assertTrue(session.is_correct(0))
        self.assertEqual(session.records[0].cost_time_ms, 1000)

    def test_wrong_response(self):
        session = Session(self.qt)
        q = Question(text="12 * 3", answer="36")
        session.record_response(q, "35", 1000)
        self.assertFalse(session.is_correct(0))

    def test_preloaded_exhausted(self):
        preloaded = [Question(text="12 * 3", answer="36")]
        session = Session(self.qt, preloaded=preloaded)
        q1 = session.next_question()
        self.assertIsNotNone(q1)
        self.assertEqual(q1.text, "12 * 3")
        q2 = session.next_question()
        self.assertIsNone(q2)

    def test_preloaded_then_end(self):
        session = Session(self.qt, preloaded=[])
        q = session.next_question()
        self.assertIsNone(q)


class TestDataStore(unittest.TestCase):
    def setUp(self):
        from data_store import DataStore, Record
        self.DataStore = DataStore
        self.Record = Record

    def test_escape_roundtrip(self):
        ds = self.DataStore("/tmp/test_records.tsv")
        original = "hello\nworld\t!"
        escaped = ds._escape(original)
        unescaped = ds._unescape(escaped)
        self.assertEqual(original, unescaped)

    def test_escape_roundtrip_backslash(self):
        ds = self.DataStore("/tmp/test_records.tsv")
        original = r"C:\path\to\file"
        escaped = ds._escape(original)
        unescaped = ds._unescape(escaped)
        self.assertEqual(original, unescaped)

    def test_format_and_parse_roundtrip(self):
        ds = self.DataStore("/tmp/test_records.tsv")
        r = self.Record(
            date="2024-01-01 12:00:00",
            type_name="两位数乘一位数",
            mode_name="跑测模式",
            question="12 * 3",
            response="36",
            answer="36",
            cost_time_ms=1500,
            is_correct=True,
        )
        line = ds._format_record(r)
        parsed = ds._parse_record(line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.date, r.date)
        self.assertEqual(parsed.type_name, r.type_name)
        self.assertEqual(parsed.question, r.question)
        self.assertEqual(parsed.response, r.response)
        self.assertEqual(parsed.is_correct, r.is_correct)
        self.assertEqual(parsed.cost_time_ms, r.cost_time_ms)

    def test_parse_invalid_line(self):
        ds = self.DataStore("/tmp/test_records.tsv")
        self.assertIsNone(ds._parse_record(""))
        self.assertIsNone(ds._parse_record("too\tfew\tfields"))


class TestExtractFeatures(unittest.TestCase):
    def test_two_digits_times_one_digit_features(self):
        qt = TwoDigitsTimesOneDigit()
        q = Question(text="12 * 3", answer="36", meta={"a": 12, "b": 3})
        feats = qt.extract_features(q)
        self.assertEqual(feats["乘数"], "3")
        self.assertIn("进位次数", feats)
        self.assertIn("十位数", feats)
        self.assertIn("个位数", feats)
        self.assertIn("结果位数", feats)

    def test_one_digit_plus_one_features(self):
        qt = OneDigitPlusOneDigit()
        q = Question(text="8 + 7", answer="15", meta={"a": 8, "b": 7})
        feats = qt.extract_features(q)
        self.assertEqual(feats["加数"], "8")
        self.assertEqual(feats["被加数"], "7")
        self.assertEqual(feats["和的个位"], "5")

    def test_three_digits_divide_two_features(self):
        qt = ThreeDigitsDivideTwoDigits()
        q = Question(text="25 厂 500", answer="2", meta={"divisor": 25, "dividend": 500})
        feats = qt.extract_features(q)
        self.assertIn("除数范围", feats)
        self.assertIn("商的首位", feats)
        self.assertIn("被除数范围", feats)
        self.assertEqual(feats["商的首位"], "2")

    def test_fraction_compare_features(self):
        qt = FractionCompare()
        q = qt.generate_question()
        feats = qt.extract_features(q)
        self.assertIn("分母位数差", feats)
        self.assertIn("数值差距", feats)
        self.assertIn(feats["数值差距"], ("接近", "明显"))

    def test_percentage_convert_features(self):
        qt = PercentageConvertToFraction()
        q = qt.generate_question()
        feats = qt.extract_features(q)
        self.assertIn("百分比范围", feats)

    def test_estimate_growth_features(self):
        qt = EstimateGrowth()
        q = qt.generate_question()
        feats = qt.extract_features(q)
        self.assertIn("基数范围", feats)
        self.assertIn("增长率", feats)


class TestCrossFeatures(unittest.TestCase):
    def test_cross_features_returns_involved_digits(self):
        for cls in (TwoDigitsTimesOneDigit, OneDigitPlusOneDigit, OneDigitTimesOneDigit,
                     ThreeDigitsTimesOneDigit, PowerNumber):
            qt = cls()
            q = qt.generate_question()
            cross = qt.extract_cross_features(q)
            self.assertIn("involved_digits", cross)
            self.assertIsInstance(cross["involved_digits"], list)
            self.assertGreater(len(cross["involved_digits"]), 0)


class TestGenerateWithFeatures(unittest.TestCase):
    def test_two_digits_times_one_with_features(self):
        qt = TwoDigitsTimesOneDigit()
        q = qt.generate_question_with_features({"乘数": "7"})
        self.assertEqual(q.meta["b"], 7)

    def test_one_digit_plus_one_with_features(self):
        qt = OneDigitPlusOneDigit()
        q = qt.generate_question_with_features({"加数": "4"})
        self.assertEqual(q.meta["a"], 4)

    def test_one_digit_times_one_with_features(self):
        qt = OneDigitTimesOneDigit()
        q = qt.generate_question_with_features({"乘数": "5"})
        big = max(q.meta["a"], q.meta["b"])
        self.assertEqual(big, 5)

    def test_estimate_growth_with_features(self):
        qt = EstimateGrowth()
        q = qt.generate_question_with_features({"基数范围": "10k-100k"})
        self.assertGreaterEqual(q.meta["base"], 10000)
        self.assertLessEqual(q.meta["base"], 99999)

    def test_power_number_with_features(self):
        qt = PowerNumber()
        q = qt.generate_question_with_features({"底数范围": "1-9"})
        self.assertGreaterEqual(q.meta["base"], 1)
        self.assertLessEqual(q.meta["base"], 9)

    def test_two_digits_sub_one_with_features(self):
        qt = TwoDigitsSubOneDigit()
        q = qt.generate_question_with_features({"是否退位": "是"})
        feats = qt.extract_features(q)
        self.assertEqual(feats["是否退位"], "是")

    def test_falls_back_when_no_match(self):
        qt = TwoDigitsTimesOneDigit()
        q = qt.generate_question_with_features({"不存在的特征": "值"})
        self.assertIsInstance(q, Question)
        self.assertTrue(len(q.text) > 0)


class TestWeaknessAnalyzer(unittest.TestCase):
    def setUp(self):
        from data_store import Record
        self.Record = Record

    def _make_record(self, type_name: str, question: str, answer: str,
                     user_answer: str, cost_ms: int, meta: dict) -> "Record":
        import json
        return self.Record(
            date="2024-01-01 12:00:00",
            type_name=type_name,
            mode_name="练习测验模式",
            question=question,
            response=user_answer,
            answer=answer,
            cost_time_ms=cost_ms,
            is_correct=(user_answer == answer),
            meta_json=json.dumps(meta, separators=(',', ':')),
        )

    def test_analyze_returns_empty_without_enough_samples(self):
        from analyzer import WeaknessAnalyzer
        records = [
            self._make_record("两位数乘一位数", "12 * 3", "36", "36", 1000, {"a": 12, "b": 3}),
            self._make_record("两位数乘一位数", "15 * 4", "60", "60", 1200, {"a": 15, "b": 4}),
        ]
        analyzer = WeaknessAnalyzer(records, min_samples=3)
        weaknesses = analyzer.analyze()
        self.assertEqual(weaknesses, [])

    def test_analyze_detects_low_accuracy_feature(self):
        from analyzer import WeaknessAnalyzer
        records = []
        # 80% correct on multiplier 3, 20% correct on multiplier 7
        for _ in range(5):
            records.append(self._make_record("两位数乘一位数", "12 * 3", "36", "36", 1000, {"a": 12, "b": 3}))
        for _ in range(5):
            records.append(self._make_record("两位数乘一位数", "14 * 7", "98", "0", 3000, {"a": 14, "b": 7}))

        analyzer = WeaknessAnalyzer(records, min_samples=3)
        weaknesses = analyzer.analyze()
        self.assertGreater(len(weaknesses), 0)
        # Should flag multiplier=7 as weak
        weak_seven = [w for w in weaknesses if w.feature_name == "乘数" and w.feature_value == "7"]
        self.assertEqual(len(weak_seven), 1)

    def test_analyze_cross_detects_digit_sensitivity(self):
        from analyzer import WeaknessAnalyzer
        records = []
        # Consistently wrong on questions involving digit "7"
        for _ in range(3):
            records.append(self._make_record("一位数乘一位数", "7 * 8", "56", "0", 2000, {"a": 7, "b": 8}))
        for _ in range(5):
            records.append(self._make_record("一位数乘一位数", "3 * 4", "12", "12", 800, {"a": 3, "b": 4}))
            records.append(self._make_record("一位数乘一位数", "2 * 5", "10", "10", 900, {"a": 2, "b": 5}))

        analyzer = WeaknessAnalyzer(records, min_samples=3)
        cross = analyzer.analyze_cross()
        # Should detect "7" as weak digit
        digit_seven = [w for w in cross if w.feature_value == "7"]
        self.assertEqual(len(digit_seven), 1)


if __name__ == "__main__":
    unittest.main()
