from datetime import datetime
from unittest import TestCase

from src.Task import Task, SnapshotManager, SnapshotStorage, TaskProvider


class MockSnapshotStorage(SnapshotStorage):
    pass


class MockTasksProvider(TaskProvider):
    def __init__(self) -> None:
        self.tasks = dict()
        super().__init__()

    def mockdata(self, key, val):
        self.tasks[key] = val


class TestSnapshotManager(TestCase):
    def test_stage_manipulation(self):
        mtp = MockTasksProvider()
        apr = [Task('April1', ['A1'], 'CC_13.3.7', ''),
               Task('April2', ['A2'], 'CC_13.3.7', '')]
        may = [Task('May1', ['M1'], 'CC_13.3.8', ''),
               Task('May2', ['M2'], 'CC_13.3.8', '')]
        mtp.mockdata('01-04-2023 30-04-2023', apr)
        mtp.mockdata('01-05-2023 31-05-2023', may)
        sm = SnapshotManager(MockSnapshotStorage(), mtp)

        sm.draft_update('patpatpatpat', '01-04-2023', '30-04-2023')
        a = sm.drafts_list()
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        u = a[0].datetime_updated

        sm.draft_update('patpatpatpat', '01-04-2023', '30-04-2023')
        a = sm.drafts_list()
        self.assertEqual(len(a), 1)  # dates are the same, count must retain
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        # datetime must change between updates
        self.assertNotEqual(u, a[0].datetime_updated)

        sm.draft_update('patpatpatpat', '01-05-2023', '31-05-2023')
        a = sm.drafts_list()
        self.assertEqual(len(a), 2)
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        self.assertEqual(a[1].date_from,  '01-05-2023')
        self.assertEqual(a[1].date_to,    '31-05-2023')

        with self.assertRaises(ValueError):
            sm.draft_get_tasks('01-05-2000', '31-05-2000')

        b = sm.draft_get_tasks('01-04-2023', '30-04-2023')
        self.assertListEqual(b, apr)
        b = sm.draft_get_tasks('01-05-2023', '31-05-2023')
        self.assertListEqual(b, may)

    def test_snapshot_manipulation(self):
        mtp = MockTasksProvider()
        apr = [Task('April1', ['A1'], 'CC_13.3.7', ''),
               Task('April2', ['A2'], 'CC_13.3.7', '')]
        mtp.mockdata('01-04-2023 30-04-2023', apr)
        sm = SnapshotManager(MockSnapshotStorage(), mtp)

        sm.draft_update('patpatpatpat', '01-04-2023', '30-04-2023')

        with self.assertRaises(ValueError):
            sm.draft_approve('01-04-2000', '30-04-2000')

        sm.draft_approve('01-04-2023', '30-04-2023')

        self.assertEqual(0, len(sm.drafts_list())) #approve removes from the drafts

        a = sm.snapshots_list()
        self.assertEqual(1, len(a))
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')

        with self.assertRaises(ValueError):
            sm.snapshot_get_tasks('01-04-2000', '30-04-2000')

        b = sm.snapshot_get_tasks('01-04-2023', '30-04-2023')
        self.assertListEqual(b, apr)
