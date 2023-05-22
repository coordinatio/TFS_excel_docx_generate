#!/usr/bin/python3
from os import path
from subprocess import call
from sys import platform
from datetime import datetime, timezone

from src.ArgsTypes import parse_args
from src.Handlers import HandlerCai, HandlerIS, HandlerLingvo
from src.Matrix import Matrix, ExcelPrinter, DocxPrinter
from src.Task import DiskSnapshotStorage, SnapshotManager, SnapshotStorage, Task, TaskProvider

class TFS_TaskProvider(TaskProvider):
    def get_tasks(self, pat, date_from, date_to) -> list[Task]:
        out = []
        for x in (HandlerCai, HandlerIS, HandlerLingvo):
            out += x(pat, date_from, date_to).tasks
        return out

def main():
    a = parse_args()

    sm = SnapshotManager(DiskSnapshotStorage('./.db'), TFS_TaskProvider())
    if a.draft_update:
        sm.draft_update(a.pat, a.date_from, a.date_to)
        with ExcelPrinter(a.out, a.date_from, a.date_to) as p:
            l = sm.draft_get_tasks(a.date_from, a.date_to)
            p.print(Matrix(l, a.names_reference), a.predefined_spend)

    elif a.draft_get:
        with ExcelPrinter(a.out, a.date_from, a.date_to) as p:
            l = sm.draft_get_tasks(a.date_from, a.date_to)
            p.print(Matrix(l, a.names_reference), a.predefined_spend)

    elif a.drafts_list:
        for i, d in enumerate(sm.drafts_list()):
            x = datetime.fromtimestamp(d.mtime, tz=timezone.utc)
            print(f'#{i} from: {d.date_from} to: {d.date_to} mtime: {x.strftime("%d-%m-%Y %H:%M:%S.%f")}')

    elif a.draft_approve:
        sm.draft_approve(a.date_from, a.date_to)

    elif a.snapshots_list:
        for i, d in enumerate(sm.snapshots_list()):
            x = datetime.fromtimestamp(d.mtime, tz=timezone.utc)
            print(f'#{i} from: {d.date_from} to: {d.date_to} mtime: {x.strftime("%d-%m-%Y %H:%M:%S.%f")}')

    else:
        i = []
        for x in (HandlerCai, HandlerIS, HandlerLingvo):
            i += x(a.pat, vars(a)["from"], vars(a)["to"]).tasks

        with ExcelPrinter(a.out, a.date_from, a.date_to) as p:
            p.print(Matrix(i, a.names_reference), a.predefined_spend)

        # test = DocxPrinter()
        # test.create_zip(Matrix(i, a.names_reference))

    if a.open and (a.draft_get or a.draft_update or a.snapshot_get):
        if platform in ("linux", "linux2"):
            call(["xdg-open", path.abspath(a.out)])
        else:
            print("--open works only on linux yet")


if __name__ == "__main__":
    main()
