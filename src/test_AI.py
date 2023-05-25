from typing import List, Tuple
from unittest import TestCase
from copy import deepcopy

from src.AI import FastStorage, AI, Cache
from src.Task import Task


class MockFastStorage(FastStorage):
    def __init__(self, known_ids: set[str]) -> None:
        self.known_ids = known_ids

    def read_essense(self, tasks: List[Task]) -> Tuple[List[Task], List[Task]]:
        known = [deepcopy(t) for t in tasks if t.tid in self.known_ids]
        for k in known:
            k.essence = 'KNOWN'
        return (known, [t for t in tasks if t.tid not in self.known_ids])

    def memorize_essense(self, tasks: List[Task]):
        self.known_ids.union({t.tid for t in tasks})


class MockAI(AI):
    def generate_essense(self, tasks: List[Task]) -> List[Task]:
        for t in tasks:
            t.essence = f'MockAI_{t.tid}_MockAI'
        return tasks


class TestCache(TestCase):
    def test_happyday(self):
        a = {'assignees': [], 'release': '', 'link': '', 'project': 'X'}
        t_in = [Task(**a, tid='1111', title='1', parent_title='10'),
                Task(**a, tid='2222', title='2', parent_title='20'),
                Task(**a, tid='3333', title='3', parent_title='30')]
        ids_in = {t.tid for t in t_in}

        ids_known = {'1111', '2222'}
        fs = MockFastStorage(ids_known)
        ai = MockAI()
        c = Cache(fs, ai)

        t_out = c.filter(t_in)
        self.assertEqual(len(t_out), len(t_in))

        ids_out = {t.tid for t in t_out}
        # the length equals and all ids are unique
        self.assertEqual(ids_out, ids_in) # if True - thus nothing is lost

        z_in = []
        for t in t_out:
            if t.tid in ids_known:
                self.assertEqual('KNOWN', t.essence)
            else:
                self.assertEqual(f'MockAI_{t.tid}_MockAI', t.essence)
                z_in.append(t)
        self.assertNotEqual(len(z_in), 0)

        z_out = c.filter(z_in)
        self.assertEqual(len(z_in), len(z_out))
        self.assertEqual({t.tid for t in z_in}, {t.tid for t in z_out})
        for z in z_out:
            self.assertEqual(z.essence, 'KNOWN')
