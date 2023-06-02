import json
import pathlib
from typing import List


class Task:
    def __init__(self, title: str, assignees: List[str], release: str, link: str, **kwargs) -> None:
        self.assignees = [x for x in sorted(
            set(kwargs['assignees'] if 'assignees' in kwargs else assignees))]
        self.title = kwargs['title'] if 'title' in kwargs else title
        self.release = kwargs['release'] if 'release' in kwargs else release
        self.link = kwargs['link'] if 'link' in kwargs else link
        self.tid = kwargs['tid'] if 'tid' in kwargs else None
        self.parent_title = kwargs['parent_title'] if 'parent_title' in kwargs else None
        self.project = kwargs['project'] if 'project' in kwargs else None
        self.essence = ''
        self.essence_completed = ''
        self.body = kwargs['body'] if 'body' in kwargs else None

    def __eq__(self, other) -> bool:
        if len(self.assignees) != len(other.assignees):
            return False
        for x in zip(self.assignees, other.assignees):
            if x[0] != x[1]:
                return False
        for k in ('title', 'release', 'link'):
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


class DiskSnapshotStorage(SnapshotStorage):
    def __init__(self, path_to_the_storage: str) -> None:
        self.path = pathlib.Path(path_to_the_storage)
        if not self.path.exists():
            self.path.mkdir()

    def write(self, storage_id: str, data_id: str, data: str) -> None:
        s_id = self.path / storage_id
        if not s_id.exists():
            s_id.mkdir()
        with open(s_id / data_id, mode='w') as f:
            f.write(data)

    def list(self, storage_id: str) -> dict[str, float]:
        return {x.name: x.stat().st_mtime for x in (self.path / storage_id).iterdir()}

    def read(self, storage_id: str, data_id: str) -> str:
        with open(self.path / storage_id / data_id, mode='r') as f:
            return f.read()

    def delete(self, storage_id: str, data_id: str) -> None:
        (self.path / storage_id / data_id).unlink()


class SnapshotManager:
    def __init__(self, ss: SnapshotStorage, tp: TaskProvider):
        self.s = ss
        self.p = tp

    @staticmethod
    def id2_encode(date_from: str, date_to: str) -> str:
        return f'{date_from}_{date_to}'

    @staticmethod
    def id2_decode(data_id: str) -> tuple[str, str]:
        x = data_id.index('_')
        return (data_id[:x], data_id[x+1:])

    @staticmethod
    def id3_encode(date_from: str, date_to: str, mtime: float) -> str:
        return f'{date_from}_{date_to}_{mtime}'

    @staticmethod
    def id3_decode(data_id: str) -> tuple[str, str, float]:
        x = data_id.index('_')
        y = data_id.index('_', x+1)
        return (data_id[:x], data_id[x+1:y], float(data_id[y+1:]))

    def draft_update(self, pat, date_from, date_to):
        t = self.p.get_tasks(pat, date_from, date_to)
        x = self.id2_encode(date_from, date_to)
        self.s.write('drafts', x, tasklist_to_json(t))

    def drafts_list(self) -> list[SnapshotInfo]:
        out = []
        for data_id, mtime in self.s.list('drafts').items():
            date_from, date_to = self.id2_decode(data_id)
            out.append(SnapshotInfo(date_from, date_to, mtime))
        return out

    def draft_delete(self, date_from: str, date_to: str) -> None:
        self.s.delete('drafts', self.id2_encode(date_from, date_to))

    def draft_get_tasks(self, date_from, date_to) -> list[Task]:
        x = self.s.read('drafts', self.id2_encode(date_from, date_to))
        return json_to_tasklist(x)

    def draft_approve(self, date_from, date_to):
        id2 = self.id2_encode(date_from, date_to)
        f = self.s.list('drafts')[id2]
        x = self.s.read('drafts', id2)
        self.s.write('snapshots', self.id3_encode(date_from, date_to, f), x)
        self.s.delete('drafts', id2)

    def snapshots_list(self) -> list[SnapshotInfo]:
        out = []
        for data_id in self.s.list('snapshots'):
            date_from, date_to, mtime = self.id3_decode(data_id)
            out.append(SnapshotInfo(date_from, date_to, mtime))
        return out

    def snapshot_get_tasks(self, date_from, date_to, mtime) -> list[Task]:
        x = self.s.read('snapshots', self.id3_encode(
            date_from, date_to, mtime))
        return json_to_tasklist(x)
