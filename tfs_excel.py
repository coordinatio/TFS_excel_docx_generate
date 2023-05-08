#!/usr/bin/python3
from os import path
from subprocess import call
from sys import platform

from src.ArgsTypes import parse_args
from src.Handlers import HandlerCai, HandlerIS, HandlerLingvo
from src.Matrix import Matrix, ExcelPrinter, DocxPrinter


def main():
    a = parse_args()

    i = []
    for x in (HandlerCai, HandlerIS, HandlerLingvo):
        i += x(a.pat, vars(a)["from"], vars(a)["to"]).workitems

    with ExcelPrinter(a.out, vars(a)["from"], vars(a)["to"]) as p:
        p.print(Matrix(i, a.names_reference), a.predefined_spend)

    # test = DocxPrinter()
    # test.create_zip(Matrix(i, a.names_reference))

    if (a.open):
        if platform in ("linux", "linux2"):
            call(["xdg-open", path.abspath(a.out)])
        else:
            print("--open works only on linux yet")


if __name__ == "__main__":
    main()
