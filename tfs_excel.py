#!/usr/bin/python3
from json import JSONDecoder
from typing import Dict, List, OrderedDict
from tfs import TFSAPI
import os
import xlsxwriter
import re
import argparse
import datetime
import subprocess
import sys
import unittest


class ArgsTypes:
    @staticmethod
    def validate_names_reference(d: dict):
        msg = 'Names json has incorrect structure, must be flat str->str pairs'
        if type(d) is not dict:
            raise argparse.ArgumentTypeError(msg)
        for k in d:
            if type(k) is not str or type(d[k]) is not str:
                raise argparse.ArgumentTypeError(msg)

    @staticmethod
    def arg_names_reference_file(path_to_file: str) -> dict:
        """reads file, parses json, validates contents
        returns dict with incorrect -> correct name pairs"""
        j = {}
        if not path_to_file:
            return j
        if not os.path.exists(path_to_file):
            raise argparse.ArgumentTypeError(
                "Names reference file %s does not exist" % path_to_file)
        try:
            with open(path_to_file, 'r') as f:
                j = JSONDecoder().decode(f.read())
        except:
            raise argparse.ArgumentTypeError(
                "%s contains invalid json" % path_to_file)
        ArgsTypes.validate_names_reference(j)
        return j


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pat',
                        default="fmzzuj6opqc2yv2zspw2uoiz73k5iwa5q2v25nzcwyztg5oqtw3q")
    parser.add_argument('--from',
                        type=lambda d: datetime.datetime.strptime(
                            d, '%d-%m-%Y').date().strftime("%d-%m-%Y"),
                        help='dd-mm-YYYY', required=True)
    parser.add_argument('--to',
                        type=lambda d: datetime.datetime.strptime(
                            d, '%d-%m-%Y').date().strftime("%d-%m-%Y"),
                        help='dd-mm-YYYY', required=True)
    parser.add_argument("--out", default="time_report.xlsx",
                        help="File to put results into")
    parser.add_argument("--open", action='store_true', default=False,
                        help="Tells if to open the resulting file immediately after creation")
    parser.add_argument('--names_reference', type=ArgsTypes.arg_names_reference_file,
                        default='name_filter.json',
                        help="Path to the file containing json with name pairs")
    return parser.parse_args()


class Task:
    def __init__(self, title, assignees, release, link) -> None:
        self.title = title
        self.assignees = assignees
        self.release = release
        self.link = link
        self.broken = not self.title or not self.assignees


class Handler():
    def __init__(self, pat, date_from, date_to) -> None:
        tasks = []
        for w in self.retrieve(pat, date_from, date_to):
            tasks.append(Task(self.get_title(w),
                              self.get_assignees(w),
                              self.get_release(w),
                              self.get_link(w)))
        self.workitems = tasks

    def get_assignees(self, workitem):
        assignees = []
        if (workitem['AssignedTo']):
            assignees.append(
                str(workitem['AssignedTo'][:workitem['AssignedTo'].find(' <')]))
        if workitem['Tags']:
            m = re.search(r'[\@#]([А-Яа-яё]+[_ ][А-Яа-яё]+)', workitem['Tags'])
            if m:
                assignees.append(str(m.group(1).replace('_', ' ')))
        return assignees

    def retrieve(self, pat, date_from, date_to):
        return []

    def get_title(self, workitem):
        return str(workitem['Title'])

    def get_release(self, workitem):
        pass

    def get_link(self, workitem):
        return str(workitem._links['html']['href'])


class HandlerCai(Handler):
    def retrieve(self, pat, date_from, date_to):
        q = """SELECT [System.AssignedTo], [Tags]
        FROM workitems
        WHERE 
            [System.State] = 'Done' 
            AND [System.WorkItemType] = 'Task' 
            AND ([Closed Date] >= '%s' AND [Closed Date] <= '%s')
            AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
        ORDER BY [System.AssignedTo]
        """ % (date_from, date_to)
        return TFSAPI("https://tfs.content.ai/", project="HQ/ContentAI", pat=pat).run_wiql(q).workitems

    def get_release(self, workitem):
        w = workitem
        while True:
            if w['Tags']:
                m = re.search(r'[A-Z]+_\d+\.\d+\.\d+', w['Tags'])
                if m:
                    return str(m.group(0))
            if not w.parent:
                return ''
            w = w.parent


