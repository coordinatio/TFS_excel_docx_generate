from unittest import TestCase
from tempfile import mkdtemp, mkstemp
from pathlib import Path
from shutil import copy, rmtree

from src.Task import Task
from src.Matrix import ExcelPrinter, Matrix, MatrixPrinter, NameNormalizer, ServiceAssignmentsMatrix, get_bundle_zip, DocsGenerator, get_product_from_release


class TestDocsGenerator(TestCase):
    def test_product_extraction(self):
        d = DocsGenerator('')
        self.assertEqual('CC', get_product_from_release('CC_12.6.1'))
        self.assertEqual('CRE', get_product_from_release('CRE_12.6.1'))
        self.assertEqual('CRN', get_product_from_release('CRN_1.0.0'))
        self.assertEqual('CRS', get_product_from_release('CRS_14.0.3'))
        self.assertEqual('CR', get_product_from_release('CR_15.1.0'))
        self.assertEqual('IS', get_product_from_release('IS_5.2'))
        self.assertEqual('LFM', get_product_from_release('LFM_1.13.1'))
        self.assertEqual('LLA', get_product_from_release('LLA_1.41'))
        self.assertEqual('LLI', get_product_from_release('LLI_1.57'))
        self.assertEqual('LMA', get_product_from_release('LMA_4.15.2'))
        self.assertEqual('LMI', get_product_from_release('LMI_4.7.1'))
        self.assertEqual('LX6', get_product_from_release('LX6_16.3.1'))
        self.assertEqual('DEFAULT', get_product_from_release('DEFAULT'))

    def test_validate_template(self):
        dg = DocsGenerator('')
        self.assertTrue(dg.is_template_valid(
            Path('.test_files/test_template_good.docx')))
        self.assertFalse(dg.is_template_valid(
            Path('.test_files/test_template_bad.docx')))

    def test_template_location(self):
        dir_root = Path(mkdtemp())
        try:
            dir_todo = dir_root / 'todo'
            dir_todo.mkdir()
            file_CC = dir_todo / 'CC.docx'
            copy('.test_files/test_template_good.docx', file_CC)

            dg = DocsGenerator(str(dir_root))

            self.assertEqual(file_CC, dg.locate_template('todo', 'CC_13.3.7'))
            with self.assertRaises(ValueError):
                dg.locate_template('WTF', 'CC_13.3.7')
            with self.assertRaises(RuntimeError):
                dg.locate_template('todo', 'OMG')
        finally:
            rmtree(dir_root)

    def test_get_docx(self):
        dir_root = Path(mkdtemp())
        try:
            dir_todo = dir_root / 'todo'
            dir_todo.mkdir()
            file_CC = dir_todo / 'CC.docx'
            copy('.test_files/test_template_good.docx', file_CC)

            dg = DocsGenerator(str(dir_root))

            docx = dg.get_docx('todo', 'CC_13.3.7', 'Тест Тестович',
                               '01-12-2023', '31-12-2023', ['A', 'B'])
            docx.save('test_out_get_docx_output.docx')
        finally:
            rmtree(dir_root)


