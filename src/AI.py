from typing import List, Tuple
from src.Task import Task


class FastStorage:
    def read_essense(self, tasks: List[Task]) -> Tuple[List[Task], List[Task]]:
        """
        Fill the stored essence into the list of tasks.

        :param List[Task] tasks: the list of tasks to consider
        :return: a Tuple of two Lists of Tasks, the first are the filled ones, the second are unknown ones 
        """
        raise NotImplementedError

    def memorize_essense(self, tasks: List[Task]):
        raise NotImplementedError

class AI:
    def generate_essense(self, tasks: List[Task]) -> List[Task]:
        raise NotImplementedError

class Cache:
    def __init__(self, fs: FastStorage, ai: AI) -> None:
        self.fs = fs
        self.ai = ai

    def filter(self, tasks: List[Task]) -> List[Task]:
        raise NotImplementedError