class HandlerIS(Handler):
    def retrieve(self, pat, date_from, date_to):
        q = """SELECT [System.AssignedTo], [Tags]
        FROM workitems
        WHERE 
            [System.State] = 'Closed' 
            AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Task') 
            AND ([Closed Date] >= '%s' AND [Closed Date] <= '%s')
            AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
        ORDER BY [System.AssignedTo]
        """ % (date_from, date_to)
        return TFSAPI("https://tfs.content.ai/", project="NLC/AIS", pat=pat).run_wiql(q).workitems

    def get_release(self, workitem):
        m = re.search(r'AIS\\(\d+\.\d+)', workitem['system.areapath'])
        if m:
            return "IS_%s" % str(m.group(1))
        return ''


class HandlerLingvo(Handler):
    def retrieve(self, pat, date_from, date_to):
        q = """SELECT [System.AssignedTo], [Tags]
        FROM workitems
        WHERE 
            [System.State] = 'Closed' 
            AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Feature')  
            AND ([Closed Date] >= '%s' AND [Closed Date] <= '%s')
            AND [System.Tags] NOT CONTAINS 'EXCLUDE_FROM_TIME_REPORTS'
        ORDER BY [System.AssignedTo]
        """ % (date_from, date_to)
        w = []
        for p in ('Lingvo', 'LingvoLive'):
            w += TFSAPI("https://tfs.content.ai/", project=p,
                        pat=pat).run_wiql(q).workitems
        return w

    def get_release(self, workitem):
        spec_a = {'Lingvo X6': 'LX6',
                  'lingvo.mobile.iOS': 'LMI',
                  'lingvo.mobile.android': 'LMA',
                  'lingvo.mac': 'LFM',
                  'lingvo.live.ios': 'LLI'}
        m = re.search(r'(.+?)\\(.+\\)?(\d+\.\d+(\.\d+)?)',
                      workitem['system.iterationpath'])
        if m:
            prj = m.group(1)
            ver = m.group(3)
            if prj in spec_a:
                return '%s_%s' % (spec_a[prj], ver)
        spec_b = {'lingvo.mobile.services': 'LLB',
                  'lingvo.live.services': 'LLB',
                  'lingvo.live.web': 'LLWW'}
        m = re.search(r'(.+?)\\.*', workitem['system.iterationpath'])
        if m:
            prj = m.group(1)
            if prj in spec_b:
                return spec_b[prj]
        return ''


class NameNormalizer:
    def __init__(self, ref) -> None:
        self.dict = ref

    def normalize(self, s: str) -> str:
        if s in self.dict:
            return self.dict[s]
        return s


class Matrix:
    class AssigneeInfo:
        def __init__(self, releases_ever_known: set) -> None:
            self.tasks_ttl = 0
            self.releases = OrderedDict()
            for r in releases_ever_known:
                self.releases[r] = []
            self.default = []  # here all not release related tasks go

        def add_task(self, release: str, task: Task):
            if release:
                self.releases[release].append(task)
            else:
                self.default.append(task)
            self.tasks_ttl += 1

    def __init__(self, tasks: List, names_reference={}):
        self.releases_ever_known = {t.release for t in tasks if t.release}
        self.nn = NameNormalizer(names_reference)
        self.rows = OrderedDict()
        for t in tasks:
            for a in t.assignees:
                self.add_record(a, t.release, t)
        for x in [y for y in names_reference.values() if y not in self.rows]:
            self.rows[x] = Matrix.AssigneeInfo(self.releases_ever_known)

    def add_record(self, assignee: str, release: str, task: Task):
        a = self.nn.normalize(assignee)
        if a not in self.rows:
            self.rows[a] = Matrix.AssigneeInfo(self.releases_ever_known)
        self.rows[a].add_task(release, task)


