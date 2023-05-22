from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime
from json import loads
from os import path
from typing import Dict
from math import fsum


class ArgsTypes:
    @staticmethod
    def validate_names_reference(d: dict):
        msg = 'Names json has incorrect structure, must be flat str->str pairs'
        if type(d) is not dict:
            raise ArgumentTypeError(msg)
        for k in d:
            if type(k) is not str or type(d[k]) is not str:
                raise ArgumentTypeError(msg)

    @staticmethod
    def arg_names_reference_file(path_to_file: str) -> dict:
        """reads file, parses json, validates contents
        returns dict with incorrect -> correct name pairs"""
        j = {}
        if not path_to_file:
            return j
        if not path.exists(path_to_file):
            raise ArgumentTypeError(
                "Names reference file %s does not exist" % path_to_file)
        try:
            with open(path_to_file, 'r', encoding="utf-8") as f:
                j = loads(f.read())
        except:
            raise ArgumentTypeError(
                "%s contains invalid json" % path_to_file)
        ArgsTypes.validate_names_reference(j)
        return j

    @staticmethod
    def validate_predefind_spend_file(d: dict):
        msg = 'Predefined spend json has incorrect structure, must be {str: {str: float}}'
        if type(d) is not dict:
            raise ArgumentTypeError(msg)
        for k in d:
            if type(k) is not str or type(d[k]) is not dict:
                raise ArgumentTypeError(msg)
            for x in d[k]:
                if type(x) is not str or type(d[k][x]) is not float:
                    raise ArgumentTypeError(msg)
            prealloc_ttl = fsum([w for _, w in d[k].items()])
            if prealloc_ttl >= 1:
                raise ArgumentTypeError("It is allowed to preallocate strictly less than 100%")

    @staticmethod
    def arg_predefined_spend_file(path_to_file: str) -> dict:
        """reads file, parses json, validates contents"""
        j = {}
        if not path_to_file:
            return j
        if not path.exists(path_to_file):
            raise ArgumentTypeError(
                "Predefined spend file %s does not exist" % path_to_file)
        try:
            with open(path_to_file, 'r', encoding="utf-8") as f:
                j = loads(f.read())
        except:
            raise ArgumentTypeError(
                "%s contains invalid json" % path_to_file)
        ArgsTypes.validate_predefind_spend_file(j)
        return j

    @staticmethod
    def arg_date(i: str) -> str:
        d = ('-', '.', '/', ' ')
        for x in d:
            try:
                return datetime.strptime(i, f'%d{x}%m{x}%Y').date().strftime("%d-%m-%Y")
            except:
                pass
        raise ArgumentTypeError(
            f"Please provide date in either {' or '.join([f'dd{x}mm{x}YYYY' for x in d])} format")


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--pat', required=True,
                        help=('A Personal Access Token string which could be obtained '
                              'in the "Security" entry inside your TFS profile'))

    parser.add_argument("--draft_update", action='store_true', default=False)
    parser.add_argument("--drafts_list", action='store_true', default=False)
    parser.add_argument("--draft_get", action='store_true', default=False)
    parser.add_argument("--draft_approve", action='store_true', default=False)
    parser.add_argument("--snapshots_list", action='store_true', default=False)
    parser.add_argument("--snapshot_get", action='store_true', default=False)

    parser.add_argument('--from', dest='date_from',
                        type=ArgsTypes.arg_date, metavar='dd-mm-YYYY',
                        help='dd-mm-YYYY', required=True)
    parser.add_argument('--to', dest='date_to',
                        type=ArgsTypes.arg_date, metavar='dd-mm-YYYY',
                        help='dd-mm-YYYY', required=True)
    parser.add_argument("--out",
                        default="time_report.xlsx", metavar='./THE_EXCEL_FILE_TO_WRITE_INTO.xlsx',
                        help="File to put the results into. Defaults to 'time_report.xlsx'.")
    parser.add_argument("--open", action='store_true', default=False,
                        help="Tells if to open the resulting file immediately after creation")
    parser.add_argument('--names_reference', type=ArgsTypes.arg_names_reference_file,
                        default='name_filter.json', metavar='./A_SPECIAL_FILE.json',
                        help=("Path to the file containing json with name pairs. "
                              "Defaults to 'name_filter.json'."))
    parser.add_argument('--predefined_spend', type=ArgsTypes.arg_predefined_spend_file,
                        default='predefined_spend.json', metavar='./A_SPECIAL_FILE.json',
                        help=("Path to the file containing json with predefined spend info. "
                              "Defaults to 'predefined_spend.json'."))
    return parser.parse_args()
