from unittest import TestCase

from tfs_excel import get_the_earliest, get_the_latest

class TestDateSort(TestCase):
    def test_happyday(self):
        dates = ['01-01-2023', '31-12-2022']
        self.assertEqual('01-01-2023', get_the_latest(dates))
        self.assertEqual('31-12-2022', get_the_earliest(dates))