class MatrixPrinter:
    def print(self, m: Matrix):
        header = [x for x in sorted(m.releases_ever_known)]
        col = 0
        for x in [''] + header + ['DEFAULT']:
            self.brush(col, 0, x)
            col += 1
        row = 0
        for y in m.rows:
            col = 0
            row += 1
            if m.rows[y].tasks_ttl == 0:
                self.brush_highlight(col, row, y)
                self.brush_comment(col, row,
                                    'Нет задач за отчётный период, скорректируйте табличку вручную.')
            else:
                self.brush(col, row, y)

            for x in header:
                col += 1
                if m.rows[y].tasks_ttl == 0:
                    self.brush_percent(col, row, 0)
                else:
                    self.brush_percent(col, row, len(
                        m.rows[y].releases[x])/m.rows[y].tasks_ttl)
                comment = ["%s: %s\n" % (t.title, t.link)
                           for t in m.rows[y].releases[x]]
                if comment:
                    self.brush_comment(col, row, "\n".join(comment))
            col += 1
            if m.rows[y].tasks_ttl == 0:
                self.brush_percent(col, row, 0)
            else:
                self.brush_percent(col, row, len(
                    m.rows[y].default)/m.rows[y].tasks_ttl)
            comment = ["%s: %s\n" % (t.title, t.link)
                       for t in m.rows[y].default]
            if comment:
                self.brush_comment(col, row, "\n".join(comment))

    def brush(self, col, row, x):
        pass

    def brush_percent(self, col, row, x):
        self.brush(col, row, x)

    def brush_highlight(self, col, row, x):
        self.brush(col, row, x)

    def brush_comment(self, col, row, x):
        pass


class ExcelPrinter(MatrixPrinter):
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def __enter__(self):
        self.book = xlsxwriter.Workbook(self.filename)
        self.sheet = self.book.add_worksheet()

        self.fmt_percent = self.book.add_format()
        self.fmt_percent.set_num_format('0.00%')

        self.fmt_gray = self.book.add_format({'font_color': '#eeeeee'})
        self.sheet.conditional_format(0, 0, 999, 999, {'type':     'cell',
                                                       'criteria': '=',
                                                       'value':    0,
                                                       'format':   self.fmt_gray})

        self.fmt_highlight = self.book.add_format({'bg_color': '#ffff7f'})
        return self

    def __exit__(self, *args):
        self.sheet.autofit()
        self.sheet.freeze_panes(1, 1)
        self.book.close()

    def brush(self, col, row, x):
        self.sheet.write(row, col, x)

    def brush_percent(self, col, row, x):
        self.sheet.write(row, col, x, self.fmt_percent)

    def brush_highlight(self, col, row, x):
        self.sheet.write(row, col, x, self.fmt_highlight)

    def brush_comment(self, col, row, x):
        self.sheet.write_comment(row, col, x)


def main():
    a = parse_args()

    i = []
    for x in (HandlerCai, HandlerIS, HandlerLingvo):
        i += x(a.pat, vars(a)["from"], vars(a)["to"]).workitems

    with ExcelPrinter(a.out) as p:
        p.print(Matrix(i, a.names_reference))

    if (a.open):
        if sys.platform in ("linux", "linux2"):
            subprocess.call(["xdg-open", a.out])
        else:
            print("--open works only on linux yet")


if __name__ == "__main__":
    main()


class MockWorkitem:
    def __init__(self, d: Dict, link='') -> None:
        self.parent = None
        self.d = d
        self._links = {'html': {'href': link}}

    def __getitem__(self, key):
        return self.d[key]


