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


if __name__ == "__main__":
    unittest.main()
