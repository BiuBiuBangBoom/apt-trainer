from typing import Optional

from config import Config
from data_store import DataStore
from strategy import ExamStrategy


class Context:
    def __init__(self, config: Config, data_store: Optional[DataStore]):
        self.config = config
        self.data_store = data_store
        self._strategy: Optional[ExamStrategy] = None

    def set_strategy(self, strategy: ExamStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> Optional[ExamStrategy]:
        return self._strategy

    def execute_strategy(self) -> None:
        if self._strategy:
            self._strategy.execute(self.config, self.data_store)
