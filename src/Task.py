from typing import List
from datetime import datetime


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
    def __init__(self, date_from, date_to, datetime_updated: datetime, is_approved):
        self.date_from = date_from
        self.date_to = date_to
        self.datetime_updated = datetime_updated
        self.is_approved = is_approved


class TaskProvider:
    pass


class SnapshotStorage:
    pass


class SnapshotManager:
    def __init__(self, st: SnapshotStorage, tp: TaskProvider):
        pass

    def stage_update(self, pat, date_from, date_to):
        pass

    def stage_list(self) -> list[SnapshotInfo]:
        return []
