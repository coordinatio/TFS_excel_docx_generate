import json
from typing import List


class Task:
    def __init__(self, title: str, assignees: List[str], release: str, link: str, date_created=None, date_closed=None, **kwargs) -> None:
        self.assignees = [x for x in sorted(
            set(kwargs['assignees'] if 'assignees' in kwargs else assignees))]
        self.title = kwargs['title'] if 'title' in kwargs else title
        self.release = kwargs['release'] if 'release' in kwargs else release
        self.link = kwargs['link'] if 'link' in kwargs else link
        self.date_created = kwargs['date_created'] if 'date_created' in kwargs else date_created
        self.date_closed = kwargs['date_closed'] if 'date_closed' in kwargs else date_closed
        self.broken = not self.title or not self.assignees

    def __eq__(self, other) -> bool:
        if len(self.assignees) != len(other.assignees):
            return False
        for x in zip(self.assignees, other.assignees):
            if x[0] != x[1]:
                return False
        for k in ('title', 'release', 'link', 'date_created', 'date_closed'):
            if k not in other.__dict__ or self.__dict__[k] != other.__dict__[k]:
                return False
        return True
        


def tasklist_to_json(tasklist: List[Task]) -> str:
    return json.dumps([x.__dict__ for x in tasklist], sort_keys=True, indent=4)


def json_to_tasklist(tasklist_json: str) -> List[Task]:
    return [Task(**a) for a in json.loads(tasklist_json)]


class SnapshotInfo:
    def __init__(self, date_from, date_to, mtime: float):
        self.date_from = date_from
        self.date_to = date_to
        self.mtime = mtime


class TaskProvider:
    def get_tasks(self, pat, date_from, date_to) -> list[Task]:
        raise NotImplementedError


class SnapshotStorage:
    def write(self, storage_id: str, data_id: str, data: str) -> None:
        """Writes data identified by data_id into storage identified by storage_id"""
        raise NotImplementedError

    def list(self, storage_id: str) -> dict[str, float]:
        """List data available by it's data_id and mtime

        Returns:
            dict[str, float]: a dict of data_id -> mtime
        """
        raise NotImplementedError

    def read(self, storage_id: str, data_id: str) -> str:
        """Reads the data identified by the data_id from the storage identified by the storage_id"""
        raise NotImplementedError

    def delete(self, storage_id: str, data_id: str) -> None:
        raise NotImplementedError


class SnapshotManager:
    def __init__(self, ss: SnapshotStorage, tp: TaskProvider):
        self.s = ss
        self.p = tp

    # def draft_update(self, pat, date_from, date_to):
    #     tasks = self.p.get_tasks(pat, date_from, date_to)
    #     self.s.draft_write((date_from, date_to), tasks)

    # def drafts_list(self) -> list[SnapshotInfo]:
    #     return [SnapshotInfo(k[0], k[1], v) for k, v in self.s.drafts_list().items()]

    # def draft_get_tasks(self, date_from, date_to) -> list[Task]:
    #     return self.s.draft_read((date_from, date_to))

    # def draft_approve(self, date_from, date_to):
    #     self.s.draft_approve((date_from, date_to))

    # def snapshots_list(self) -> list[SnapshotInfo]:
    #     return [SnapshotInfo(x[0][0], x[0][1], x[1]) for x in self.s.snapshots_list()]

    # def snapshot_get_tasks(self, date_from, date_to) -> list[Task]:
    #     return self.s.snapshot_read((date_from, date_to))
