from datetime import datetime
from typing import Tuple
from unittest import TestCase

from src.Task import Task, SnapshotManager, SnapshotStorage, TaskProvider


class MockSnapshotStorage(SnapshotStorage):
    def __init__(self) -> None:
        self.drafts = dict()
        self.snaps = dict()

    def draft_write(self, draft_id, tasks):
       self.drafts[draft_id] = (tasks, datetime.now().astimezone().timestamp()) 

    def drafts_list(self) -> dict[Tuple[str, str], float]:
        return {k:v[1] for k,v in self.drafts.items()}

    def draft_read(self, draft_id) -> list[Task]:
        return self.drafts[draft_id][0]

    def draft_approve(self, draft_id):
        p = self.drafts.pop(draft_id)
        self.snaps[(draft_id, p[1])] = p[0]

    def snapshots_list(self) -> list[Tuple[Tuple[str, str], float]]:
        return [k for k in self.snaps]

    def snapshot_read(self, snap_id) -> list[Task]:
        return self.snaps[snap_id]


apr = [Task('April1', ['A1'], 'CC_13.3.7', ''),
       Task('April2', ['A2'], 'CC_13.3.7', '')]
may = [Task('May1', ['M1'], 'CC_13.3.8', ''),
       Task('May2', ['M2'], 'CC_13.3.8', '')]


class MockTasksProvider(TaskProvider):
    def get_tasks(self, pat, date_from, date_to) -> list[Task]:
        if date_from == '01-04-2023' and date_to == '30-04-2023':
            return apr
        if date_from == '01-05-2023' and date_to == '31-05-2023':
            return may
        raise ValueError


class TestSnapshotManager(TestCase):
    def test_stage_manipulation(self):
        sm = SnapshotManager(MockSnapshotStorage(), MockTasksProvider())

        sm.draft_update('patpatpatpat', '01-04-2023', '30-04-2023')
        a = sm.drafts_list()
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        u = a[0].mtime

        sm.draft_update('patpatpatpat', '01-04-2023', '30-04-2023')
        a = sm.drafts_list()
        self.assertEqual(len(a), 1)  # dates are the same, count must retain
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        # datetime must change between updates
        self.assertNotEqual(u, a[0].mtime)

        sm.draft_update('patpatpatpat', '01-05-2023', '31-05-2023')
        a = sm.drafts_list()
        self.assertEqual(len(a), 2)
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        self.assertEqual(a[1].date_from,  '01-05-2023')
        self.assertEqual(a[1].date_to,    '31-05-2023')

        with self.assertRaises(KeyError):
            sm.draft_get_tasks('01-05-2000', '31-05-2000')

        b = sm.draft_get_tasks('01-04-2023', '30-04-2023')
        self.assertListEqual(b, apr)
        b = sm.draft_get_tasks('01-05-2023', '31-05-2023')
        self.assertListEqual(b, may)

    def test_snapshot_manipulation(self):
        sm = SnapshotManager(MockSnapshotStorage(), MockTasksProvider())

        sm.draft_update('patpatpatpat', '01-04-2023', '30-04-2023')

        with self.assertRaises(KeyError):
            sm.draft_approve('01-04-2000', '30-04-2000')

        sm.draft_approve('01-04-2023', '30-04-2023')

        # approve removes from the drafts
        self.assertEqual(0, len(sm.drafts_list()))

        a = sm.snapshots_list()
        self.assertEqual(1, len(a))
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')

        with self.assertRaises(KeyError):
            sm.snapshot_get_tasks('01-04-2000', '30-04-2000')

        b = sm.snapshot_get_tasks('01-04-2023', '30-04-2023')
        self.assertListEqual(b, apr)


class TestSnapshotStorage(TestCase):
    pass
