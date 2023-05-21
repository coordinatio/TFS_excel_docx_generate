from datetime import datetime
from unittest import TestCase

from src.Task import Task, SnapshotManager, SnapshotStorage, TaskProvider, tasklist_to_json, json_to_tasklist


class MockSnapshotStorage(SnapshotStorage):
    def __init__(self) -> None:
        # Dict[str, Dict[str, Tuple[str, float]]]
        #      storage   data_id    data mtime
        self.s = dict()

    def write(self, storage_id: str, data_id: str, data: str) -> None:
        x = (data, datetime.now().astimezone().timestamp())
        if storage_id in self.s:
            self.s[storage_id][data_id] = x
        else:
            self.s[storage_id] = {data_id: x}

    def list(self, storage_id: str) -> dict[str, float]:
        return {k: v[1] for k, v in self.s[storage_id].items()}

    def read(self, storage_id: str, data_id: str) -> str:
        return self.s[storage_id][data_id][0]

    def delete(self, storage_id: str, data_id: str) -> None:
        del self.s[storage_id][data_id]


apr = [Task('April1', ['A1'], 'CC_13.3.7', ''),
       Task('April2', ['A2'], 'CC_13.3.7', '')]
may = [Task('May1', ['M1'], 'CC_13.3.8', ''),
       Task('May2', ['M2'], 'CC_13.3.8', '')]


class TestTaskSerialization(TestCase):
    def test_serialize_deserialize(self):
        self.assertListEqual(apr, json_to_tasklist(tasklist_to_json(apr)))


class MockTasksProvider(TaskProvider):
    def get_tasks(self, pat, date_from, date_to) -> list[Task]:
        if date_from == '01-04-2023' and date_to == '30-04-2023':
            return apr
        if date_from == '01-05-2023' and date_to == '31-05-2023':
            return may
        raise ValueError


class TestSnapshotManager(TestCase):
    def test_id2_decoding(self):
        in_from = '01-05-2023'
        in_to = '31-05-2023'
        x = SnapshotManager.id2_encode(in_from, in_to)
        out_from, out_to = SnapshotManager.id2_decode(x)
        self.assertEqual(in_from, out_from)
        self.assertEqual(in_to, out_to)

    def test_id3_decoding(self):
        in_from = '01-05-2023'
        in_to = '31-05-2023'
        in_mtime = datetime.now().astimezone().timestamp()
        x = SnapshotManager.id3_encode(in_from, in_to, in_mtime)
        out_from, out_to, out_mtime = SnapshotManager.id3_decode(x)
        self.assertEqual(in_from, out_from)
        self.assertEqual(in_to, out_to)
        self.assertAlmostEqual(in_mtime, out_mtime)

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
        u = a[0].mtime

        with self.assertRaises(KeyError):
            sm.snapshot_get_tasks('01-04-2000', '30-04-2000', u)

        b = sm.snapshot_get_tasks('01-04-2023', '30-04-2023', u)
        self.assertListEqual(b, apr)


class TestSnapshotStorage(TestCase):
    pass
