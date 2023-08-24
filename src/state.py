from pathlib import Path
import pickle
from typing import Sequence, TypeVar

T = TypeVar('T')


class State:
    def __init__(self, filepath: Path | str):
        self._filepath = Path(filepath)

    def dump(self, products: Sequence[T]):
        with self._filepath.open(mode="wb") as file:
            pickle.dump(products, file)

    def load(self) -> Sequence[T]:
        if not self._filepath.is_file():
            self.dump([])
        with self._filepath.open(mode="rb") as file:
            return pickle.load(file)

    def filter_not_presented(self, items: Sequence[T]) -> Sequence[T]:
        state = self.load()
        filtered = []
        for item in items:
            if item not in state:
                filtered.append(item)
        return filtered
