from argparse import ArgumentTypeError
from json import loads
from unittest import TestCase

from src.ArgsTypes import ArgsTypes


class TestNamesReferenceValidator(TestCase):
    def test_valid(self):
        j = '{"a" : "b", "s" : "b", "d" : "f"}'
        ArgsTypes.validate_names_reference(loads(j))

    def test_invalid1(self):
        j = '{"a" : "b", "s" : {"x" : "y"}}'
        with self.assertRaises(ArgumentTypeError):
            ArgsTypes.validate_names_reference(loads(j))

    def test_invalid2(self):
        j = '{"a" : "b", "s" : ["x", "y"]}'
        with self.assertRaises(ArgumentTypeError):
            ArgsTypes.validate_names_reference(loads(j))

    def test_invalid3(self):
        j = '["a", "s"]'
        with self.assertRaises(ArgumentTypeError):
            ArgsTypes.validate_names_reference(loads(j))
