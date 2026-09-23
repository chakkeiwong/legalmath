#!/usr/bin/env python3
# CLINGO STANDALONE.py
#   by Lut99
#
# Created:
#   11 Apr 2025, 11:05:25
# Last edited:
#   14 Apr 2025, 11:15:08
# Auto updated?
#   Yes
#
# Description:
#   Quick wrapper around the `clingo` library s.t. we can test Clingo
#   snippets
#

import argparse
import clingo
import os
import sys
import typing


##### HELPER FUNCTIONS #####
def _supports_color():
    """
        Returns True if the running system's terminal supports color, and False
        otherwise.

        From: https://stackoverflow.com/a/22254892
    """
    plat = sys.platform
    supported_platform = plat != 'Pocket PC' and (plat != 'win32' or
                                                  'ANSICON' in os.environ)
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    return supported_platform and is_a_tty





##### ENTRYPOINT #####
def main(programs: typing.List[str], use_colors: typing.Optional[bool] = None) -> int:
    """
        Entrypoint to the script.

        # Arguments
        - `programs`: The list of Clingo programs to execute.
    """

    color_support_question_mark = use_colors if use_colors is not None else _supports_color()
    yellow = "\033[93;1m" if color_support_question_mark else ""
    bold = "\033[1m" if color_support_question_mark else ""
    clear = "\033[0m" if color_support_question_mark else ""

    if len(programs) == 0:
        print("No programs given; nothing to do")
        return 0

    for program in programs:
        # Open the file
        with open(program, "r") as h:
            contents = h.read()

        print(f"\n{bold}##### Program '{program}' #####{clear}")

        # Run the Clingo solver
        ctl = clingo.Control()
        ctl.add("base", [], contents)
        ctl.ground([("base", [])])
        with ctl.solve(yield_=True) as handle:
            # Show 'em
            found_any = False
            for i, model in enumerate(handle):
                print("\n+" + (35 * '-') + f"Model {str(i + 1).rjust(2, '0')}" + (35 * '-') + "+")
                for symbol in model.symbols(atoms=True):
                    print(f"| {str(symbol).ljust(76)} |")
                print("+" + (78 * '-') + "+")
                found_any = True
            if not found_any:
                print(f"{yellow}WARNING:{clear} {bold}Clingo did not find any models{clear}")

    # Done
    return 0



# Actual entrypoint
if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("PROGRAMS", nargs='*', help="The list of Clingo programs to execute. Given as filenames.")
    parser.add_argument("-c", "--use-colors", type=bool, help="If given, then forces (or disallows) the usage of ANSI colors.")

    args = parser.parse_args()
    exit(main(args.PROGRAMS, args.use_colors))
