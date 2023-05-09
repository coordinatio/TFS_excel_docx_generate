from datetime import datetime
from typing import List, Tuple


class Task:
    def __init__(self, title: str, assignees: List[str], release: str, link: str, date_created=None, date_closed=None) -> None:
        self.title = title
        self.assignees = [x for x in sorted(set(assignees))]
        self.release = release
        self.link = link
        self.date_created = date_created
        self.date_closed = date_closed
        self.broken = not self.title or not self.assignees


class SnapshotInfo:
    def __init__(self, date_from, date_to, mtime: float):
        self.date_from = date_from
        self.date_to = date_to
        self.mtime = mtime


class TaskProvider:
    def get_tasks(self, pat, date_from, date_to) -> list[Task]:
        raise NotImplementedError


class SnapshotStorage:
    def draft_write(self, draft_id: Tuple[str, str], tasks: List[Task]) -> None:
        raise NotImplementedError

    def drafts_list(self) -> dict[Tuple[str, str], float]:
        #                         ID   mtime
        raise NotImplementedError

    def draft_read(self, draft_id: Tuple[str, str]) -> list[Task]:
        raise NotImplementedError

    def draft_approve(self, draft_id: Tuple[str, str]):
        raise NotImplementedError

    def snapshots_list(self) -> list[Tuple[Tuple[str, str], float]]:
        raise NotImplementedError

    def snapshot_read(self, snap_id: Tuple[Tuple[str, str], float]) -> list[Task]:
        # snap_id == (ID, mtime)
        raise NotImplementedError


class SnapshotManager:
    def __init__(self, ss: SnapshotStorage, tp: TaskProvider):
        self.s = ss
        self.p = tp

    def draft_update(self, pat, date_from, date_to):
        tasks = self.p.get_tasks(pat, date_from, date_to)
        self.s.draft_write((date_from, date_to), tasks)

    def drafts_list(self) -> list[SnapshotInfo]:
        return [SnapshotInfo(k[0], k[1], v) for k, v in self.s.drafts_list().items()]

    def draft_get_tasks(self, date_from, date_to) -> list[Task]:
        return self.s.draft_read((date_from, date_to))

    def draft_approve(self, date_from, date_to):
        self.s.draft_approve((date_from, date_to))

    def snapshots_list(self) -> list[SnapshotInfo]:
        return [SnapshotInfo(x[0][0], x[0][1], x[1]) for x in self.s.snapshots_list()]

    def snapshot_get_tasks(self, date_from, date_to) -> list[Task]:
        return self.s.snapshot_read((date_from, date_to))
