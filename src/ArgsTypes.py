from argparse import ArgumentParser, ArgumentTypeError
from json import loads
from os import path
from math import fsum
from pathlib import Path
from tempfile import mkstemp
import re


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
                raise ArgumentTypeError(
                    "It is allowed to preallocate strictly less than 100%")

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
    def arg_dates_interval(i: str) -> tuple[str, str] | bool:
        if i == 'next':
            return True
        r = re.compile(
            r'^((\d\d?)[-\.\/\s](\d\d?)[-\.\/\s](\d\d\d\d))-((\d\d?)[-\.\/\s](\d\d?)[-\.\/\s](\d\d\d\d))$')
        m = r.fullmatch(i)
        if not m:
            raise ArgumentTypeError(("Please provide the interval in the following format "
                                     "dd.mm.YYYY-dd.mm.YYYY (you can use '-','/',' ' instead of '.'). "
                                     "You can also use the keywork 'next' to calculate the interval "
                                     "automatically based on the latest snapshot available."))
        return (f'{m.group(2)}-{m.group(3)}-{m.group(4)}', f'{m.group(6)}-{m.group(7)}-{m.group(8)}')


def parse_args():
    parser = ArgumentParser()

    pat_help = ('A Personal Access Token string which could be obtained '
                'in the "Security" entry inside your TFS profile. '
                'You can provide the value by creating ".pat" file with it in the script\'s work directory, '
                'thus you can omit the explicit argument while the value is read implicitly from the file.')
    pat_file = Path('./.pat')
    if not pat_file.is_file():
        parser.add_argument('--pat', required=True, help=pat_help)
    else:
        with pat_file.open() as f:
            parser.add_argument('--pat', default=f.read(), help=pat_help)

    mutex = parser.add_mutually_exclusive_group(required=True)
    mutex.add_argument("--draft_update", type=ArgsTypes.arg_dates_interval,
                       metavar='next|dd.mm.YYYY-dd.mm.YYYY')
    mutex.add_argument("--drafts_list", action='store_true')
    mutex.add_argument("--draft_get", type=int, metavar='DRAFT#')
    mutex.add_argument("--draft_delete", type=int, metavar='DRAFT#')
    mutex.add_argument("--draft_approve", type=int, metavar='DRAFT#')
    mutex.add_argument("--snapshots_list", action='store_true')
    mutex.add_argument("--snapshot_get", type=int, metavar='SNAPSHOT#')

    parser.add_argument("--out",
                        default=mkstemp(suffix='.xlsx', prefix='tfs_excel_')[1],
                        metavar='./THE_EXCEL_FILE_TO_WRITE_INTO.xlsx',
                        help="File to put the results into. Defaults to 'time_report.xlsx'.")
    parser.add_argument("--no_open", action='store_true',
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
