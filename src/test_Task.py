from unittest import TestCase
from datetime import datetime
from src.Task import SnapshotManager, SnapshotInfo, TaskProvider, SnapshotStorage


class MockSnapshotStorage(SnapshotStorage):
    pass


class MockTasksProvider(TaskProvider):
    pass


class TestSnapshotManager(TestCase):
    def test_stage_manipulation(self):
        sm = SnapshotManager(MockSnapshotStorage(), MockTasksProvider())

        sm.stage_update('patpatpatpat', '01-04-2023', '30-04-2023')
        a = sm.stage_list()
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        self.assertEqual(a[0].is_approved, False)
        u = a[0].datetime_updated

        sm.stage_update('patpatpatpat', '01-04-2023', '30-04-2023')
        a = sm.stage_list()
        self.assertEqual(len(a), 1) #dates are the same, count must retain
        self.assertEqual(a[0].date_from,  '01-04-2023')
        self.assertEqual(a[0].date_to,    '30-04-2023')
        self.assertEqual(a[0].is_approved, False)
        self.assertNotEqual(u, a[0].datetime_updated) #datetime must change between updates
