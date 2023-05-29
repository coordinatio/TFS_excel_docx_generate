from typing import List, Tuple
from pathlib import Path
from sqlite3 import connect

from tfs import deepcopy

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

class SQlite(FastStorage):
    def __init__(self, path_db: str) -> None:
        self.db = Path(path_db)
        if not self.db.exists() or self.db.stat().st_size == 0:
            if not self.db.parent.exists() or not self.db.parent.is_dir():
                raise ValueError("Invalid SQlite DB path")
            con = connect(self.db)
            con.execute(("CREATE TABLE essence_cache ("
                         "   project TEXT, "
                         "   tid TEXT, "
                         "   parent_title TEXT, "
                         "   title TEXT, "
                         "   essence TEXT, "
                         "   PRIMARY KEY (project, tid)"
                         ");"))
            con.close()
        self.con = connect(self.db)

    def read_essense(self, tasks: List[Task]) -> Tuple[List[Task], List[Task]]:
        known: List[Task] = []
        unknown: List[Task] = []
        for t in tasks:
            q = "SELECT essence FROM essence_cache WHERE project=? AND tid=?"
            e = self.con.execute(q, (t.project, t.tid)).fetchone()
            c = deepcopy(t)
            if not e:
                unknown.append(c)
            else:
                c.essence = e[0]
                known.append(c)
        return (known, unknown)




class AI:
    def generate_essense(self, tasks: List[Task]) -> List[Task]:
        raise NotImplementedError

class Cache:
    def __init__(self, fs: FastStorage, ai: AI) -> None:
        self.fs = fs
        self.ai = ai

    def filter(self, tasks: List[Task]) -> List[Task]:
        k, unk = self.fs.read_essense(tasks)
        if not unk:
            return k
        gen = self.ai.generate_essense(unk) 
        self.fs.memorize_essense(gen)
        return k + gen