class TestAssigneeExtraction(unittest.TestCase):
    def test_cai_happyday(self):
        d = {'AssignedTo': 'Алексей Калюжный <CONTENT\\AKalyuzhny>',
             'Tags': '@Федор_Симашев; CC_12.8.0',
             'Title': 'Test title'}

        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                return [MockWorkitem(d)]
        self.assertEqual(X('', '', '').workitems[0].assignees, [
                         'Алексей Калюжный', 'Федор Симашев'])

    def test_cai_no_tags(self):
        d = {'AssignedTo': 'Алексей Калюжный <CONTENT\\AKalyuzhny>',
             'Tags': None,
             'Title': 'Test title'}

        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                return [MockWorkitem(d)]
        self.assertEqual(X('', '', '').workitems[0].assignees, [
                         'Алексей Калюжный'])

    def test_cai_hashtag(self):
        d = {'AssignedTo': 'Алексей Калюжный <CONTENT\\AKalyuzhny>',
             'Tags': '#Федор_Симашев; CC_12.8.0',
             'Title': 'Test title'}

        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                return [MockWorkitem(d)]
        self.assertEqual(X('', '', '').workitems[0].assignees, [
                         'Алексей Калюжный', 'Федор Симашев'])


class TestReleaseExtraction(unittest.TestCase):
    def test_cai_happyday(self):
        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': '@Федор_Симашев; Garbage',
                     'Title': 'Test title'}
                w = MockWorkitem(d)
                w.parent = MockWorkitem(
                    {'AssignedTo': '', 'Tags': 'CC_12.8.0', 'Title': 'T'})
                return [w]
        self.assertEqual('CC_12.8.0', X('', '', '').workitems[0].release)

    def test_cai_no_tags(self):
        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': None,
                     'Title': 'Test title'}
                w = MockWorkitem(d)
                w.parent = MockWorkitem(
                    {'AssignedTo': '', 'Tags': 'CC_12.8.0', 'Title': 'T'})
                return [w]
        self.assertEqual('CC_12.8.0', X('', '', '').workitems[0].release)

    def test_is_happyday(self):
        class X(HandlerIS):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': '@Федор_Симашев; Garbage',
                     'Title': 'Test title',
                     'system.areapath': 'AIS\\5.2'}
                return [MockWorkitem(d)]
        self.assertEqual('IS_5.2', X('', '', '').workitems[0].release)

    def test_lx6_happyday(self):
        class X(HandlerLingvo):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': '@Федор_Симашев; Garbage',
                     'Title': 'Test title',
                     'system.iterationpath': 'Lingvo X6\\16.3.1'}
                return [MockWorkitem(d)]
        self.assertEqual('LX6_16.3.1', X('', '', '').workitems[0].release)


