from unittest import TestCase

from src.Handlers import Task
from src.Matrix import ExcelPrinter, Matrix, MatrixPrinter, NameNormalizer


class TestMatrix(TestCase):
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

    def test_same_assignee_several_times(self):
        t1 = Task('A', ['Petr'], 'FTW_13.3.7', 'http://')
        t2 = Task('B', ['Ptr', 'Petr'], 'OMG_13.3.8', 'http://')
        m = Matrix([t1, t2], {"Ptr": "Petr"})
        self.assertEqual(m.rows['Petr'].tasks_ttl, 2)

    def test_release_percents_calculation(self):
        self.assertAlmostEqual(
            0.1, MatrixPrinter.get_release_percents(0, 1, 0.1, 0.6))
        self.assertAlmostEqual(
            0.5, MatrixPrinter.get_release_percents(1, 1, 0.1, 0.6))

    def test_count_releases_of_type(self):
        s = {'FTW_13.3.7', 'FTW_14.0.0', 'OMG_15.2.3'}
        self.assertEqual(2, MatrixPrinter.count_releases_of_type(s, 'FTW'))
        self.assertEqual(0, MatrixPrinter.count_releases_of_type(s, 'XXX'))

    def test_cell_comments_generator(self):
        s =  MatrixPrinter.msg_control_spends % 20
        self.assertEqual(s, MatrixPrinter.get_release_comment(0.2, []))

        s = f"{MatrixPrinter.msg_control_spends % 10}\nA: hA\n"
        t = Task('A', ['Petr'], 'FTW_13.3.7', 'hA')
        self.assertEqual(s, MatrixPrinter.get_release_comment(0.1, [t]))

class TestPredefinedSpend(TestCase):

    def test_happyday(self):
        r = {'FTW_13.3.7', 'FTW_14.0.0', 'OMG_15.0.0'}
        ps = {'Fedor' : {'FTW': 0.2, 'DEFAULT': 0.3}}
        p = MatrixPrinter.PredefinedSpend(ps, r)
        self.assertAlmostEqual(0.5, p.assignees['Fedor'].ttl_percent)
        self.assertAlmostEqual(0.1, p.assignees['Fedor'].distribution['FTW_13.3.7'])
        d = {'FTW_13.3.7': 0.1, 'FTW_14.0.0': 0.1, 'OMG_15.0.0': 0.0, 'DEFAULT': 0.3}
        self.assertDictEqual(d, p.assignees['Fedor'].distribution)


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
        tsks = [Task('A', ['Petr'], 'FTW_13.3.7', ''),
                Task('B', ['Foma', 'Petr'], 'OMG_13.3.8', ''),
                Task('C', ['P'], 'FTW_14.0.0', ''),
                Task('D', ['P'], '', '')]
        l = TestMatrixPrinter.TestPrinter()
        predefined = {'Foma': {'OMG': 0.1, 'FTW': 0.2, 'DEFAULT': 0.3}}
        l.print(Matrix(tsks, {'P': 'Petr', 'F': 'Foma'}), predefined)
        out = [['',          'Petr', 'Foma'],
               ['FTW_13.3.7', 0.25,   0.1],
               ['FTW_14.0.0', 0.25,   0.1],
               ['OMG_13.3.8', 0.25,   0.5],
               ['DEFAULT',    0.25,   0.3]]
        for i, col in enumerate(l.paper):
            self.assertListEqual(out[i], col)

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
               ['', 'B: hB\n', 'Учтено 10% управленческих затрат времени на выпуск\nB: hB\n'],
               ['', 'D: hD\n', 'Учтено 30% управленческих затрат времени']]
        for i, col in enumerate(l.paper):
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
        with ExcelPrinter('test_excel_printer.xlsx', '31-01-2023', '28-02-2023') as printer:
            printer.print(Matrix([t1, t2, t3], {'x': 'Empty'}))


class TestNameFilter(TestCase):
    def test_filtration(self):
        src = ['a', 'b']
        nf = NameNormalizer({"a": "1", "b": "2", "c": "2"})
        dst = [nf.normalize(x)[0] for x in src]
        self.assertListEqual(['1', '2'], dst)
