#!/usr/bin/python3
from subprocess import call
from sys import platform
from datetime import datetime as dt, timezone, timedelta
from tempfile import mkstemp
from typing import Tuple
from progress.bar import Bar
import os

from src.ArgsTypes import parse_args
from src.Handlers import HandlerCai, HandlerIS, HandlerLingvo
from src.Matrix import Matrix, ExcelPrinter, ServiceAssignmentsMatrix, get_bundle_zip, DocsGenerator
from src.Task import DiskSnapshotStorage, SnapshotManager, Task, TaskProvider
from src.AI import Cache, SQlite, ChatGPT


class TFS_TaskProvider(TaskProvider):
    def get_tasks(self, pat, date_from, date_to) -> list[Task]:
        out = []
        handlers = (HandlerCai, HandlerIS, HandlerLingvo)
        with Bar('Loading tasks from the TFS:', max=len(handlers)) as bar:
            for h in handlers:
                out += h(pat, date_from, date_to).tasks
                bar.next()
        return out


def get_next(sm: SnapshotManager) -> Tuple[str, str]:
    d = [(dt.strptime(x.date_to, '%d-%m-%Y'), x) for x in sm.snapshots_list()]
    dt_recent = dt.strptime(sorted(d)[0][1].date_to, '%d-%m-%Y')
    date_fr = dt.strftime(dt_recent + timedelta(1), '%d-%m-%Y')
    date_to = dt.strftime(dt.now() - timedelta(1), '%d-%m-%Y')
    return (date_fr, date_to)


def get_the_earliest(dates: list[str]) -> str:
    d = [(dt.strptime(x, '%d-%m-%Y'), x) for x in dates]
    return sorted(d, reverse=False)[0][1]


def get_the_latest(dates: list[str]) -> str:
    d = [(dt.strptime(x, '%d-%m-%Y'), x) for x in dates]
    return sorted(d, reverse=True)[0][1]


path_db_dir = './.db'
path_sqlite = './.essence_cache.sqlite'
path_templates = './templates'
fname_xslsx = {'prefix': 'tfs_excel_', 'suffix': '.xlsx'}
fname_zip = {'prefix': 'tfs_excel_', 'suffix': '.zip'}


def main():
    a = parse_args()
    file_out = None

    tp = TFS_TaskProvider()
    sm = SnapshotManager(DiskSnapshotStorage(path_db_dir), tp)
    if a.cache_fill is not None:
        date_from, date_to = ('', '')
        if isinstance(a.cache_fill, bool):
            date_from, date_to = get_next(sm)
        else:
            date_from, date_to = a.cache_fill
        c = Cache(SQlite(path_sqlite), ChatGPT(a.key, a.ai_rpm_limit))
        c.filter(tp.get_tasks(a.pat, date_from, date_to))

    elif a.draft_update is not None:
        date_from, date_to = ('', '')
        if isinstance(a.draft_update, bool):
            date_from, date_to = get_next(sm)
        else:
            date_from, date_to = a.draft_update
        sm.draft_update(a.pat, date_from, date_to)
        file_out = a.out if a.out is not None else mkstemp(**fname_xslsx)[1]
        with ExcelPrinter(file_out, date_from, date_to) as p:
            l = sm.draft_get_tasks(date_from, date_to)
            p.print(Matrix(l, a.names_reference), a.predefined_spend)

    elif a.draft_get is not None:
        x = sm.drafts_list()[a.draft_get]
        file_out = a.out if a.out is not None else mkstemp(**fname_xslsx)[1]
        with ExcelPrinter(file_out, x.date_from, x.date_to) as p:
            l = sm.draft_get_tasks(x.date_from, x.date_to)
            p.print(Matrix(l, a.names_reference), a.predefined_spend)

    elif a.draft_delete is not None:
        x = sm.drafts_list()[a.draft_delete]
        sm.draft_delete(x.date_from, x.date_to)

    elif a.drafts_list:
        for i, d in enumerate(sm.drafts_list()):
            x = dt.fromtimestamp(d.mtime, tz=timezone.utc).astimezone()
            print((f'#{i} from: {d.date_from}'
                   f' to: {d.date_to}'
                   f' mtime: {x.strftime("%d-%m-%Y %H:%M:%S.%f")}'))

    elif a.draft_approve is not None:
        x = sm.drafts_list()[a.draft_approve]
        sm.draft_approve(x.date_from, x.date_to)

    elif a.snapshots_list:
        for i, d in enumerate(sm.snapshots_list()):
            x = dt.fromtimestamp(d.mtime, tz=timezone.utc).astimezone()
            print((f'#{i} from: {d.date_from}'
                   f' to: {d.date_to}'
                   f' mtime: {x.strftime("%d-%m-%Y %H:%M:%S.%f")}'))

    elif a.snapshot_get is not None:
        fr, to, tasks = [], [], []
        for i in a.snapshot_get:
            x = sm.snapshots_list()[i]
            tasks += sm.snapshot_get_tasks(x.date_from, x.date_to, x.mtime)
            fr.append(x.date_from)
            to.append(x.date_to)
        date_fr = get_the_earliest(fr)
        date_to = get_the_latest(to)

        c = Cache(SQlite(path_sqlite), ChatGPT(a.key, a.ai_rpm_limit))
        s = ServiceAssignmentsMatrix(c.filter(tasks), a.names_reference)
        dg = DocsGenerator(path_templates)
        file_out = a.out if a.out is not None else mkstemp(**fname_zip)[1]
        with open(file_out, mode='wb') as f:
            f.write(get_bundle_zip(s, date_fr, date_to, a.predefined_spend, dg))

    if file_out:
        if a.no_open:
            print(f'The xlsx is saved into "{file_out}"')
        else:
            if platform in ("linux", "linux2"):
                call(["xdg-open", os.path.abspath(file_out)])
            else:
                os.startfile(out)


if __name__ == "__main__":
    main()
