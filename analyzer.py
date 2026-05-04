import json
from dataclasses import dataclass
from collections import defaultdict

from data_store import Record
from mode import Question, question_type_for_name


@dataclass
class Weakness:
    type_name: str
    feature_name: str
    feature_value: str
    accuracy: float
    avg_time_ms: float
    total_count: int
    baseline_accuracy: float
    baseline_time_ms: float


@dataclass
class CrossWeakness:
    feature_name: str
    feature_value: str
    accuracy: float
    avg_time_ms: float
    total_count: int
    affected_types: list[str]


class WeaknessAnalyzer:
    _ACCURACY_THRESHOLD = 0.15
    _TIME_RATIO_THRESHOLD = 1.5
    _CROSS_ACCURACY_THRESHOLD = 0.10
    _CROSS_TIME_RATIO_THRESHOLD = 1.5

    def __init__(self, records: list[Record], min_samples: int = 3):
        self._records = records
        self._min_samples = min_samples

    def analyze(self) -> list[Weakness]:
        typed_records: dict[str, list[Record]] = defaultdict(list)
        for r in self._records:
            typed_records[r.type_name].append(r)

        weaknesses: list[Weakness] = []
        for type_name, recs in typed_records.items():
            qt = question_type_for_name(type_name)
            if qt is None:
                continue

            total = len(recs)
            type_correct = sum(1 for r in recs if r.is_correct)
            type_accuracy = type_correct / total if total > 0 else 0.0
            type_time = sum(r.cost_time_ms for r in recs) / total if total > 0 else 0.0

            feature_stats: dict[tuple[str, str], dict] = defaultdict(
                lambda: {"count": 0, "correct": 0, "total_time": 0.0})

            for r in recs:
                if not r.meta_json:
                    continue
                try:
                    meta = json.loads(r.meta_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                q = Question(text=r.question, answer=r.answer, meta=meta)
                feats = qt.extract_features(q)
                if not feats:
                    continue
                for fname, fval in feats.items():
                    key = (fname, fval)
                    feature_stats[key]["count"] += 1
                    feature_stats[key]["total_time"] += r.cost_time_ms
                    if r.is_correct:
                        feature_stats[key]["correct"] += 1

            for (fname, fval), stats in feature_stats.items():
                cnt = stats["count"]
                if cnt < self._min_samples:
                    continue
                f_acc = stats["correct"] / cnt
                f_avg_time = stats["total_time"] / cnt
                if f_acc < type_accuracy - self._ACCURACY_THRESHOLD or f_avg_time > type_time * self._TIME_RATIO_THRESHOLD:
                    weaknesses.append(Weakness(
                        type_name=type_name,
                        feature_name=fname,
                        feature_value=fval,
                        accuracy=f_acc,
                        avg_time_ms=f_avg_time,
                        total_count=cnt,
                        baseline_accuracy=type_accuracy,
                        baseline_time_ms=type_time,
                    ))

        weaknesses.sort(key=lambda w: w.accuracy)
        return weaknesses

    def analyze_cross(self) -> list[CrossWeakness]:
        if not self._records:
            return []

        total = len(self._records)
        global_correct = sum(1 for r in self._records if r.is_correct)
        global_accuracy = global_correct / total if total > 0 else 0.0
        global_time = sum(r.cost_time_ms for r in self._records) / total if total > 0 else 0.0

        digit_stats: dict[str, dict] = defaultdict(
            lambda: {"count": 0, "correct": 0, "total_time": 0.0, "types": set()})

        for r in self._records:
            if not r.meta_json:
                continue
            try:
                meta = json.loads(r.meta_json)
            except (json.JSONDecodeError, TypeError):
                continue
            q = Question(text=r.question, answer=r.answer, meta=meta)
            qt = question_type_for_name(r.type_name)
            if qt is None:
                continue
            cross = qt.extract_cross_features(q)
            for digit in cross.get("involved_digits", []):
                ds = digit_stats[digit]
                ds["count"] += 1
                ds["total_time"] += r.cost_time_ms
                if r.is_correct:
                    ds["correct"] += 1
                ds["types"].add(r.type_name)

        cross_weaknesses: list[CrossWeakness] = []
        for digit, ds in digit_stats.items():
            cnt = ds["count"]
            if cnt < self._min_samples:
                continue
            d_acc = ds["correct"] / cnt
            d_time = ds["total_time"] / cnt
            if d_acc < global_accuracy - self._CROSS_ACCURACY_THRESHOLD or d_time > global_time * self._CROSS_TIME_RATIO_THRESHOLD:
                cross_weaknesses.append(CrossWeakness(
                    feature_name="involved_digits",
                    feature_value=digit,
                    accuracy=d_acc,
                    avg_time_ms=d_time,
                    total_count=cnt,
                    affected_types=sorted(ds["types"]),
                ))

        cross_weaknesses.sort(key=lambda w: w.accuracy)
        return cross_weaknesses
