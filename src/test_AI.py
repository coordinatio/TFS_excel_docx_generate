from typing import List, Tuple
from unittest import TestCase
from unittest.mock import MagicMock
from copy import deepcopy
from tempfile import mkstemp

from src.AI import ChatGPT, FastStorage, SQlite, AI, Cache
from src.Task import Task


class MockFastStorage(FastStorage):
    def __init__(self, known_ids: set[str]) -> None:
        self.known_ids = deepcopy(known_ids)

    def read_essense(self, tasks: List[Task]) -> Tuple[List[Task], List[Task]]:
        known = [deepcopy(t) for t in tasks if t.tid in self.known_ids]
        for k in known:
            k.essence = f'KNOWN_{k.tid}_KNOWN'
        return (known, [deepcopy(t) for t in tasks if t.tid not in self.known_ids])

    def memorize_essense(self, task: Task):
        self.known_ids |= {task.tid}


class MockAI(AI):
    def generate_essense(self, task: Task) -> Task:
        task.essence = f'MockAI_{task.tid}_MockAI'
        return task


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
            unk.essence = f'{unk.project}_{unk.tid} суть суть суть'
            s.memorize_essense(unk)

        t.append(Task(**a, tid='7777', title='77',
                 parent_title='70', project='Y'))

        known, unknown = s.read_essense(deepcopy(t))
        self.assertEqual(1, len(unknown))
        self.assertTupleEqual(
            ('7777', 'Y'), (unknown[0].tid, unknown[0].project))
        self.assertEqual(6, len(known))
        for k in known:
            self.assertEqual(k.essence, f'{k.project}_{k.tid} суть суть суть')

    def test_empty_ids(self):
        a = {'assignees': [], 'release': '', 'link': '',
             'title': 't', 'parent_title': 'pt'}
        s = SQlite(mkstemp(suffix='.db')[1])

        t = Task(**a, tid=None, project='X')
        with self.assertRaises(RuntimeError):
            s.memorize_essense(t)

        t = Task(**a, tid='1111', project=None)
        with self.assertRaises(RuntimeError):
            s.memorize_essense(t)

        t = Task(**a, tid=None, project=None)
        with self.assertRaises(RuntimeError):
            s.memorize_essense(t)


class TestAI(TestCase):
    # def test_for_manual_prompt_debugging(self):
    #     c = ChatGPT('%PLACE YOUR APTI KEY HERE%')
    #     print(c.talk_to_ChatGPT('Сервер-приложений альфа-версия', 'Починить HTTPS', ''))

    def test_happyday(self):
        t = Task(assignees=[], release='', link='', project='X',
                 tid='TID', title='T', parent_title='PT', body='B')

        ai = ChatGPT('', 21)
        ai.now = MagicMock(return_value=100)
        ai.sleep = MagicMock()
        ai.talk_to_ChatGPT = MagicMock(return_value='MockAI')

        out = ai.generate_essense(t)

        self.assertEqual('MockAI', out.essence)  # talk occured
        ai.talk_to_ChatGPT.assert_called_with('PT', 'T', 'B')
        ai.sleep.assert_not_called()  # no sleep during the first call
        self.assertEqual(ai.last_request_ts, 100)  # last_request_ts updated

        ai.now = MagicMock(return_value=110)
        ai.sleep = MagicMock()

        out = ai.generate_essense(t)

        # rate 21sec, 10 sec passed => must sleep for 11 sec
        ai.sleep.assert_called_once_with(11)
