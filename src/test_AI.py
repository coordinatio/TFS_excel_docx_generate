from typing import List, Tuple
from unittest import TestCase
from copy import deepcopy
from tempfile import mkstemp

from src.AI import FastStorage, SQlite, AI, Cache
from src.Task import Task


class MockFastStorage(FastStorage):
    def __init__(self, known_ids: set[str]) -> None:
        self.known_ids = deepcopy(known_ids)

    def read_essense(self, tasks: List[Task]) -> Tuple[List[Task], List[Task]]:
        known = [deepcopy(t) for t in tasks if t.tid in self.known_ids]
        for k in known:
            k.essence = f'KNOWN_{k.tid}_KNOWN'
        return (known, [deepcopy(t) for t in tasks if t.tid not in self.known_ids])

    def memorize_essense(self, tasks: List[Task]):
        self.known_ids |= {t.tid for t in tasks}


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
        self.assertEqual(ids_out, ids_in)  # if True - thus nothing is lost

        z_in = []
        for t in t_out:
            if t.tid in ids_known:
                self.assertEqual(f'KNOWN_{t.tid}_KNOWN', t.essence)
            else:
                self.assertEqual(f'MockAI_{t.tid}_MockAI', t.essence)
                z_in.append(t)
        self.assertNotEqual(len(z_in), 0)

        z_out = c.filter(z_in)
        self.assertEqual(len(z_in), len(z_out))
        self.assertEqual({t.tid for t in z_in}, {t.tid for t in z_out})
        for z in z_out:
            self.assertEqual(z.essence, f'KNOWN_{z.tid}_KNOWN')


class TestFastStorage(TestCase):
    def test_happyday(self):
        a = {'assignees': [], 'release': '', 'link': ''}
        t = []
        for i in range(1, 4):
            t.append(Task(
                **a, tid=f'{i}{i}{i}{i}', title=f'X{i}X{i}', parent_title=f'X{i}X0', project='X'))
            t.append(Task(
                **a, tid=f'{i}{i}{i}{i}', title=f'Y{i}Y{i}', parent_title=f'Y{i}Y0', project='Y'))
        s = SQlite(mkstemp(suffix='.db')[1])

        known, unknown = s.read_essense(deepcopy(t))

        self.assertEqual(len(t), len(unknown))
        self.assertEqual(0, len(known))

        for unk in unknown:
            unk.essence = "Съешь ещё этих мягких французских булок да выпей же чаю."
        s.memorize_essense(unknown)

        t.append(Task(**a, tid='7777', title='77', parent_title='70', project='Y'))