class TestMatrix(TestCase):
    def test_happyday(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://')
        m = Matrix([t1, t2])
        self.assertEqual(m.num_tasks_ttl('Petr'), 2)
        self.assertEqual(m.num_tasks_ttl('Foma'), 1)
        self.assertTrue('FTW_13.3.7' in m._rows['Petr'].releases)

    def test_name_normalization(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://')
        t3 = Task('C', ['Ptr'], 'FTW_13.3.7', 'http://')
        m = Matrix([t1, t2, t3], {"Ptr": "Petr", "x": "y"})
        self.assertEqual(m.num_tasks_ttl('Petr'), 3)
        self.assertEqual(m.num_tasks_ttl('Foma'), 1)
        self.assertTrue('FTW_13.3.7' in m._rows['Petr'].releases)
        self.assertTrue('OMG_13.3.8' in m._rows['Petr'].releases)

    def test_empty_assignee_control(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://')
        m = Matrix([t1, t2], {"Ptr": "Petr", "x": "Empty", "y": "Empty"})
        self.assertEqual(m.num_tasks_ttl('Empty'), 0)

    def test_same_assignee_several_times(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Ptr', 'Petr'], 'OMG_13.3.8', 'http://')
        m = Matrix([t1, t2], {"Ptr": "Petr"})
        self.assertEqual(m.num_tasks_ttl('Petr'), 2)

    def test_release_percents_calculation(self):
        self.assertAlmostEqual(  # the simplest case
            0.1, MatrixPrinter.get_release_percents(0, 1, 0.1, 0.6))
        self.assertAlmostEqual(  # additional tasks done for the release
            0.5, MatrixPrinter.get_release_percents(1, 1, 0.1, 0.6))
        self.assertAlmostEqual(  # only predefined spend is present
            0.5, MatrixPrinter.get_release_percents(0, 0, 0.3, 0.6))

    def test_count_releases_of_type(self):
        s = {'FTW_13.3.7', 'FTW_14.0.0', 'OMG_15.2.3'}
        self.assertEqual(2, MatrixPrinter.count_releases_of_type(s, 'FTW'))
        self.assertEqual(0, MatrixPrinter.count_releases_of_type(s, 'XXX'))

    def test_cell_comments_generator(self):
        s = MatrixPrinter.msg_control_spends % 20
        self.assertEqual(s, MatrixPrinter.get_release_comment(0.2, []))

        s = f"{MatrixPrinter.msg_control_spends % 10}\n\nA: hA\n"
        t = Task('A', ['Petr'], 'FTW_13.3.7', 'hA')
        self.assertEqual(s, MatrixPrinter.get_release_comment(0.1, [t]))


class TestPredefinedSpend(TestCase):

    def test_happyday(self):
        r = {'FTW_13.3.7', 'FTW_14.0.0', 'OMG_15.0.0'}
        ps = {'Fedor': {'FTW': 0.2, 'DEFAULT': 0.3}}
        p = MatrixPrinter.PredefinedSpend(ps, r)
        self.assertAlmostEqual(0.5, p.get_percents_preallocated_ttl('Fedor'))
        self.assertAlmostEqual(
            0.1, p.get_percents_predefined_for_release('Fedor', 'FTW_13.3.7'))
        d = {'FTW_13.3.7': 0.1, 'FTW_14.0.0': 0.1,
             'OMG_15.0.0': 0.0, 'DEFAULT': 0.3}
        self.assertDictEqual(d, p.assignees['Fedor']._distribution)

    def test_default_handling(self):
        r = {'FTW_13.3.7', 'FTW_14.0.0', 'OMG_15.0.0'}
        ps = {'Fedor': {'FTW': 0.2}}
        p = MatrixPrinter.PredefinedSpend(ps, r)
        self.assertAlmostEqual(
            0.0, p.get_percents_predefined_for_release('Fedor', 'DEFAULT'))


class TestMatrixPrinter(TestCase):

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
        l.print(Matrix([t1, t2], {'P': 'Petr', 'F': 'Foma'}))
        out = [['', 'Petr', 'Foma'],
               ['FTW_13.3.7', 0.5, 0.0],
               ['OMG_13.3.8', 0.5, 1.0],
               ['DEFAULT', 0.0, 0.0]]
        for i, col in enumerate(l.paper):
            self.assertListEqual(out[i], col)

    def test_predefined_proj_spend(self):
        tsks = [Task('A', ['Petr'], 'CRS_13.3.7', ''),
                Task('B', ['Foma', 'Petr'], 'CR_13.3.8', ''),
                Task('C', ['P'], 'CRS_14.0.0', ''),
                Task('D', ['P'], '', '')]
        l = TestMatrixPrinter.TestPrinter()
        predefined = {
            'Foma': {'CR': 0.1, 'CRS': 0.2, 'DEFAULT': 0.3, 'WTF': 0.3}}
        l.print(Matrix(tsks, {'P': 'Petr', 'F': 'Foma'}), predefined)
        out = [['',          'Petr', 'Foma'],
               ['CRS_13.3.7', 0.25,   0.1],
               ['CRS_14.0.0', 0.25,   0.1],
               ['CR_13.3.8',  0.25,   0.5],
               ['DEFAULT',    0.25,   0.3]]
        for i, col in enumerate(l.paper):
            self.assertListEqual(out[i], col)

    def test_predefined_proj_taskless_case(self):
        tsks = [Task('A', ['Petr'], 'CRS_13.3.7', ''),
                Task('B', ['Foma', 'Petr'], 'CR_13.3.8', ''),
                Task('C', ['P'], 'CRS_14.0.0', ''),
                Task('D', ['P'], '', '')]
        l = TestMatrixPrinter.TestPrinter()
        predefined = {'Fedor': {'CR': 0.1,
                                'CRS': 0.2, 'DEFAULT': 0.3, 'WTF': 0.3}}
        l.print(
            Matrix(tsks, {'P': 'Petr', 'Fo': 'Foma', 'Fe': 'Fedor'}), predefined)
        out = [['',          'Petr', 'Foma', ''],
               ['CRS_13.3.7', 0.25,   0,      0.1666667],
               ['CRS_14.0.0', 0.25,   0,      0.1666667],
               ['CR_13.3.8',  0.25,   1,      0.1666667],
               ['DEFAULT',    0.25,   0,      0.5]]
        out_h = [['', '', '', 'Fedor']]
        for i, col in enumerate(l.paper):
            self.assertListEqual(out[i], col)
        for i, col in enumerate(l.paper_highlights):
            self.assertListEqual(out_h[i], col)

    def test_predefined_proj_spend_comments(self):
        tsks = [Task('A', ['Petr'], 'FTW_13.3.7', 'hA'),
                Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'hB'),
                Task('C', ['P'], 'FTW_14.0.0', 'hC'),
                Task('D', ['P'], '', 'hD')]
        l = TestMatrixPrinter.TestPrinter()
        predefined = {'Foma': {'OMG': 0.1, 'FTW': 0.2, 'DEFAULT': 0.3}}
        l.print(Matrix(tsks, {'P': 'Petr', 'F': 'Foma'}), predefined)
        out = [['', '',        ''],
               ['', 'A: hA\n', 'Учтено 10% управленческих затрат времени на выпуск'],
               ['', 'C: hC\n', 'Учтено 10% управленческих затрат времени на выпуск'],
               ['', 'B: hB\n', 'Учтено 10% управленческих затрат времени на выпуск\n\nB: hB\n'],
               ['', 'D: hD\n', 'Учтено 30% управленческих затрат времени на выпуск']]
        for i, col in enumerate(l.paper_comments):
            self.assertListEqual(out[i], col)

    def test_comments(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://A')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://B')
        l = TestMatrixPrinter.TestPrinter()
        l.print(Matrix([t1, t2], {'x': 'A person with no tasks', 'y': 'Foma'}))
        out = [['', MatrixPrinter.msg_person_unknown, '', MatrixPrinter.msg_no_tasks],
               ['', 'A: http://A\n', '', ''],
               ['', 'B: http://B\n', 'B: http://B\n', '']]
        for i, col in enumerate(l.paper_comments):
            self.assertListEqual(out[i], col)

    def test_hightlights_if_no_tasks(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://A')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://B')
        l = TestMatrixPrinter.TestPrinter()
        l.print(
            Matrix([t1, t2], {'P': 'Petr', 'F': 'Foma', 'x': 'Empty', 'y': 'Empty'}))
        out = [['', '', '', 'Empty']]
        for i, col in enumerate(l.paper_highlights):
            self.assertListEqual(out[i], col)

    def test_hightlights_if_new_name(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://A')
        t2 = Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://B')
        l = TestMatrixPrinter.TestPrinter()
        l.print(Matrix([t1, t2], {'F': 'Foma', 'x': 'Empty', 'y': 'Empty'}))
        out = [['', 'Petr', '', 'Empty']]
        for i, col in enumerate(l.paper_highlights):
            self.assertListEqual(out[i], col)

    def test_excel_printer(self):
        t1 = Task('Task 1 with very very long description like you can find in real life',
                  ['Petr'], 'FTW_13.3.7', 'http://task1/adsfakjhdslfkjahdlskfjhaldsfhadf/adlskfj')
        t2 = Task('Task 2', ['Sheph', 'Petr'], 'OMG_13.3.8', 'http://task2')
        t3 = Task('Task 3 with very very long description like you can find in real life',
                  ['Petr'], 'FTW_13.3.7', 'http://task3/asdfupfasdfbdsfdsfasdfadv/asdfefwewdf')
        predef_spend = {'Sheph': {'FTW': 0.4, 'DEFAULT': 0.2}}
        with ExcelPrinter('test_out_excel_printer.xlsx', '31-01-2023', '28-02-2023') as printer:
            printer.print(Matrix([t1, t2, t3], {'x': 'Empty'}), predef_spend)


class TestNameFilter(TestCase):
    def test_filtration(self):
        src = ['a', 'b']
        nf = NameNormalizer({"a": "1", "b": "2", "c": "2"})
        dst = [nf.normalize(x)[0] for x in src]
        self.assertListEqual(['1', '2'], dst)


class TestAssignmentsGeneration(TestCase):
    def test_matrix2assignment_conversion(self):
        t = [Task('A', ['Petr'],         'FTW_13.3.7', 'http://'),
             Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', 'http://'),
             Task('C', ['Ptr'],          'FTW_13.3.7', 'http://'),
             Task('D', ['Ptr'],          '',           'http://'),
             Task('E', ['Oleg'],         '',           'http://')]
        for x in t:
            x.essence = x.title
            x.essence_completed = f'{x.title}_done'
        s = ServiceAssignmentsMatrix(t, {"Ptr": "Petr", "x": "y"})

        self.assertEqual(len(s.list_assignees_by_release('FTW_13.3.7')), 1)

        e = s.list_essences('FTW_13.3.7', 'Petr')
        self.assertListEqual(e, ['A', 'C'])
        e = s.list_completed_essences('FTW_13.3.7', 'Petr')
        self.assertListEqual(e, ['A_done', 'C_done'])

        self.assertEqual(len(s.list_assignees_by_release('OMG_13.3.8')), 2)
        e = s.list_essences('OMG_13.3.8', 'Foma')
        self.assertListEqual(e, ['B'])
        e = s.list_completed_essences('OMG_13.3.8', 'Foma')
        self.assertListEqual(e, ['B_done'])
        e = s.list_essences('OMG_13.3.8', 'Petr')
        self.assertListEqual(e, ['B'])
        e = s.list_completed_essences('OMG_13.3.8', 'Petr')
        self.assertListEqual(e, ['B_done'])

        self.assertEqual(len(s.list_assignees_by_release('DEFAULT')), 2)
        e = s.list_essences('DEFAULT', 'Petr')
        self.assertListEqual(e, ['D'])
        e = s.list_completed_essences('DEFAULT', 'Petr')
        self.assertListEqual(e, ['D_done'])
        e = s.list_essences('DEFAULT', 'Oleg')
        self.assertListEqual(e, ['E'])
        e = s.list_completed_essences('DEFAULT', 'Oleg')
        self.assertListEqual(e, ['E_done'])


class TestZipper(TestCase):
    def test_happyday(self):
        t = [Task('A', ['Petr'],         'CC_13.3.7', 'http://'),
             Task('B', ['Foma', 'Petr'], 'CR_13.3.8', 'http://'),
             Task('C', ['Ptr'],          'CC_13.3.7', 'http://'),
             Task('D', ['Ptr'],          '',           'http://'),
             Task('E', ['Oleg'],         '',           'http://')]
        for x in t:
            x.essence = f'AI_{x.title}'
            x.essence_completed = f'AI2_{x.title}'
        dir_root = Path(mkdtemp())
        try:
            dir_todo = dir_root / 'todo'
            dir_todo.mkdir()
            dir_done = dir_root / 'done'
            dir_done.mkdir()
            for x in (dir_todo, dir_done):
                for y in ('CC', 'CR', 'DEFAULT'):
                    copy('.test_files/test_template_good.docx',
                         x / f'{y}.docx')

            dg = DocsGenerator(str(dir_root))

            s = ServiceAssignmentsMatrix(t, {"Ptr": "Petr", "x": "y"})
            with open('test_out.zip', mode='wb') as f:
                f.write(get_bundle_zip(s, '01-01-2023', '02-02-2023', {}, dg))

        finally:
            rmtree(dir_root)
