#!/usr/bin/python3
from subprocess import call
from sys import platform
from datetime import datetime, timezone, timedelta
import os

from src.ArgsTypes import parse_args
from src.Handlers import HandlerCai, HandlerIS, HandlerLingvo
from src.Matrix import Matrix, ExcelPrinter, DocxPrinter
from src.Task import DiskSnapshotStorage, SnapshotManager, Task, TaskProvider

class TFS_TaskProvider(TaskProvider):
    def get_tasks(self, pat, date_from, date_to) -> list[Task]:
        out = []
        for x in (HandlerCai, HandlerIS, HandlerLingvo):
            out += x(pat, date_from, date_to).tasks
        return out

def main():
    a = parse_args()

    sm = SnapshotManager(DiskSnapshotStorage('./.db'), TFS_TaskProvider())
    if a.draft_update is not None:
        date_from = ''
        date_to = ''
        if isinstance(a.draft_update, bool):
            date_from = sorted([(datetime.strptime(x.date_to, '%d-%m-%Y'), x) for x in sm.snapshots_list()])[0][1].date_to
            date_to = datetime.strftime(datetime.now() - timedelta(1), '%d-%m-%Y')
        else:
            date_from = a.draft_update[0]
            date_to = a.draft_update[1]
        sm.draft_update(a.pat, date_from, date_to)
        with ExcelPrinter(a.out, date_from, date_to) as p:
            l = sm.draft_get_tasks(date_from, date_to)
            p.print(Matrix(l, a.names_reference), a.predefined_spend)

    elif a.draft_get is not None:
        x = sm.drafts_list()[a.draft_get]
        with ExcelPrinter(a.out, x.date_from, x.date_to) as p:
            l = sm.draft_get_tasks(x.date_from, x.date_to)
            p.print(Matrix(l, a.names_reference), a.predefined_spend)

    elif a.drafts_list:
        for i, d in enumerate(sm.drafts_list()):
            x = datetime.fromtimestamp(d.mtime, tz=timezone.utc).astimezone()
            print(f'#{i} from: {d.date_from} to: {d.date_to} mtime: {x.strftime("%d-%m-%Y %H:%M:%S.%f")}')

    elif a.draft_approve is not None:
        x = sm.drafts_list()[a.draft_approve]
        sm.draft_approve(x.date_from, x.date_to)

    elif a.snapshots_list:
        for i, d in enumerate(sm.snapshots_list()):
            x = datetime.fromtimestamp(d.mtime, tz=timezone.utc).astimezone()
            print(f'#{i} from: {d.date_from} to: {d.date_to} mtime: {x.strftime("%d-%m-%Y %H:%M:%S.%f")}')

    elif a.snapshot_get is not None:
        x = sm.snapshots_list()[a.snapshots_list]
        with ExcelPrinter(a.out, x.date_from, x.date_to) as p:
            l = sm.snapshot_get_tasks(x.date_from, x.date_to, x.mtime)
            p.print(Matrix(l, a.names_reference), a.predefined_spend)


    # test = DocxPrinter()
    # test.create_zip(Matrix(i, a.names_reference))

    if any(x is not None for x in (a.draft_get, a.draft_update, a.snapshot_get)):
        if a.no_open:
            print(f'The xlsx is saved into "{a.out}"')
        else:
            if platform in ("linux", "linux2"):
                call(["xdg-open", os.path.abspath(a.out)])
            else:
                os.startfile(a.out)


if __name__ == "__main__":
    main()
