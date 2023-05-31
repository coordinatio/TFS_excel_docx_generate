# -*- coding: utf-8 -*-
from time import sleep
from typing import List, Tuple
from pathlib import Path
from sqlite3 import connect
from copy import deepcopy
from progress.bar import Bar

from src.Task import Task

import openai


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
            q = "SELECT essence FROM essence_cache WHERE project=? AND tid=?;"
            e = self.con.execute(q, (t.project, t.tid)).fetchone()
            c = deepcopy(t)
            if not e:
                unknown.append(c)
            else:
                c.essence = e[0]
                known.append(c)
        return (known, unknown)

    def memorize_essense(self, tasks: List[Task]):
        for t in tasks:
            d = {'project': t.project,
                 'tid': t.tid,
                 'parent_title': t.parent_title,
                 'title': t.title,
                 'essence': t.essence}
            q = ("INSERT INTO essence_cache"
                 " VALUES(:project, :tid, :parent_title, :title, :essence)"
                 " ON CONFLICT(project, tid) DO"
                 " UPDATE SET parent_title=:parent_title, title=:title, essence=:essence;")
            with self.con:
                self.con.execute(q, d)


class AI:
    def generate_essense(self, tasks: List[Task]) -> List[Task]:
        raise NotImplementedError


class ChatGPT(AI):
    def __init__(self, api_key) -> None:
        openai.api_key = api_key

    def generate_essense(self, tasks: List[Task]) -> List[Task]:
        out: List[Task] = []
        with Bar('Talking with AI', max=len(tasks)) as bar:
            for t in tasks:
                o = deepcopy(t)
                o.essence = self.talk_to_ChatGPT(
                    o.parent_title, o.title, o.body)
                sleep(21)
                bar.next()
        return out

    def talk_to_ChatGPT(self, parent_title: str | None, title: str, body: str | None) -> str:
        m = [
            {'role': 'system',
             'content': ('На основе информации из системы отслеживания'
                         ' работы сформулируй задачу одним кратким предложением.')},
            {'role': 'user',
             'content': (f'Заголовок задачи: "{parent_title}",'
                         f' заголовок подзадачи: "{title}",'
                         f' тело подзадачи "{body}".')}
        ]
        c = openai.ChatCompletion.create(
            model='gpt-3.5-turbo', messages=m, temperature=0.5)
        return c.choices[0].message.content


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
