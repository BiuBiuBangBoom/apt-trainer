import os
from dataclasses import dataclass
from typing import Optional

from common import cyan_str, yellow_str, GREEN, YELLOW, RED, RESET


@dataclass
class Record:
    date: str = ""
    type_name: str = ""
    mode_name: str = ""
    question: str = ""
    response: str = ""
    answer: str = ""
    cost_time_ms: int = 0
    is_correct: bool = False
    meta_json: str = ""


@dataclass
class TypeStats:
    type_name: str = ""
    total_count: int = 0
    correct_count: int = 0
    avg_time_ms: float = 0.0
    accuracy: float = 0.0


class DataStore:
    def __init__(self, file_path: str):
        self._file_path = file_path

    @staticmethod
    def _escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")

    @staticmethod
    def _unescape(s: str) -> str:
        result = []
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                nxt = s[i + 1]
                if nxt == "n":
                    result.append("\n")
                    i += 2
                    continue
                if nxt == "t":
                    result.append("\t")
                    i += 2
                    continue
            result.append(s[i])
            i += 1
        return "".join(result)

    def _format_record(self, record: Record) -> str:
        return "\t".join([
            record.date,
            self._escape(record.type_name),
            self._escape(record.mode_name),
            self._escape(record.question),
            self._escape(record.response),
            self._escape(record.answer),
            str(record.cost_time_ms),
            "1" if record.is_correct else "0",
            self._escape(record.meta_json),
        ])

    def _parse_record(self, line: str) -> Optional[Record]:
        fields = line.split("\t")
        if len(fields) < 8:
            return None
        return Record(
            date=self._unescape(fields[0]),
            type_name=self._unescape(fields[1]),
            mode_name=self._unescape(fields[2]),
            question=self._unescape(fields[3]),
            response=self._unescape(fields[4]),
            answer=self._unescape(fields[5]),
            cost_time_ms=int(fields[6]),
            is_correct=(fields[7] == "1"),
            meta_json=self._unescape(fields[8]) if len(fields) >= 9 else "",
        )

    def save_record(self, record: Record) -> None:
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        with open(self._file_path, "a") as f:
            f.write(self._format_record(record) + "\n")

    def get_all_records(self) -> list[Record]:
        records: list[Record] = []
        if not os.path.exists(self._file_path):
            return records
        with open(self._file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    r = self._parse_record(line)
                    if r:
                        records.append(r)
        return records

    def get_wrong_records(self) -> list[Record]:
        return [r for r in self.get_all_records() if not r.is_correct]

    def get_type_stats(self) -> list[TypeStats]:
        records = self.get_all_records()
        stats_map: dict[str, TypeStats] = {}

        for r in records:
            if r.type_name not in stats_map:
                stats_map[r.type_name] = TypeStats(type_name=r.type_name)
            s = stats_map[r.type_name]
            s.total_count += 1
            if r.is_correct:
                s.correct_count += 1
            s.avg_time_ms += r.cost_time_ms

        stats = list(stats_map.values())
        for s in stats:
            s.accuracy = s.correct_count / s.total_count if s.total_count > 0 else 0.0
            s.avg_time_ms = s.avg_time_ms / s.total_count if s.total_count > 0 else 0.0
        return stats

    def clear_all(self) -> None:
        """Delete all records."""
        if os.path.exists(self._file_path):
            os.remove(self._file_path)

    def print_summary(self) -> None:
        stats = self.get_type_stats()
        if not stats:
            print(yellow_str("暂无历史记录"))
            return

        print(f"\n{cyan_str('========== 历史统计 ==========')}\n")

        for s in stats:
            if s.accuracy >= 0.85:
                color = GREEN
            elif s.accuracy >= 0.7:
                color = YELLOW
            else:
                color = RED

            print(f"题型: {s.type_name}")
            print(f"  练习次数: {s.total_count}")
            print(f"  正确率:   {color}{s.accuracy * 100:.1f}%{RESET}")
            print(f"  平均耗时: {s.avg_time_ms / 1000:.2f}s\n")

        print(f"{cyan_str('================================')}\n")