class TestMatrix(unittest.TestCase):
    def test_happyday(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://')
        m = Matrix([t1, t2])
        self.assertEqual(m.rows['Petr'].tasks_ttl, 2)
        self.assertEqual(m.rows['Foma'].tasks_ttl, 1)
        self.assertTrue('FTW_13.3.7' in m.rows['Petr'].releases)

    def test_name_normalization(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://')
        t3 = Task('C', ['Ptr'], 'FTW_13.3.7', 'http://')
        m = Matrix([t1, t2, t3], {"Ptr": "Petr", "x": "y"})
        self.assertEqual(m.rows['Petr'].tasks_ttl, 3)
        self.assertEqual(m.rows['Foma'].tasks_ttl, 1)
        self.assertTrue('FTW_13.3.7' in m.rows['Petr'].releases)

    def test_empty_assignee_control(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://')
        m = Matrix([t1, t2], {"Ptr": "Petr", "x": "Empty", "y": "Empty"})
        self.assertEqual(m.rows['Empty'].tasks_ttl, 0)



class TestMatrixPrinter(unittest.TestCase):

    class TestPrinter(MatrixPrinter):
        def __init__(self) -> None:
            self.paper = [['']]
            self.paper_comments = [['']]
            self.paper_highlights = [['']]

        def brush(self, col, row, x):
            TestMatrixPrinter.TestPrinter._print(self.paper, col, row, x)

        def brush_comment(self, col, row, x):
            TestMatrixPrinter.TestPrinter._print(
                self.paper_comments, col, row, x)

        def brush_highlight(self, col, row, x):
            TestMatrixPrinter.TestPrinter._print(
                self.paper_highlights, col, row, x)

        @staticmethod
        def _print(p, col, row, x):
            if len(p) < col + 1:
                p += [[''] for x in range(col + 1 - len(p))]
            for i, l in enumerate(p):  # extend all rows
                if len(l) < row + 1:
                    p[i] += ['' for x in range(row + 1 - len(l))]
            p[col][row] = x

        # nicely print contents into string
        def __str__(self) -> str:
            out = ''
            for row in range(len(self.paper[0])):
                for col in range(len(self.paper)):
                    out += "%s, " % self.paper[col][row]
                out += '\n'
            return out

    def test_sheet(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://')
        l = TestMatrixPrinter.TestPrinter()
        l.print(Matrix([t1, t2]))
        out = [['', 'Petr', 'Foma'],
               ['FTW_13.3.7', 0.5, 0.0],
               ['OMG_13.3.8', 0.5, 1.0],
               ['DEFAULT', 0.0, 0.0]]
        for i, col in enumerate(l.paper):
            self.assertListEqual(out[i], col)

    def test_comments(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://A')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://B')
        l = TestMatrixPrinter.TestPrinter()
        l.print(Matrix([t1, t2], {'x': 'A person with no tasks'}))
        out = [['', '', '', 'Нет задач за отчётный период, скорректируйте табличку вручную.'],
               ['', 'A: http://A\n', '', ''],
               ['', 'B: http://B\n', 'B: http://B\n', '']]
        for i, col in enumerate(l.paper_comments):
            self.assertListEqual(out[i], col)

    def test_hightlights(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://A')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://B')
        l = TestMatrixPrinter.TestPrinter()
        l.print(Matrix([t1, t2], {'x' : 'Empty', 'y' : 'Empty'}))
        out = [['', '', '', 'Empty']]
        for i, col in enumerate(l.paper_highlights):
            self.assertListEqual(out[i], col)

    def test_excel_printer(self):
        t1 = Task('Task 1 with very very long description like you can find in real life',
                  ['Petr'], 'FTW_13.3.7', 'http://task1/adsfakjhdslfkjahdlskfjhaldsfhadf/adlskfj')
        t2 = Task('Task 2', ['Sheph', 'Petr'], 'OMG_13.3.8', 'http://task2')
        t3 = Task('Task 3 with very very long description like you can find in real life',
                  ['Petr'], 'FTW_13.3.7', 'http://task3/asdfupfasdfbdsfdsfasdfadv/asdfefwewdf')
        with ExcelPrinter('test_excel_printer.xlsx') as printer:
            printer.print(Matrix([t1, t2, t3], {'x': 'Empty'}))


class TestNameFilter(unittest.TestCase):
    def test_filtration(self):
        src = ['a', 'b']
        nf = NameNormalizer({"a": "1", "b": "2", "c" : "2"})
        dst = [nf.normalize(x) for x in src]
        self.assertListEqual(['1', '2'], dst)


class TestNamesReferenceValidator(unittest.TestCase):
    def test_valid(self):
        j = '{"a" : "b", "s" : "b", "d" : "f"}'
        ArgsTypes.validate_names_reference(JSONDecoder().decode(j))

    def test_invalid1(self):
        j = '{"a" : "b", "s" : {"x" : "y"}}'
        with self.assertRaises(argparse.ArgumentTypeError):
            ArgsTypes.validate_names_reference(JSONDecoder().decode(j))

    def test_invalid2(self):
        j = '{"a" : "b", "s" : ["x", "y"]}'
        with self.assertRaises(argparse.ArgumentTypeError):
            ArgsTypes.validate_names_reference(JSONDecoder().decode(j))

    def test_invalid3(self):
        j = '["a", "s"]'
        with self.assertRaises(argparse.ArgumentTypeError):
            ArgsTypes.validate_names_reference(JSONDecoder().decode(j))
