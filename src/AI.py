# -*- coding: utf-8 -*-
from datetime import datetime
from time import sleep
from typing import List, Tuple
from pathlib import Path
from sqlite3 import connect, IntegrityError
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

    def memorize_essense(self, task: Task):
        raise NotImplementedError


class SQlite(FastStorage):
    def __init__(self, path_db: str) -> None:
        self.db = Path(path_db)
        if not self.db.exists() or self.db.stat().st_size == 0:
            if not self.db.parent.exists() or not self.db.parent.is_dir():
                raise ValueError("Invalid SQlite DB path")
            con = connect(self.db)
            con.execute(("CREATE TABLE essence_cache ("
                         "   project TEXT NOT NULL, "
                         "   tid TEXT NOT NULL, "
                         "   parent_title TEXT, "
                         "   title TEXT NOT NULL, "
                         "   body TEXT, "
                         "   essence TEXT NOT NULL, "
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

    def memorize_essense(self, task: Task):
        d = {'project': task.project,
             'tid': task.tid,
             'parent_title': task.parent_title,
             'title': task.title,
             'body': task.body,
             'essence': task.essence}
        q = ('INSERT INTO essence_cache'
             ' VALUES(:project, :tid, :parent_title, :title, :body, :essence)'
             ' ON CONFLICT(project, tid) DO'
             ' UPDATE SET parent_title=:parent_title, title=:title, essence=:essence, body=:body;')
        try:
            with self.con:
                self.con.execute(q, d)
        except (IntegrityError) as e:
            raise RuntimeError(
                f'SQlite error {e.sqlite_errorcode}: {e.sqlite_errorname}')


class AI:
    def generate_essense(self, task: Task) -> Task:
        raise NotImplementedError


class ChatGPT(AI):
    def __init__(self, api_key: str, max_query_rate_sec: float) -> None:
        openai.api_key = api_key
        self.max_rate_sec = max_query_rate_sec
        self.last_request_ts: float = 0.0
        self.now = datetime.now().astimezone().timestamp
        self.sleep = sleep

    def generate_essense(self, task: Task) -> Task:
        self._limit_RPM_rate()
        o = deepcopy(task)
        if not o.parent_title and not o.body:
            o.essence = o.title  # no need for an AI if we have no data
        else:
            quota_tries = 3
            while True:
                try:
                    o.essence = self.talk_to_ChatGPT(
                        o.parent_title, o.title, o.body)
                    break
                except (openai.error.RateLimitError) as e:
                    if quota_tries <= 0:
                        raise e
                    delay_sec = 63
                    print(('\nThe rate limit hit.'
                           f' Sleeping for {delay_sec} seconds.'
                           f' {quota_tries} attempts left. ({e})\n'))
                    quota_tries -= 1
                    self.sleep(delay_sec)
        return o

    def _limit_RPM_rate(self):
        delta_sec: float = self.now() - self.last_request_ts
        if delta_sec < self.max_rate_sec:
            self.sleep(self.max_rate_sec - delta_sec)
        self.last_request_ts = self.now()

    def talk_to_ChatGPT(self, parent_title: str | None, title: str, body: str | None) -> str:
        m = [
            {'role': 'system',
             'content': ('На основе информации из системы отслеживания'
                         ' работы сформулируй задачу одним кратким предложением.'
                         ' Не начинай предложения со слов "Задача: ",  "Сформулированная задача:"'
                         ' или подобных, сразу переходи к сути.'
                         ' Не проси более подробную информацию, работай с тем, что есть.')},
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
        gen: List[Task] = []
        with Bar('Talking with the AI:', max=len(unk)) as bar:
            for t in unk:
                o = self.ai.generate_essense(t)
                self.fs.memorize_essense(o)
                gen.append(o)
                bar.next()
        return k + gen
