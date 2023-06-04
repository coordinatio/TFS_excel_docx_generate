from unittest import TestCase
from typing import Dict
from src.Handlers import HandlerCai, HandlerIS, HandlerLingvo, convert_html2plain


class MockWorkitem:
    def __init__(self, d: Dict, link='') -> None:
        self.parent = None
        self.d = d
        if 'System.Description' not in self.d:
            self.d['System.Description'] = ''
        if 'System.TeamProject' not in self.d:
            self.d['System.TeamProject'] = 'UnitTest'
        self.id = f'id_id_{d["Title"]}'
        self._links = {'html': {'href': link}}

    def __getitem__(self, key):
        return self.d[key]


class TestPandoc(TestCase):
    def test_html2plain(self):
        with open('test_input.html', mode='r') as html:
            with open('test_output.txt', mode='r') as txt:
                o = convert_html2plain(html.read())
                self.assertEqual(o, txt.read())


class TestAssigneeExtraction(TestCase):
    def test_cai_happyday(self):
        d = {'AssignedTo': 'Алексей Калюжный <CONTENT\\AKalyuzhny>',
             'Tags': '@Федор_Симашев; CC_12.8.0',
             'CreatedDate': '2023-01-01',
             'microsoft.vsts.common.closeddate': '2023-01-01',
             'Title': 'Test title'}

        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                return [MockWorkitem(d)]
        self.assertEqual(X('', '', '').tasks[0].assignees, [
                         'Алексей Калюжный', 'Федор Симашев'])

    def test_cai_no_tags(self):
        d = {'AssignedTo': 'Алексей Калюжный <CONTENT\\AKalyuzhny>',
             'Tags': None,
             'CreatedDate': '2023-01-01',
             'microsoft.vsts.common.closeddate': '2023-01-01',
             'Title': 'Test title'}

        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                return [MockWorkitem(d)]
        self.assertEqual(X('', '', '').tasks[0].assignees, [
                         'Алексей Калюжный'])

    def test_cai_hashtag(self):
        d = {'AssignedTo': 'Алексей Калюжный <CONTENT\\AKalyuzhny>',
             'Tags': '#Федор_Симашев; CC_12.8.0',
             'CreatedDate': '2023-01-01',
             'microsoft.vsts.common.closeddate': '2023-01-01',
             'Title': 'Test title'}

        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                return [MockWorkitem(d)]
        self.assertEqual(X('', '', '').tasks[0].assignees, [
                         'Алексей Калюжный', 'Федор Симашев'])

    def test_assignee_doubling_case(self):
        d = {'AssignedTo': 'Федор Симашев <CONTENT\\Somestring>',
             'Tags': '#Федор_Симашев; CC_12.8.0',
             'Title': 'Test title',
             'CreatedDate': '2023-01-01',
             'microsoft.vsts.common.closeddate': '2023-01-01'}

        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                return [MockWorkitem(d)]
        self.assertEqual(X('', '', '').tasks[0].assignees, [
                         'Федор Симашев'])


class TestReleaseExtraction(TestCase):
    def test_cai_happyday(self):
        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': '@Федор_Симашев; Garbage',
                     'CreatedDate': '2023-01-01',
                     'microsoft.vsts.common.closeddate': '2023-01-01',
                     'Title': 'Test title'}
                w = MockWorkitem(d)
                w.parent = MockWorkitem(
                    {'AssignedTo': '', 'Tags': 'CC_12.8.0',
                     'CreatedDate': '2023-01-01',
                     'microsoft.vsts.common.closeddate': '2023-01-01',
                     'Title': 'T'})
                return [w]
        self.assertEqual('CC_12.8.0', X('', '', '').tasks[0].release)

    def test_cai_no_tags(self):
        class X(HandlerCai):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': None,
                     'CreatedDate': '2023-01-01',
                     'microsoft.vsts.common.closeddate': '2023-01-01',
                     'Title': 'Test title'}
                w = MockWorkitem(d)
                w.parent = MockWorkitem(
                    {'AssignedTo': '', 'Tags': 'CC_12.8.0',
                     'CreatedDate': '2023-01-01',
                     'microsoft.vsts.common.closeddate': '2023-01-01',
                     'Title': 'T'})
                return [w]
        self.assertEqual('CC_12.8.0', X('', '', '').tasks[0].release)

    def test_is_happyday(self):
        class X(HandlerIS):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': '@Федор_Симашев; Garbage',
                     'Title': 'Test title',
                     'CreatedDate': '2023-01-01',
                     'microsoft.vsts.common.closeddate': '2023-01-01',
                     'system.areapath': 'AIS\\5.2'}
                return [MockWorkitem(d)]
        self.assertEqual('IS_5.2', X('', '', '').tasks[0].release)

    def test_lx6_happyday(self):
        class X(HandlerLingvo):
            def retrieve(self, pat, date_from, date_to):
                d = {'AssignedTo': None,
                     'Tags': '@Федор_Симашев; Garbage',
                     'Title': 'Test title',
                     'CreatedDate': '2023-01-01',
                     'microsoft.vsts.common.closeddate': '2023-01-01',
                     'system.iterationpath': 'Lingvo X6\\16.3.1'}
                return [MockWorkitem(d)]
        self.assertEqual('LX6_16.3.1', X('', '', '').tasks[0].release)
