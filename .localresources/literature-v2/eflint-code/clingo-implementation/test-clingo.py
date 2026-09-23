#!/usr/bin/env python3
# TEST CLINGO.py
#   by Lut99
#
# Created:
#   07 Apr 2025, 13:05:13
# Last edited:
#   08 May 2025, 14:28:24
# Auto updated?
#   Yes
#
# Description:
#   Test script for automagically evaluating the eFLINT -> Clingo
#   translation.
#

import abc
import argparse
import clingo
import collections
import copy
import os
import shlex
import subprocess
import sys
import time
import typing
import typing_extensions


##### CONSTANTS #####
EFLINT_HEADER_NAME = "eFLINT"
CLINGO_HEADER_NAME = "Clingo"





##### GLOBALS #####
# Whether to print with debug or not
DEBUG: bool = False
# Whether to print traces or not
TRACE: bool = False





##### HELPER FUNCTIONS #####
def is_whitespace(text: str) -> bool:
    """
        Checks if the given string consists only of whitespaces.

        # Arguments
        - `text`: The text to check.

        # Returns
        True if it's only ' ', '\\t', '\\r' or '\\n'.
    """

    for c in text:
        if c != ' ' and c != '\t' and c != '\r' and c != '\n':
            return False
    return True

def strip_suffix(filename: str, suffixes: typing.List[str]) -> typing.Optional[str]:
    """
        Attempts to return the given filename with any of the given suffixes stripped.

        # Arguments
        - `filename`: The name of the file to compute the suffix of.
        - `suffixes`: The list of suffixes to match.

        # Returns
        The name without any of the suffixes, or `None` if it did not have one of the suffixes.
    """

    for suffix in suffixes:
        # We do this a little obtrusively
        mode = "start"
        i = len(filename)
        match = True
        for c in suffix[::-1]:
            if mode == "start":
                # Either we parse an escape, or the filename still matches
                if c == "$":
                    mode = "escape"
                    continue
                elif i > 0 and filename[i - 1] == c:
                    i -= 1
                    continue
                else:
                    match = False
                    break
            elif mode == "escape":
                # It's an escape: see what we parse
                if c != "$":
                    mode = f"escape-{c}"
                    continue
                # If it _is_ a dollar, we assume '$$' -> '$'
                elif i > 0 and filename[i - 1] == "$":
                    i -= 1
                    continue
                else:
                    match = False
                    break
            elif mode.startswith("escape-"):
                # Wait for the final one
                escaped = mode[7:]
                if c == "$":
                    # Evalue the escaped
                    if escaped == "n":
                        # Pop numbers off the filename!
                        at_least_one = False
                        while i > 0 and ord(filename[i - 1]) >= ord('0') and ord(filename[i - 1]) <= ord('9'):
                            at_least_one = True
                            i -= 1
                        if not at_least_one: return None
                        mode = "start"
                        continue
                    elif escaped == "n":
                        match = False
                        break
                    else:
                        perror(f"Unknown special char \"${escaped}$\" in suffix \"{suffix}\"")
                        exit(1)

        # Check if we matched everything
        if match: return filename[:i]

    # Nothing was matched
    return None

def get_area_before_prompt(stdout: str) -> str:
    """
        Gets the part of an eFLINT output that's before the first prompt.

        # Arguments
        - `stdout`: The eFLINT output to search.

        # Returns
        The output but stripped of anything after the first prompt.

        # Exceptions
        This function throws exceptions if it failed to find an eFLINT prompt in the output.
    """

    # Find the prompt
    area_end = None
    for i in range(len(stdout)):
        # Check if we find '#$n$ > '
        start_i = i
        if stdout[i] == '#':
            i += 1
            skip = False
            while i < len(stdout):
                if stdout[i] == ' ':
                    break
                elif ord(stdout[i]) < ord('0') or ord(stdout[i]) > ord('9'):
                    # Not what we're looking for
                    skip = True
                    break
                i += 1
            if skip: continue
            if i + 3 <= len(stdout) and stdout[i:i+3] == " > ":
                # It is! Strip until here
                area_end = start_i
                break
    if area_end is None:
        raise RuntimeError("eFLINT reasoner did not output prompt")

    # Done
    return stdout[:area_end].strip()

def get_area_in_between_last_prompts(stdout: str) -> typing.Optional[typing.Tuple[str, int, int]]:
    """
        Gets the part of an eFLINT output that's wrapped in between the last two prompts.

        # Arguments
        - `stdout`: The eFLINT output to search.

        # Returns
        The output but stript of anything before- or after the area wrapped in prompts.

        Also returns the start- and end position of the first prompt.

        # Exceptions
        This function throws exceptions if it failed to find two distinct eFLINT prompts in the output.
    """

    def find_last_prompt(stdout: str) -> typing.Optional[typing.Tuple[int, int]]:
        """
            Returns the positions of the first- and last characters of the last prompt in the given
            reasoner output.

            # Arguments
            - `stdout`: The stdout to search.

            # Returns
            A tuple of the start character and the last character, or `None` if we didn't find any.

            Note the first index is inclusive, the second exclusive.
        """

        for i in range(len(stdout) - 1, -1, -1):
            # Check if we find '#$n$ > '
            start_i = i
            if stdout[i] == '#':
                i += 1
                skip = False
                while i < len(stdout):
                    if stdout[i] == ' ':
                        break
                    elif ord(stdout[i]) < ord('0') or ord(stdout[i]) > ord('9'):
                        # Not what we're looking for
                        skip = True
                        break
                    i += 1
                if skip: continue
                if i + 3 <= len(stdout) and stdout[i:i+3] == " > ":
                    # It is! Strip until here
                    return (start_i, i+3)
        return None

    # Find the first prompt
    prompt = find_last_prompt(stdout)
    if prompt is None:
        ptrace("eFLINT reasoner did not output ending prompt")
        return None
    area_end = prompt[0]
    stdout = stdout[:area_end]

    # Find the second prompt, but from the other side
    prompt = find_last_prompt(stdout)
    if prompt is None:
        ptrace("eFLINT reasoner did not output starting prompt")
        return None
    area_start = prompt[1]
    stdout = stdout[area_start:]

    # Done
    return (stdout.strip(), prompt[0], prompt[1])



def _supports_color(file: typing.TextIO = sys.stdout):
    """
        Returns True if the running system's terminal supports color, and False
        otherwise.

        From: https://stackoverflow.com/a/22254892
    """
    plat = sys.platform
    supported_platform = plat != 'Pocket PC' and (plat != 'win32' or
                                                  'ANSICON' in os.environ)
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(file, 'isatty') and file.isatty()
    return supported_platform and is_a_tty

def perror(text: str, start: str="", end: str="\n", file: typing.TextIO=sys.stderr, use_color: typing.Optional[bool]=None):
    """
        Writes an error message.

        # Arguments
        - `text`: The text to write.
        - `end`: The suffix to write after `text`.
        - `file`: The file to write to.
        - `use_color`: Whether to use ANSI colors or not. If `None`, attempt to derive
          automatically based on whether `stdin` is a tty.
    """

    color_question_mark = use_color if use_color is not None else _supports_color(file)
    accent = "\033[91;1m" if color_question_mark else ""
    bold = "\033[1m" if color_question_mark else ""
    clear = "\033[0m" if color_question_mark else ""
    print(f"{start}{accent}ERROR:{clear} {bold}{text}{clear}", end=end, file=file)

def pwarn(text: str, start: str="", end: str="\n", file: typing.TextIO=sys.stderr, use_color: typing.Optional[bool]=None):
    """
        Writes a warning message.

        # Arguments
        - `text`: The text to write.
        - `end`: The suffix to write after `text`.
        - `file`: The file to write to.
        - `use_color`: Whether to use ANSI colors or not. If `None`, attempt to derive
          automatically based on whether `stdin` is a tty.
    """

    color_question_mark = use_color if use_color is not None else _supports_color(file)
    accent = "\033[93;1m" if color_question_mark else ""
    bold = "\033[1m" if color_question_mark else ""
    clear = "\033[0m" if color_question_mark else ""
    print(f"{start}{accent}WARNING:{clear} {bold}{text}{clear}", end=end, file=file)

def pdebug(text: str, start: str="", end: str="\n", file: typing.TextIO=sys.stderr, use_color: typing.Optional[bool]=None):
    """
        Writes a debug message.

        Does nothing if the `DEBUG`-global is False.

        # Arguments
        - `text`: The text to write.
        - `end`: The suffix to write after `text`.
        - `file`: The file to write to.
        - `use_color`: Whether to use ANSI colors or not. If `None`, attempt to derive
          automatically based on whether `stdin` is a tty.
    """

    if not DEBUG:
        return

    color_question_mark = use_color if use_color is not None else _supports_color(file)
    accent = "\033[90;1m" if color_question_mark else ""
    clear = "\033[0m" if color_question_mark else ""
    print(f"{start}{accent}DEBUG:{clear} {accent}{text}{clear}", end=end, file=file)

def ptrace(text: str, start: str="", end: str="\n", file: typing.TextIO=sys.stderr, use_color: typing.Optional[bool]=None):
    """
        Writes a trace message.

        Does nothing if the `TRACE`-global is False.

        # Arguments
        - `text`: The text to write.
        - `end`: The suffix to write after `text`.
        - `file`: The file to write to.
        - `use_color`: Whether to use ANSI colors or not. If `None`, attempt to derive
          automatically based on whether `stdin` is a tty.
    """

    if not TRACE:
        return

    color_question_mark = use_color if use_color is not None else _supports_color(file)
    accent = "\033[1m" if color_question_mark else ""
    dark = "\033[90;1m" if color_question_mark else ""
    clear = "\033[0m" if color_question_mark else ""
    print(f"{start}{accent}TRACE:{clear} {dark}{text}{clear}", end=end, file=file)



def preprocess_tyname(name: str) -> str:
    """
        Preprocesses eFLINT type names as Clingo would.
    """

    newname = ""
    for c in name:
        if (ord(c) >= ord('a') and ord(c) <= ord('z')) or (ord(c) >= ord('0') and ord(c) <= ord('9')) or c == '_' or c == '\'':
            newname += c
        elif (ord(c) >= ord('A') and ord(c) <= ord('Z')):
            newname += c.lower()
        else:
            newname += '_'
    return newname





##### EFLINT PARSING #####
class Line(abc.ABC):
    """
        Abstraction over either Statements or StatementGroups.
    """

    @abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

class Import(Line):
    """
        One of the few statements we try to understand. Represents either a `#require` or
        `#include`.
    """

    path: str
    # Basically, is a require
    only_when_not_done_already: bool

    def __init__(self, path: str, only_when_not_done_already: bool):
        self.path = path
        self.only_when_not_done_already = only_when_not_done_already
    @classmethod
    def require(cls, path: str) -> typing.Self:
        cls(path, True)
    @classmethod
    def include(cls, path: str) -> typing.Self:
        cls(path, False)

    def __str__(self) -> str:
        # NOTE: eFLINT REPL actually thinks the quotes are part of the path lol. So we don't serialize them.
        return f"#{'require' if self.only_when_not_done_already else 'include'} {self.path}"

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        """
            Parses an import statement from the head of the input.

            # Arguments
            - `input`: The input to analyze from.

            # Returns
            A tuple with the parsed import and the remaining input, or `None` if we didn't find
            a dot.
        """

        ptrace(f"Attempting 'Import.parse_eflint' on \"{input}\"")

        # Parse either of the magics
        require_magic = "#require"
        include_magic = "#include"
        if len(input) >= len(require_magic) and input[:len(require_magic)] == require_magic:
            only_when_not_done_already = True
            input = input[len(require_magic):].lstrip()
        elif len(input) >= len(include_magic) and input[:len(include_magic)] == include_magic:
            only_when_not_done_already = False
            input = input[len(include_magic):].lstrip()
        else:
            return None

        # Now we parse a string literal
        if (res := StringLit.parse_eflint(input)) is not None:
            path = res[0].value
            input = res[1].lstrip()
        else:
            perror(f"Expected string literal after '#{'require' if only_when_not_done_already else 'include'}' at \"{input}\"")
            exit(1)

        # Parse the closing dot
        if len(input) < 1 or input[0] != '.':
            perror(f"Expected '.' after path after '#{'require' if only_when_not_done_already else 'include'}' at \"{input}\"")
            exit(1)
        input = input[1:]

        # Done!
        return (cls(path, only_when_not_done_already), input)

class Statement(Line):
    """
        Defines an abstract statement. Abstract as in, we don't care what it is ~ we just want to
        differentiate between the different ones.
    """

    raw: str

    def __init__(self, raw: str):
        self.raw = raw

    def __str__(self) -> str:
        return f"{self.raw}."

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        """
            Parses a statement from the head of the input.

            This will simply parse *anything* until a dot is found.

            # Arguments
            - `input`: The input to analyze from.

            # Returns
            A tuple with the parsed statement and the remaining input, or `None` if we didn't find
            a dot.
        """

        ptrace(f"Attempting 'Statement.parse_eflint' on \"{input}\"")

        # Search for the dot
        value = ""
        state = "main"
        for i, c in enumerate(input):
            if state == "main":
                if c == '.':
                    # Done
                    return (cls(value.strip()), input[i+1:])
                # We need to escape strings and comments
                elif c == '"':
                    value += c
                    state = "string"
                    continue
                elif c == '/':
                    state = "comment_start_question_mark"
                    continue
                else:
                    value += c
                    continue
            elif state == "string":
                if c == '"':
                    # Done with strings
                    value += c
                    state = "main"
                    continue
                elif c == '\\':
                    state = "string-escape"
                    continue
                else:
                    value += c
                    continue
            elif state == "string-escape":
                if c == 'n':
                    value += '\n'
                    state = "string"
                    continue
                elif c == 'r':
                    value += '\r'
                    state = "string"
                    continue
                elif c == 't':
                    value += '\t'
                    state = "string"
                    continue
                else:
                    value += c
                    state = "string"
                    continue
            elif state == "comment_start_question_mark":
                if c == '/':
                    state = "comment"
                    continue
                # Else, re-do main for this char
                elif c == '.':
                    # Done
                    return (cls(value.strip()), input[i+1:])
                # We need to escape strings and comments
                elif c == '"':
                    value += c
                    state = "string"
                    continue
                else:
                    value += c
                    continue
            elif state == "comment":
                if c == '\n':
                    state = "main"
                    continue
                else:
                    continue
        perror(f"Missing '.' after statement in \"{input}\"")
        exit(1)

class StatementGroup(Line):
    """
        Multiple statements wrapped in `{}`
    """

    stmts: typing.List[Statement]

    def __init__(self, stmts: typing.List[Statement] = []):
        self.stmts = stmts

    def __str__(self) -> str:
        return "{" + ' '.join([str(stmt) for stmt in self.stmts]) + "}"

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        """
            Parses a statement group from the head of the input.

            This will parse multiple statements wrapped in curly brackets.

            # Arguments
            - `input`: The input to analyze from.

            # Returns
            A tuple with the parsed statement group and the remaining input, or `None` if we didn't find
            a dot.
        """

        ptrace(f"Attempting 'StatementGroup.parse_eflint' on \"{input}\"")

        # Parse the head curly bracket
        if len(input) < 1 or input[0] != '{':
            return None
        input = input[1:].lstrip()

        # Parse statements OR the curly bracket
        stmts = []
        while len(input) > 0:
            # Possibly parse the ending bracket
            if input[0] == '}':
                # Done!
                return (cls(stmts), input[1:])

            # Else, attempt to parse as a statement
            if (res := Statement.parse_eflint(input)) is not None:
                (stmt, rem) = res
                stmts.append(stmt)
                input = rem.lstrip()
                continue

            # Else, something we could not care less about
            perror(f"Expected either a closing brace '}}' or a statement in phrase group at \"{input}\"")
            exit(1)

        # Unexpected end-of-file
        perror(f"Expected closing brace '}}' after phrase group at \"{input}\"")

class Scenario:
    """
        Defines a scenario file, but such that we understand it.
    """

    # The statements
    stmts: typing.List[Line]

    def __init__(self, stmts: typing.List[Line] = []):
        self.stmts = stmts

    # def __str__(self) -> str:
    #     """
    #         Writes this instance to a string.
    #     """
    #     raise NotImplementedError()

    @classmethod
    def parse_eflint(cls, rem: str) -> typing_extensions.Self:
        """
            Parses this scenario from the input.

            # Arguments
            - `input`: The remaining input stream to parse.

            # Returns
            The parsed Scenario.

            This does not return the remaining input, as we shall parse the whole of it or die
            trying.

            # Fails
            This function will `exit()` the program if the input is not a valid specification.
        """

        # Parse phrases ad infinitum
        rem = rem.lstrip()
        stmts = []
        while len(rem) > 0:
            # lstrip comments
            while len(rem) >= 2 and rem[:2] == "//":
                rem = rem[2:]
                while len(rem) > 0 and rem[0] != '\n': rem = rem[1:]
                rem = rem.lstrip()
                if len(rem) == 0:
                    return cls(stmts)

            # Now attempt to parse a statement OR a group
            if (res := Import.parse_eflint(rem)) is not None:
                stmts.append(res[0])
                rem = res[1].lstrip()
            elif (res := StatementGroup.parse_eflint(rem)) is not None:
                if len(res[0].stmts) > 0:
                    stmts.append(res[0])
                rem = res[1].lstrip()
            elif (res := Statement.parse_eflint(rem)) is not None:
                # NOTE: Should be last, just parses up until a dot
                if len(res[0].raw.strip()) > 0:
                    stmts.append(res[0])
                rem = res[1].lstrip()
            else:
                perror(f"Failed to parse either a Statement or StatementGroup from \"{rem}\"")
                exit(1)

        # Done
        return cls(stmts)



class Fluent:
    """
        Represents the most abstract form of what we're parsing.
    """

    # The attribute itself.
    attr: str
    # Some instance it is attributing.
    inst: typing.Any     # NOTE: Cannot type annotate due to the cross-referencing

    def __init__(self, attr: str, inst: typing.Any):
        self.attr = attr
        self.inst = inst

    @staticmethod
    def _analyze_symbol_shape(symbol: clingo.Symbol) -> typing.Optional[typing.Tuple[str, str, clingo.Symbol, int]]:
        """
            Asserts the toplevel symbol state we expect for all symbols.

            # Arguments
            - `symbol`: The symbol to assert.

            # Returns
            A quadruplet of the function name, argument name, argument symbol and the parsed state number, or `None` if the assertion failed.
        """

        # All fluents should be wrapped in `in(..., ...)`
        if symbol.type != clingo.SymbolType.Function:
            ptrace(f"Clingo produced unexpected toplevel symbol {symbol} (not a function)")
            return None
        if symbol.name != "in":
            ptrace(f"Clingo produced unexpected toplevel symbol {symbol} (not \"in\")")
            return None
        if len(symbol.arguments) != 2:
            ptrace(f"Clingo produced unexpected toplevel symbol {symbol} (got arity {len(symbol.arguments)}, expected arity 2)")
            return None
        inst, state = symbol.arguments

        # Ensure the first argument is, in turn a two-arity function
        if inst.type != clingo.SymbolType.Function:
            ptrace(f"Clingo produced unexpected instance symbol {inst} in {symbol} (not a function)")
            return None
        if len(inst.name) != 0:
            ptrace(f"Clingo produced unexpected instance symbol {inst} in {symbol} (not an anonymous tuple)")
            return None
        if len(inst.arguments) != 2:
            ptrace(f"Clingo produced unexpected instance symbol {inst} in {symbol} (got arity {len(inst.arguments)}, expected arity 2)")
            return None
        inst_name, arg = inst.arguments

        # Now ensure that the name is an empty symbol
        if inst_name.type != clingo.SymbolType.Function:
            ptrace(f"Clingo produced unexpected argument name symbol {inst_name} in {symbol} (not a function)")
            return None
        if len(inst_name.arguments) != 0:
            ptrace(f"Clingo produced unexpected argument name symbol {inst_name} in {symbol} (got arity {len(inst_name.arguments)}, expected arity 0)")
            return None

        # Ensure the second argument is a state number
        if state.type != clingo.SymbolType.Number:
            ptrace(f"Clingo produced unexpected state symbol {state} in {symbol} (not a number)")
            return None
        i = state.number

        # OK! Done!
        return (inst_name.name, arg.name, arg, i)
    @classmethod
    def from_symbol(cls, symbol: clingo.Symbol, full_eval: bool = False) -> typing.Optional[typing.Tuple[typing_extensions.Self, int]]:
        """
            Attempts to build a recognized fluent out of the given Clingo symbol.

            # Arguments
            - `symbol`: The symbol to attmept to convert.
            - `full_eval`: Whether we do a full diff or not. Essentially, if true, then "create", "obfuscate" and "terminate" are normal symbols; else, they are seen as debug symbols.

            # Returns
            A new Fluent that is parsed from the symbol and the state it was derived in, or else
            `None` if it wasn't a valid fluent.
        """

        # Get the fluent's information
        res = Fluent._analyze_symbol_shape(symbol)
        if res is None: return None
        name, arg_name, arg, state = res

        # Now we're ready: match the function head
        if (not arg_name.startswith("aggr_")) and (name == "holds" or name == "trigger" or name == "actViolation" or name == "dutyViolation" or (full_eval and (name == "create" or name == "terminate" or name == "obfuscate"))):
            return (Fluent(name, Instance.from_clingo_symbol(arg)), state)
        else:
            ptrace(f"Clingo produced unknown fluent ({name}, {arg_name}({arg})@{state} in {symbol}")
            return None
    @classmethod
    def from_debug_symbol(cls, symbol: clingo.Symbol, full_eval: bool = False) -> typing.Optional[typing.Tuple[typing_extensions.Self, int]]:
        """
            Attempts to build a recognized debug fluent out of the given Clingo symbol.

            # Arguments
            - `symbol`: The symbol to attmept to convert.
            - `full_eval`: Whether we do a full diff or not. Essentially, if true, then "create", "obfuscate" and "terminate" are normal symbols; else, they are seen as debug symbols.

            # Returns
            A new Fluent that is parsed from the symbol and the state it was derived in, or else
            `None` if it wasn't a valid fluent.
        """

        # Get the fluent's information
        res = Fluent._analyze_symbol_shape(symbol)
        if res is None: return None
        name, arg_name, arg, state = res

        # Now we're ready: match the function head
        if arg_name.startswith("aggr_") or name == "add" or name == "rem" or name == "derived" or name == "enum" or name == "actTrigger" or name == "enabled" or name == "created" or name == "terminated" or name == "obfuscated" or name == "suppressed" or name == "violated" or (not full_eval and (name == "create" or name == "terminate" or name == "obfuscate")):
            return (Fluent(name, Instance.from_clingo_symbol(arg)), state)
        else:
            ptrace(f"Clingo produced unknown debug fluent ({name}, {arg_name}({arg})@{state} in {symbol}")
            return None

    def __eq__(self, other) -> bool:
        return self.attr == other.attr and self.inst == other.inst
    def __hash__(self) -> int:
        return hash((self.attr, self.inst))

    def __str__(self) -> str:
        return f"({self.attr}, {self.inst})"

class Instance(abc.ABC):
    """
        Defines an abstract eFLINT instance.
    """

    @classmethod
    def from_clingo_symbol(cls, symbol: clingo.Symbol) -> typing_extensions.Self:
        """
            Creates an appropriate instance from the given Clingo one.

            # Arguments
            - `symbol`: The Clingo Symbol to convert.

            # Returns
            An equivalent `StringLit`, `IntLit` or `Composite`.
        """

        ptrace(f"Applying 'Instance.from_clingo_symbol' on \"{symbol}\"")

        if symbol.type == clingo.SymbolType.String:
            return typing.cast(typing_extensions.Self, StringLit(symbol.string))
        elif symbol.type == clingo.SymbolType.Number:
            return typing.cast(typing_extensions.Self, IntLit(symbol.number))
        elif symbol.type == clingo.SymbolType.Function:
            return typing.cast(typing_extensions.Self, Composite(symbol.name, [Instance.from_clingo_symbol(arg) for arg in symbol.arguments]))
        else:
            perror(f"Cannot convert Clingo symbol \"{symbol}\" of unsupported symbol type \"{symbol.type}\"")
            exit(1)

    def __eq__(self, other) -> bool:
        if isinstance(self, StringLit) and isinstance(other, StringLit):
            return StringLit.__eq__(self, other)
        elif isinstance(self, IntLit) and isinstance(other, IntLit):
            return IntLit.__eq__(self, other)
        elif isinstance(self, Composite) and isinstance(other, Composite):
            return Composite.__eq__(self, other)
        else:
            return False
    def __hash__(self) -> int:
        if isinstance(self, StringLit):
            return hash((1, StringLit.__hash__(self)))
        elif isinstance(self, IntLit):
            return hash((2, IntLit.__hash__(self)))
        elif isinstance(self, Composite):
            return hash((3, Composite.__hash__(self)))

    @abc.abstractmethod
    def as_fluent(self) -> Fluent:
        raise NotImplementedError

    @abc.abstractmethod
    def __str__(self) -> str:
        """
            Writes this instance to a string.
        """
        raise NotImplementedError()

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        """
            Parses this instance from the head of the input.

            # Arguments
            - `input`: The remaining input stream to parse.

            # Returns
            A tuple of the parsed Instance and the head after parsing; or `None` if we failed to
            parse this instance.
        """

        ptrace(f"Attempting 'Instance.parse_eflint' on \"{input}\"")

        # Try a composite first
        # NOTE: mypy does not like the neat `(res := ...) is not None`-syntax. Hence this ugly beast
        comp: typing.Optional[typing.Tuple[Composite, str]] = Composite.parse_eflint(input)
        if comp is not None:
            compinst, rem = comp
            return typing.cast(typing_extensions.Self, compinst), rem
        lstr: typing.Optional[typing.Tuple[StringLit, str]] = StringLit.parse_eflint(input)
        if lstr is not None:
            strinst, rem = lstr
            return typing.cast(typing_extensions.Self, strinst), rem
        lint: typing.Optional[typing.Tuple[IntLit, str]] = IntLit.parse_eflint(input)
        if lint is not None:
            intinst, rem = lint
            return typing.cast(typing_extensions.Self, intinst), rem
        return None

class StringLit(Instance):
    """
        It's a string literal.
    """

    value: str

    def __init__(self, value: str):
        self.value = value

    def __eq__(self, other) -> bool:
        return self.value == other.value
    def __hash__(self) -> int:
        return hash(self.value)

    def as_fluent(self) -> Fluent:
        return Fluent("holds", self)

    def __str__(self) -> str:
        """
            Writes this string literal to a string.
        """
        return f"\"{self.value}\""

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        """
            Parses this string listeral from the head of the input.

            # Arguments
            - `input`: The remaining input stream to parse.

            # Returns
            A tuple of the parsed Instance and the head after parsing; or `None` if we failed to
            parse this string listeral.

            # Failing
            This function may `exit()` if it fails fatably - i.e., the output is confirmed a string
            literal but ill-formed (missing closing quote).
        """

        ptrace(f"Attempting 'StringLit.parse_eflint' on \"{input}\"")

        # Let's do a stateful lil' parser
        value = ""
        state = "open"
        for i, c in enumerate(input):
            if state == "open":
                if c == "\"":
                    state = "value"
                    continue
                elif ord(c) >= ord('A') and ord(c) <= ord('Z'):
                    value += c
                    state = "naked"
                    continue
                else:
                    # Not a string literal
                    return None
            elif state == "value":
                if c == '"':
                    # Done!
                    return (cls(value), input[i + 1:])
                elif c == '\\':
                    state = "escaped"
                    continue
                else:
                    value += c
                    continue
            elif state == "escaped":
                if c == 'n':
                    value += '\n'
                    state = "value"
                    continue
                elif c == 't':
                    value += '\t'
                    state = "value"
                    continue
                elif c == 'r':
                    value += '\r'
                    state = "value"
                    continue
                else:
                    value += c
                    state = "value"
                    continue
            elif state == "naked":
                if (ord(c) >= ord('a') and ord(c) <= ord('z')) or (ord(c) >= ord('A') and ord(c) <= ord('Z')) or (ord(c) >= ord('0') and ord(c) <= ord('9')):
                    value += c
                    continue
                else:
                    return (cls(value), input[i:])

        # If we got here, missing end quote
        perror("Missing ending quote in eFLINT output")
        exit(1)
class IntLit(Instance):
    """
        It's an int literal.
    """

    value: int

    def __init__(self, value: int):
        self.value = value

    def __eq__(self, other) -> bool:
        return self.value == other.value
    def __hash__(self) -> int:
        return hash(self.value)

    def as_fluent(self) -> Fluent:
        return Fluent("holds", self)

    def __str__(self) -> str:
        """
            Writes this integer literal to a string.
        """
        return f"{self.value}"

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        """
            Parses this int literal from the head of the input.

            # Arguments
            - `input`: The remaining input stream to parse.

            # Returns
            A tuple of the parsed Instance and the head after parsing; or `None` if we failed to
            parse this int literal.

            # Failing
            This function may `exit()` if it fails fatably - i.e., the output is confirmed a int
            literal but ill-formed (missing closing quote).
        """

        ptrace(f"Attempting 'IntLit.parse_eflint' on \"{input}\"")

        # Let's do a stateful lil' parser
        for i, c in enumerate(input):
            if ord(c) >= ord('0') and ord(c) <= ord('9'):
                continue
            elif i > 0:
                # Done!
                return (cls(int(input[:i])), input[i:])
            else:
                return None
        return None
class Composite(Instance):
    """
        A composite eFLINT type.
    """

    ty: str
    args: typing.List[Instance]

    def __init__(self, ty: str, args: typing.List[Instance] = []):
        self.ty = ty
        self.args = args

    def __eq__(self, other) -> bool:
        return self.ty == other.ty and self.args == other.args
    def __hash__(self) -> int:
        return hash((self.ty, tuple(self.args)))

    def as_fluent(self) -> Fluent:
        return Fluent("holds", self)

    def __str__(self) -> str:
        """
            Writes this composite to a string.
        """
        return f"{self.ty}({', '.join([str(arg) for arg in self.args])})"

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        """
            Parses this composite from the head of the input.

            # Arguments
            - `input`: The remaining input stream to parse.

            # Returns
            A tuple of the parsed Instance and the head after parsing; or `None` if we failed to
            parse this composite.

            # Failing
            This function may `exit()` if it fails fatably - i.e., the output is confirmed a
            composite but ill-formed (missing closing quote).
        """

        ptrace(f"Attempting 'Composite.parse_eflint' on \"{input}\"")

        # Parse an identifier first
        ty = None
        depth = 1
        state = "first"
        for i, c in enumerate(input):
            if state == "first":
                if (ord(c) >= ord('a') and ord(c) <= ord('z')) or c == '_':
                    state = "middle"
                    continue
                elif (c == '[' or c == '<'):
                    state = "delim-" + c
                    continue
                else:
                    return None
            elif state == "middle":
                if (ord(c) >= ord('a') and ord(c) <= ord('z')) or (ord(c) >= ord('A') and ord(c) <= ord('Z')) or c == '-' or c == '_':
                    continue
                elif (ord(c) >= ord('0') and ord(c) <= ord('9')) or c == '\'':
                    state = "end"
                    continue
                elif is_whitespace(c):
                    ty = input[:i]
                    input = input[i + 1:]
                    state = "whitespace"
                    continue
                elif c == '(':
                    ty = input[:i]
                    input = input[i + 1:]
                    break
                else:
                    # Missing the parenthesis
                    return None
            elif state == "end":
                if (ord(c) >= ord('0') and ord(c) <= ord('9')) or c == '\'':
                    continue
                elif is_whitespace(c):
                    ty = input[:i]
                    input = input[i + 1:]
                    state = "whitespace"
                    continue
                elif c == '(':
                    ty = input[:i]
                    input = input[i + 1:]
                    break
                else:
                    # Missing the parenthesis
                    return None
            elif state.startswith("delim-"):
                start = state[6:]
                end = ']' if start == '[' else '>'
                if c == start:
                    depth += 1
                    continue
                elif c == end:
                    if depth == 1:
                        # We're done! Move to popping whitespace
                        ty = input[:i + 1]
                        input = input[i + 1:]
                        state = "whitespace"
                        continue
                    else:
                        depth -= 1
                        continue
                else:
                    continue
            elif state == "whitespace":
                if is_whitespace(c):
                    input = input[1:]
                    continue
                elif c == '(':
                    input = input[1:]
                    break
                else:
                    # Something else than parenthesis follows
                    return None
        if ty is None:
            raise RuntimeError("This should not have happened")
        if state.startswith("delim-") and depth > 1:
            perror(f"Unterminated delimiter {c} at \"{input}\"")
            exit(1)

        # Empty is also allowed, for some reason...
        tinput = input.lstrip()
        if len(tinput) > 0 and tinput[0] == ')':
            return (cls(preprocess_tyname(ty), []), tinput[1:])

        # Now parse instances
        args = []
        while len(input) > 0:
            # Pop any whitespace first
            input = input.lstrip()

            # Attempt to parse an instance
            if (res := Instance.parse_eflint(input)) is not None:
                (inst, rem) = res
                args.append(inst)
                input = rem

                # Pop whitespace
                input = input.lstrip()

                # Require a comma or a parenthesis
                if len(input) > 0 and input[0] == ',':
                    input = input[1:]
                    continue
                elif len(input) > 0 and input[0] == ')':
                    # Done!
                    return (cls(preprocess_tyname(ty), args), input[1:])
                else:
                    # Missing closing parenthesis!
                    perror(f"Missing closing parenthesis in \"{input}\"")
                    exit(1)
            else:
                perror(f"Expected an instance after composite type opening parenthesis in \"{input}\"")
                exit(1)
        perror(f"Expected instances followed by a closing parenthesis after composite type in \"{input}\"")
        exit(1)

class InstanceTruth:
    """
        Parses an `<instance> = <True|False>`-pair.
    """

    inst: Instance
    value: bool

    def __init__(self, inst: Instance, value: bool):
        self.inst = inst
        self.value = value

    @classmethod
    def parse(cls, input: str) -> typing.Optional[typing.Tuple[typing_extensions.Self, str]]:
        ptrace(f"Attempting 'InstanceTruth.parse' on \"{input}\"")

        # Parse the instance
        if (res := Instance.parse_eflint(input)) is not None:
            inst = res[0]
            input = res[1]
        else:
            return None

        # Then parse the equals sign
        input = input.lstrip()
        if len(input) == 0 or input[0] != '=':
            return None
        input = input[1:]

        # Finally, parse the value
        input = input.lstrip()
        if len(input) >= 4 and input[:4] == "True":
            value = True
            input = input[4:]
        elif len(input) >= 5 and input[:5] == "False":
            value = False
            input = input[5:]
        else:
            perror(f"Expected boolean value after '<instance> = ' in \"{input}\"")
            exit(1)

        # Alright done
        return (cls(inst, value), input)

class Delta(abc.ABC):
    """
        Represents some eFLINT delta, like "instance created" or similar.
    """

    @abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def as_fluent(self) -> Fluent:
        raise NotImplementedError

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing.List[typing_extensions.Self], str]]:
        ptrace(f"Attempting 'Delta.parse_eflint' on \"{input}\"")

        # Attempt 'em one-by-one
        post: typing.Optional[typing.Tuple[typing.List[Postulation], str]] = Postulation.parse_eflint(input)
        if post is not None:
            postinst, rem = post
            return typing.cast(typing.List[typing_extensions.Self], postinst), rem
        trgr: typing.Optional[typing.Tuple[typing.List[Trigger], str]] = Trigger.parse_eflint(input)
        if trgr is not None:
            trgrinst, rem = trgr
            return typing.cast(typing.List[typing_extensions.Self], trgrinst), rem
        avio: typing.Optional[typing.Tuple[typing.List[ActViolation], str]] = ActViolation.parse_eflint(input)
        if avio is not None:
            avioinst, rem = avio
            return typing.cast(typing.List[typing_extensions.Self], avioinst), rem
        dvio: typing.Optional[typing.Tuple[typing.List[DutyViolation], str]] = DutyViolation.parse_eflint(input)
        if dvio is not None:
            dvioinst, rem = dvio
            return typing.cast(typing.List[typing_extensions.Self], dvioinst), rem
        tdef: typing.Optional[typing.Tuple[typing.List[TypeDef], str]] = TypeDef.parse_eflint(input)
        if tdef is not None:
            tdefinst, rem = tdef
            return typing.cast(typing.List[typing_extensions.Self], tdefinst), rem
        quer: typing.Optional[typing.Tuple[typing.List[Query], str]] = Query.parse_eflint(input)
        if quer is not None:
            querinst, rem = quer
            return typing.cast(typing.List[typing_extensions.Self], querinst), rem
        return None
class TypeDef(Delta):
    """
        Represents a type definition.

        Note actually used, just to parse the initial state snippet.
    """

    name: str

    def __init__(self, name: str):
        self.name = name

    def as_fluent(self) -> Fluent:
        return Fluent("newtype", StringLit(self.name))

    def __str__(self) -> str:
        return f"New type {self.name}."

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing.List[typing_extensions.Self], str]]:
        ptrace(f"Attempting 'TypeDef.parse_eflint' on \"{input}\"")

        # Parse the magic string
        magic = "New type "
        if len(input) < len(magic) or input[:len(magic)] != magic:
            return None
        input = input[len(magic):]

        # Then parse the name
        input = input.lstrip()
        state = "first"
        for i, c in enumerate(input):
            if state == "first":
                if (ord(c) >= ord('a') and ord(c) <= ord('z')) or c == '_':
                    state = "middle"
                    continue
                else:
                    perror(f"Expected identifier after '{magic}' in \"{input[i:]}\"")
                    exit(1)
            elif state == "middle":
                if (ord(c) >= ord('a') and ord(c) <= ord('z')) or (ord(c) >= ord('A') and ord(c) <= ord('Z')) or c == '-' or c == '_':
                    continue
                elif (ord(c) >= ord('0') and ord(c) <= ord('9')) or c == '\'':
                    state = "end"
                    continue
                elif is_whitespace(c):
                    break
                else:
                    perror(f"Expected non-first character of identifier after start of identifier in \"{input[i:]}\"")
                    exit(1)
            elif state == "end":
                if (ord(c) >= ord('0') and ord(c) <= ord('9')) or c == '\'':
                    continue
                elif is_whitespace(c):
                    break
                else:
                    perror(f"Expected identifier suffix after identifier with suffix in \"{input[i:]}\"")
                    exit(1)

        # Done
        return ([cls(input[:i])], input[i:])
class Postulation(Delta):
    """
        Represents a postulation thingy.
    """

    action: str   # Only ever '+', '-' or '~'
    inst: Instance

    def __init__(self, action: str, inst: Instance):
        if action != '+' and action != '-' and action != '~':
            raise RuntimeError(f"'action' in 'Postulation(...)' must always be '+', '-' or '~' (got \"{action}\")")
        self.action = action
        self.inst = inst

    def as_fluent(self) -> Fluent:
        return Fluent("create" if self.action == '+' else ("terminate" if self.action == '-' else "obfuscate"), self.inst)

    def __str__(self) -> str:
        return f"{self.action}{self.inst}."

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing.List[typing_extensions.Self], str]]:
        ptrace(f"Attempting 'Postulation.parse_eflint' on \"{input}\"")

        # Attempt to parse the action first
        if len(input) < 1 or (input[0] != '+' and input[0] != '-' and input[0] != '~'):
            return None
        action = input[0]
        input = input[1:]

        # Then parse the instance
        input = input.lstrip()
        if (res := Instance.parse_eflint(input)) is not None:
            inst = res[0]
            input = res[1]
        else:
            perror(f"Expected instance after postulation action '{action}' in \"{input}\"")
            exit(1)

        # Done
        return ([cls(action, inst)], input)
class Trigger(Delta):
    """
        Represents the triggering of an action.
    """

    act: Instance

    def __init__(self, act: Instance):
        self.act = act

    def as_fluent(self) -> Fluent:
        return Fluent("trigger", self.act)

    def __str__(self) -> str:
        return f"{self.act}."

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing.List[typing_extensions.Self], str]]:
        ptrace(f"Attempting 'Trigger.parse_eflint' on \"{input}\"")

        # Parse the magic word
        magic = "executed transition:"
        if len(input) < len(magic) or input[:len(magic)] != magic:
            return None
        input = input[len(magic):].lstrip()

        # Parse the triggered instance
        if (res := Instance.parse_eflint(input)) is not None:
            act = res[0]
            input = res[1]
        else:
            perror(f"Expected instance after '{magic.strip()}' in \"{input}\"")
            exit(1)

        # Parse "enabled", optionally
        input = input.lstrip()
        if len(input) >= 1 and input[0] == '(':
            input = input[1:]

            # Parse the enabled/disabled keyword
            input = input.lstrip()
            if len(input) >= 7 and input[:7] == "ENABLED":
                _enabled = True
                input = input[7:]
            elif len(input) >= 8 and input[:8] == "DISABLED":
                _enabled = False
                input = input[8:]
            else:
                perror(f"Expected '(ENABLED|DISABLED)' after instance in \"{input}\"")
                exit(1)

            # Finally, parse the closing bracket
            input = input.lstrip()
            if len(input) < 1 or input[0] != ')':
                perror(f"Expected closing parenthesis after '(ENABLED|DISABLED)' in \"{input}\"")
                exit(1)
            input = input[1:]

        # Now parse any tree
        tinput = input.lstrip()
        if len(tinput) >= 1 and tinput[0] == '|':
            # Trigger tree syntax
            input = tinput
            acts = [act]
            while len(input) >= 1 and input[0] == '|':
                input = input[1:]

                # Parse the hook of the branch
                input = input.lstrip()
                if len(input) < 1 or input[0] != '`':
                    perror(f"Expected '`-' after '|' in \"{input}\"")
                    exit(1)
                input = input[1:]

                # Parse the horizontal part of the branch
                input = input.lstrip()
                if len(input) < 1 or input[0] != '-':
                    perror(f"Expected '-' after '|`' in \"{input}\"")
                    exit(1)
                input = input[1:]

                # Great, now parse the instance
                input = input.lstrip()
                if (res := Instance.parse_eflint(input)) is not None:
                    acts.append(res[0])
                    input = res[1]
                else:
                    perror(f"Expected instance after '|`-' in \"{input}\"")
                    exit(1)

                # Optionaly parse ENABLED|DISABLED again
                input = input.lstrip()
                if len(input) >= 1 and input[0] == '(':
                    input = input[1:]

                    # Parse the enabled/disabled keyword
                    input = input.lstrip()
                    if len(input) >= 7 and input[:7] == "ENABLED":
                        _enabled = True
                        input = input[7:]
                    elif len(input) >= 8 and input[:8] == "DISABLED":
                        _enabled = False
                        input = input[8:]
                    else:
                        perror(f"Expected '(ENABLED|DISABLED)' after instance in \"{input}\"")
                        exit(1)

                    # Finally, parse the closing bracket
                    input = input.lstrip()
                    if len(input) < 1 or input[0] != ')':
                        perror(f"Expected closing parenthesis after '(ENABLED|DISABLED)' in \"{input}\"")
                        exit(1)
                    input = input[1:]

                # Try again if there's still trees to go
                input = input.lstrip()
            acts.reverse()

            # Done
            return ([cls(act) for act in acts], input)

        # Done as well
        return ([cls(act)], input)
class ActViolation(Delta):
    """
        Represents the violation of an action.
    """

    act: Instance

    def __init__(self, act: Instance):
        self.act = act

    def as_fluent(self) -> Fluent:
        return Fluent("actViolation", self.act)

    def __str__(self) -> str:
        return f"!!!{self.act}"

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing.List[typing_extensions.Self], str]]:
        ptrace(f"Attempting 'ActViolation.parse_eflint' on \"{input}\"")

        # Parse the magic word
        magic = "violations:"
        if len(input) < len(magic) or input[:len(magic)] != magic:
            return None
        input = input[len(magic):].lstrip()

        # Now parse multiple instances
        prompt = "disabled action: "
        tinput = input.lstrip()
        acts = []
        while len(tinput) >= len(prompt) and tinput[:len(prompt)] == prompt:
            input = tinput[len(prompt):]

            # Parse the violated instance
            input = input.lstrip()
            if (res := Instance.parse_eflint(input)) is not None:
                acts.append(res[0])
                input = res[1]
            else:
                perror(f"Expected instance after '{prompt.strip()}' in \"{input}\"")
                exit(1)

            # Try again
            tinput = input.lstrip()
        if len(acts) == 0:
            return None

        # Done
        return ([typing.cast(typing_extensions.Self, cls(act)) for act in acts], input)
class DutyViolation(Delta):
    """
        Represents the violation of a duty.
    """

    duty: Instance

    def __init__(self, duty: Instance):
        self.duty = duty

    def as_fluent(self) -> Fluent:
        return Fluent("dutyViolation", self.duty)

    def __str__(self) -> str:
        return f"!!!{self.duty}"

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing.List[typing_extensions.Self], str]]:
        ptrace(f"Attempting 'DutyViolation.parse_eflint' on \"{input}\"")

        # Parse the magic word
        magic = "violations:"
        if len(input) < len(magic) or input[:len(magic)] != magic:
            return None
        input = input[len(magic):].lstrip()

        # Now parse multiple instances
        prompt = "violated duty!: "
        tinput = input.lstrip()
        acts = []
        while len(tinput) >= len(prompt) and tinput[:len(prompt)] == prompt:
            input = tinput[len(prompt):]

            # Parse the violated instance
            input = input.lstrip()
            if (res := Instance.parse_eflint(input)) is not None:
                acts.append(res[0])
                input = res[1]
            else:
                perror(f"Expected instance after '{prompt.strip()}' in \"{input}\"")
                exit(1)

            # Try again
            tinput = input.lstrip()
        if len(acts) == 0:
            return None

        # Done
        return ([typing.cast(typing_extensions.Self, cls(act)) for act in acts], input)
class Query(Delta):
    """
        Represents a query result.

        Note actually used, just to parse the initial state snippet.
    """

    success: bool

    def __init__(self, success: bool):
        self.success = success

    def as_fluent(self) -> Fluent:
        return Fluent("query", StringLit("successful" if self.success else "failure"))

    def __str__(self) -> str:
        return f"query {'successful' if self.name else 'failed'}."

    @classmethod
    def parse_eflint(cls, input: str) -> typing.Optional[typing.Tuple[typing.List[typing_extensions.Self], str]]:
        ptrace(f"Attempting 'Query.parse_eflint' on \"{input}\"")

        # Parse the magic string
        success_magic = "query successful"
        failure_magic = "query failed"
        if len(input) >= len(success_magic) and input[:len(success_magic)] == success_magic:
            return ([cls(True)], input[len(success_magic):])
        elif len(input) >= len(failure_magic) and input[:len(failure_magic)] == failure_magic:
            return ([cls(False)], input[len(failure_magic):])
        else:
            return None



class State:
    """
        Represents a parsed state.

        This contains both the transitions (to find e.g. violations) and knowledge bases.
    """

    i: typing.Optional[int]
    fluents: typing.List[Fluent]
    debug_fluents: typing.List[Fluent]

    def __init__(self, i: typing.Optional[int] = None, fluents: typing.List[Fluent] = list(), debug_fluents: typing.List[Fluent] = list()):
        self.i = i
        self.fluents = copy.deepcopy(fluents)
        self.debug_fluents = copy.deepcopy(debug_fluents)

    @classmethod
    def from_eflint_snippets(cls, snippets: typing.List[typing.Tuple[str, str]], full_eval: bool = False) -> typing.List[typing_extensions.Self]:
        """
            Creates States by reading a list of eFLINT _event snippet_ and _knowledge base snippet_ pairs.

            # Arguments
            - `snippets`: A list of (`event_snippet`, `kb_snippet`)-pairs that describe the per-state deltas and instances.
            - `full_eval`: Whether we do a full diff or not. Essentially, if true, then "create", "obfuscate" and "terminate" are normal symbols; else, they are seen as debug symbols.

            # Returns
            A new instance of a State that equals the state as described by the two snippets.
        """

        # Do all of the states
        result = []
        deltas_carry = []
        for i, (event_snippet, kb_snippet) in enumerate(snippets):
            i = i + 1
            state = cls(i=i)

            # Parse the knowledge base snippet first
            state.fluents = list()
            kb_snippet = kb_snippet.lstrip()
            while len(kb_snippet) > 0:
                res: typing.Optional[typing.Tuple[InstanceTruth, str]] = InstanceTruth.parse(kb_snippet)
                if res is not None:
                    if res[0].value:
                        state.fluents.append(res[0].inst.as_fluent())
                    kb_snippet = res[1]
                else:
                    perror(f"Expected '<instance> = <True|False>' in knowledge base snippet \"{kb_snippet}\"")
                    exit(1)

                # Clear whitespace and try again
                kb_snippet = kb_snippet.lstrip()

            # Then try the events
            new_deltas_carry = []
            event_snippet = event_snippet.lstrip()
            while len(event_snippet) > 0:
                dlt = Delta.parse_eflint(event_snippet)
                if dlt is not None:
                    for delta in dlt[0]:
                        if isinstance(delta, DutyViolation):
                            # Duty violations need to be pushed one state later
                            new_deltas_carry.append(delta)
                        elif (not isinstance(delta, Postulation) or full_eval) and not isinstance(delta, TypeDef):
                            state.fluents.append(delta.as_fluent())
                        else:
                            state.debug_fluents.append(delta.as_fluent())
                    event_snippet = dlt[1]
                else:
                    perror(f"Expected delta in event snippet \"{event_snippet}\"")
                    exit(1)

                # Clear whitespace and try again
                event_snippet = event_snippet.lstrip()
            pdebug(f"Parsed {len(state.fluents)} fluent(s) for state {i}")

            # Also add the carry-over from the last state
            if i > 1:
                pdebug(f"Carried {len(deltas_carry)} delta(s) over from last state {i - 1}")
                state.fluents += [delta.as_fluent() for delta in deltas_carry]
            deltas_carry = new_deltas_carry

            # Done
            result.append(state)

        # Done
        return typing.cast(typing.List[typing_extensions.Self], result)

    def __str__(self) -> str:
        return "State" + (f" {self.i}" if self.i is not None else "") + "\n" + (80 * "-") + "\n" + "\n".join([f"{elem.attr_name()}({elem.instance()})" for elem in self.fluents]) + "\n" + (80 * '-') + "\n"

class Diff:
    """
        Represents a diff between two states.
    """

    left: State
    right: State

    def __init__(self, left: State, right: State):
        self.left = left
        self.right = right

    @classmethod
    def list(cls, left: typing.List[State], right: typing.List[State]) -> typing.List[typing_extensions.Self]:
        """
            Diffs a list of States.

            # Arguments
            - `left`: A list of states to diff on the left side.
            - `right`: A list of states to diff on the right side.

            # Returns
            A new list of Diffs that describes the change for every item.

            If the lists are different in length, then missing items are populated with Diffs that
            show all items occurring from the other side (i.e., we interpret a missing item as an
            empty State).
        """

        max_len = max(len(left), len(right))
        eq_left = left + [State(i=len(left) + i) for i in range(max_len - len(left))]
        eq_right = right + [State(i=len(right) + i) for i in range(max_len - len(right))]
        return [cls(left, right) for left, right in zip(eq_left, eq_right)]



    @staticmethod
    # Note: `0` means same, `< 0` means it exists in left but not in right, `> 0` means it exists
    # in right but not in left.
    def diff(left: typing.List[Fluent], right: typing.List[Fluent]) -> typing.Dict[Fluent, int]:
        # We begin with setting everything to left
        res = {l: -1 for l in left}
        # Then, progressively, add things for right or move them in the middle
        for r in right:
            if r in res:
                res[r] = 0
            else:
                res[r] = 1
        return res



    def __bool__(self) -> bool:
        diff = Diff.diff(self.left.fluents, self.right.fluents)
        for same in diff.values():
            if same != 0: return True
        return False

    def max_column_width(self) -> int:
        max_width = max(len(EFLINT_HEADER_NAME), len(CLINGO_HEADER_NAME))
        for fluent in self.left.fluents + self.right.fluents + (self.left.debug_fluents + self.right.debug_fluents if DEBUG else []):
            max_width = max(max_width, len(str(fluent)))
        return max_width

    def show(self, state: int, max_state: int, max_width: int, file: typing.TextIO=sys.stdout, use_color: typing.Optional[bool]=None):
        """
            Renders the difference between the first (left) and second (right) states.

            # Arguments
            - `state`: State index.
            - `max_state`: The largest state we would ever print.
            - `max_width`: The maximum column width.
            - `file`: A file to write to.
            - `use_color`: Whether to enforce ANSI colors or not, or leave them on auto (`None`).
        """

        color_question_mark = use_color if use_color is not None else _supports_color()
        red = "\033[91;1m" if color_question_mark else ""
        bold = "\033[1m" if color_question_mark else ""
        dark = "\033[90;1m" if color_question_mark else ""
        clear = "\033[0m" if color_question_mark else ""

        # Split the diff
        diff = Diff.diff(self.left.fluents, self.right.fluents)
        debug_diff = Diff.diff(self.left.debug_fluents, self.right.debug_fluents)

        # Print the header
        max_state_width = len(str(max_state))
        print(f"{bold}{str(state).rjust(max_state_width, '0')} +-{EFLINT_HEADER_NAME.ljust(max_width, '-')}{clear}-+-{bold}{CLINGO_HEADER_NAME.ljust(max_width, '-')}{clear}-+", file=file)

        # Sort the keys by string, first
        keys = list(diff.keys())
        if DEBUG: keys += list(debug_diff.keys())
        keys.sort(key=lambda fluent: str(fluent))

        # Loop to show the diff
        for fluent in keys:
            if fluent in diff:
                suffix = ""
                side = diff[fluent]
                if side < 0:
                    marker = '<'
                    accent = red
                    cleans = clear
                elif side > 0:
                    marker = '>'
                    accent = red
                    cleans = clear
                else:
                    marker = ' '
                    accent = bold
                    cleans = clear
            else:
                suffix = "(debug)"
                side = debug_diff[fluent]
                if side < 0:
                    marker = '<'
                    accent = dark
                    cleans = clear
                elif side > 0:
                    marker = '>'
                    accent = dark
                    cleans = clear
                else:
                    marker = ' '
                    accent = dark
                    cleans = clear
            print(f"{accent}{marker.ljust(max_state_width)} | " + (str(fluent).ljust(max_width) if side <= 0 else max_width * " ") + f" | " + (str(fluent).ljust(max_width) if side >= 0 else max_width * " ") + f" | {suffix}{cleans}", file=file)





##### RUNNING FUNCTIONS #####
def find_tests(tests: typing.List[str], types: typing.List[str], spec_suffixes: typing.List[str], same_suffixes: typing.List[str], diff_suffixes: typing.List[str], perf_suffixes: typing.List[str], strict_perf: bool) -> typing.List[typing.Tuple[str, str, str, str]]:
    """
        Searches the test directories to find tests to run.

        # Arguments
        - `tests`: A list of paths to search for tests in.
        - `spec_suffixes`: Suffixes of specification files.
        - `same_suffixes`: Suffixes of same scenario files.
        - `diff_suffixes`: Suffixes of diff scenario files.
        - `perf_suffixes`: Suffixes of perf scenario files.
        - `strict_perf`: Whether to _not_ generate equality tests for performance tests.

        # Returns
        A  list of (base name, specification, scenario, type) triplets to test, where `type` is one
        of:
        1. `same`, to mark an equality test;
        2. `diff`, to mark a difference test; or
        3. `perf`, to mark a performance benchmark.
    """

    # Search through the test directory
    res = []      # pairs of (name without suffix, scene file, spec file, test type)
    for test in tests:
        todo = [test]
        while len(todo) > 0:
            path = todo.pop()
            if os.path.isfile(path):
                ptrace(f"Test path '{path}' points to a file")
                if (root := strip_suffix(path, same_suffixes)) is not None:
                    # Equality test
                    test_tys = ["same"]
                elif (root := strip_suffix(path, diff_suffixes)) is not None:
                    # Difference test
                    test_tys = ["diff"]
                elif (root := strip_suffix(path, perf_suffixes)) is not None:
                    # Difference test
                    test_tys = ["perf"] + (["same"] if not strict_perf else [])
                else:
                    if strip_suffix(path, spec_suffixes) is None:
                        if path in tests:
                            plog = pwarn
                        else:
                            plog = pdebug
                        plog(f"Skipping test file \"{path}\" as it does not end in a same scene suffix")
                    continue

                # Maybe skip this test
                test_tys = [test_ty for test_ty in test_tys if test_ty in types]
                if len(test_tys) == 0:
                    pdebug(f"Skipping test file \"{path}\" as it is not in the set of test types (expected: {types})")
                    continue

                # Find the matching specification file
                for suffix in spec_suffixes:
                    spec = root + suffix
                    if os.path.isfile(spec):
                        # Add the pair!
                        for test_ty in test_tys:
                            res.append((path, spec, path, test_ty))
                    else:
                        pwarn(f"Cannot find specification \"{spec}\" for scene file \"{path}\" (or it is not a file); skipping scene file")
                        continue

            elif os.path.isdir(path):
                ptrace(f"Test path '{path}' points to a directory")
                for entry in os.listdir(path):
                    entry_path = os.path.join(path, entry)
                    if os.path.isfile(entry_path):
                        todo.append(entry_path)
                    elif os.path.isdir(entry_path):
                        if entry == "uncovered":
                            pdebug(f"Skipping \"{entry_path}\" as it's marked as an uncovered directory")
                        else:
                            todo.append(entry_path)
                    else:
                        pwarn(f"Skipping \"{entry_path}\" as it's neither a file, nor a direcotry")

            else:
                perror(f"Given test path \"{path}\" is not a file nor a directory (does it exist?)")
                exit(1)
    pdebug(f"Found {len(res)} specification/scenario pair(s)")
    res.sort(key=lambda a: a[0])
    return res

def compile_spec(spec: str, scen: typing.Optional[str], cabal_exec: typing.List[str], core_lib: typing.Optional[str]) -> str:
    """
        Runs the Haskell interpreter to obtain a Clingo specification.

        # Arguments
        - `spec`: The path to the specification file to run.
        - `scen`: The path to a scenario file to run. If none is given, does not run any.
        - `cabal_exec`: The command to run Cabal.
        - `core_lib`: An optional path to a file to load the core eFLINT from (or `None`, if we use the default). May be `-` to load from stdin.

        # Returns
        The compiled Clingo spec.

        Note that it already has been stripped of whitespace on either ends.
    """

    cmd = cabal_exec + ["run", "eflint-repl", "--", spec] + ([] if core_lib is None else ["--clingo-no-libs"])
    pdebug(f"Calling \"{cmd}\"...")
    handle = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (bstdout, bstderr) = handle.communicate(f":clingo {scen}\n:q\n".encode("utf-8"))
    (stdout, stderr) = (bstdout.decode('utf-8'), bstderr.decode('utf-8'))
    if handle.returncode != 0:
        perror(f"Command \"{cmd}\" returned non-zero exit code {handle.returncode}\n\nstdout:\n{80 * '-'}\n{stdout}\n{80 * '-'}\n\nstderr:\n{80 * '-'}\n{stderr}\n{80 * '-'}\n\n")
    pdebug(f"Command \"{cmd}\" exited with code {handle.returncode}")

    # Ensure stderr is empty
    if len(stderr.strip()) > 0:
        pwarn(f"Reasoner returned non-empty stderr:\n{80 * '-'}\n{stderr}\n{80 * '-'}\n\n")

    # Get the area in between the prompts and that is the compiled bit
    res = get_area_in_between_last_prompts(stdout)
    if res is not None:
        if core_lib is not None: pdebug(f"Injecting core library\n\nCore lib:\n{80 * '-'}\n{core_lib}\n{80 * '-'}\n")
        return ("" if core_lib is None else core_lib + "\n") + res[0]
    else:
        perror(f"eFLINT did not output prompts in stdout:\n{80 * '-'}\n{stdout}\n{80 * '-'}\n\n")
        exit(1)

def run_spec_scen_eflint(spec: str, scen: str, cabal_exec: typing.List[str], full_eval: bool) -> typing.List[State]:
    """
        Runs the Haskell interpreter on the given specification / scenario pair.

        # Arguments
        - `spec`: The path to the specification file to run.
        - `scen`: The path to a scenario file to run.
        - `cabal_exec`: The command to run Cabal.
        - `full_eval`: Whether we do a full diff or not. Essentially, if true, then "create", "obfuscate" and "terminate" are normal symbols; else, they are seen as debug symbols.

        # Returns
        The results as parsed from the results of the reasoner.
    """

    # Build eFLINT first of first
    cmd = cabal_exec + ["build", "eflint-repl"]
    pdebug(f"Calling \"{cmd}\"...")
    handle = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (bstdout, bstderr) = handle.communicate("")
    (stdout, stderr) = (bstdout.decode('utf-8'), bstderr.decode('utf-8'))
    if handle.returncode != 0:
        perror(f"eFLINT build command \"{cmd}\" returned non-zero exit code {handle.returncode}\n\nstdout:\n{80 * '-'}\n{stdout}\n{80 * '-'}\n\nstderr:\n{80 * '-'}\n{stderr}\n{80 * '-'}\n\n")
    pdebug(f"Command \"{cmd}\" exited with code {handle.returncode}")

    # First, we parse the scenario file as a scenario
    with open(scen, "r") as h:
        # SUPER SECRET PLAN: eFLINT will see _one_ additional state such that we can fake the "initial" transition. Let's see if this works.
        scenario = Scenario.parse_eflint("?string.\n" + h.read())

    # Build the instruction string with it
    instr = "".join([":d\n" + str(stmt) + "\n" for stmt in scenario.stmts]) + ":d\n:q\n"

    # Run the cmd now
    cmd = cabal_exec + ["run", "eflint-repl", "--", spec]
    pdebug(f"Calling \"{cmd}\"...")
    handle = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (bstdout, bstderr) = handle.communicate(instr.encode("utf-8"))
    (stdout, stderr) = (bstdout.decode('utf-8'), bstderr.decode('utf-8'))
    if handle.returncode != 0:
        perror(f"Command \"{cmd}\" returned non-zero exit code {handle.returncode}\n\nstdout:\n{80 * '-'}\n{stdout}\n{80 * '-'}\n\nstderr:\n{80 * '-'}\n{stderr}\n{80 * '-'}\n\n")
    pdebug(f"Command \"{cmd}\" exited with code {handle.returncode}")

    # Ensure stderr is empty
    if len(stderr.strip()) > 0:
        pwarn(f"Reasoner returned non-empty stderr:\n{80 * '-'}\n{stderr}\n{80 * '-'}\n\n")
    pdebug(f"Raw eFLINT output:\n{80 * '-'}\n{stdout}\n{80 * '-'}")

    # First: we parse the state of the _last_ snippet
    res = get_area_in_between_last_prompts(stdout)
    if res is None:
        perror(f"Expected initial knowledge base snippet in reasoner response")
        exit(1)
    kb_snippet, prompt0, prompt1 = res
    stdout = stdout[:prompt1]
    pdebug(f"Final state snippet:\n\nknowledge base:\n{80 * '-'}\n{kb_snippet}\n{80 * '-'}\n")

    # Go backwards through all the rest of the prompts
    snippets: typing.List[typing.Tuple[str, str]] = [("", kb_snippet)]
    while len(stdout) > 0:
        # Get the second state, which is the instance one
        res = get_area_in_between_last_prompts(stdout)
        if res is None: break
        event_snippet, _, prompt1 = res
        stdout = stdout[:prompt1]

        # Get the first state, which is the event one
        res = get_area_in_between_last_prompts(stdout)
        if res is None:
            perror(f"Expected knowledge base snippet to come after event snippet")
            exit(1)
        kb_snippet, prompt0, prompt1 = res
        stdout = stdout[:prompt1]

        # Store them
        pdebug(f"State snippets:\n\nknowledge base:\n{80 * '-'}\n{kb_snippet}\n{80 * '-'}\n\nevent:\n{80 * '-'}\n{event_snippet}\n{80 * '-'}\n")
        snippets.append((event_snippet, kb_snippet))

    # Now parse the snippets
    snippets.reverse()
    states = State.from_eflint_snippets(snippets, full_eval=full_eval)
    pdebug(f"Reasoner returned {len(states)} state(s)")

    # Done
    return states[1:]

def run_spec_scen_clingo(spec: str, scen: str, cabal_exec: typing.List[str], full_eval: bool, core_lib: typing.Optional[str]) -> typing.List[State]:
    """
        Runs the Haskell interpreter on the given specification / scenario pair to get a Clingo
        translation, then runs a Clingo interpreter to obtain an answer.

        # Arguments
        - `spec`: The path to the specification file to run.
        - `scen`: The path to a scenario file to run.
        - `cabal_exec`: The command to run Cabal.
        - `full_eval`: Whether we do a full diff or not. Essentially, if true, then "create", "obfuscate" and "terminate" are normal symbols; else, they are seen as debug symbols.
        - `core_lib`: An optional path to a file to load the core eFLINT from (or `None`, if we use the default). May be `-` to load from stdin.

        # Returns
        The results as parsed from the results of the Clingo reasoner.
    """

    def is_state_symbol(symbol: clingo.Symbol) -> bool:
        if symbol.type != clingo.SymbolType.Function:
            return False
        if symbol.name != "state":
            return False
        if len(symbol.arguments) != 1:
            return False
        arg, = symbol.arguments
        if arg.type != clingo.SymbolType.Number:
            return False
        return True

    # Compile the Clingo snippet first
    cspec = compile_spec(spec, scen, cabal_exec, core_lib=core_lib)
    pdebug(f"Compiled Clingo snippet:\n{80 * '-'}\n{cspec}\n{80 * '-'}")

    # Obtain all models
    pdebug("Calling Clingo...");
    ctl = clingo.Control(arguments=["--models", "0"])
    ctl.add("base", [], cspec)
    ctl.ground([("base", [])])
    with ctl.solve(yield_=True) as handle:
        models = list(handle)
        pdebug(f"Found {len(models)} model(s)")
        for i, model in enumerate(models):
            smodel = '\n'.join(str(symbol) for symbol in model.symbols(atoms=True))
            pdebug(f"Model {i}:\n{80 * '-'}\n{smodel}\n{80 * '-'}\n")

        # Reduce it to one (let's say the last)
        if len(models) > 1:
            pwarn("Clingo found multiple models; choosing the last one")
        elif len(models) == 0:
            pwarn("Clingo did not find any models; assuming empty model")
            return [State(i = 1)]
        model = models[-1]

        # Convert it to our result
        pdebug(f"Converting model {len(models) - 1} to States...")
        states = collections.defaultdict(lambda: State())
        for symbol in model.symbols(atoms=True):
            ptrace(f"Considering symbol {symbol}...")

            # Parse the symbol
            if is_state_symbol(symbol):
                # Thank you but we can ignore
                continue
            elif (res := Fluent.from_symbol(symbol, full_eval=full_eval)) is not None:
                (fluent, i) = res
                states[i].fluents.append(fluent)
            elif (res := Fluent.from_debug_symbol(symbol, full_eval=full_eval)) is not None:
                (fluent, i) = res
                states[i].debug_fluents.append(fluent)
            else:
                perror(f"Unrecognized symbol {symbol} in Clingo output")
                exit(1)

    # Cool!
    keys = list(states.keys())
    keys.sort()
    res = []
    for i in keys:
        states[i].i = i
        res.append(states[i])
    return res





##### ENTRYPOINT #####
def main(tests: typing.List[str], types: typing.List[str], spec_suffixes: typing.List[str], same_suffixes: typing.List[str], diff_suffixes: typing.List[str], perf_suffixes: typing.List[str], eflint_core: typing.Optional[str], cabal_exec: typing.List[str], full_eval: bool, all_diffs: bool, n_runs: int, strict_perf: bool, output_perf_path: typing.Optional[str], clingo_only: bool) -> int:
    """
        Entrypoint to the script.

        # Arguments
        - `tests`: A list of paths to search for test(s) in.
        - `types`: The set of types of tests to run.
        - `spec_suffixes`: Suffixes of specification files.
        - `same_suffixes`: Suffixes of same scenario files.
        - `diff_suffixes`: Suffixes of diff scenario files.
        - `perf_suffixes`: Suffixes of perf scenario files.
        - `eflint_core`: An optional path to a file to load the core eFLINT from (or `None`, if we use the default). May be `-` to load from stdin.
        - `cabal_exec`: The `cabal` command to run.
        - `full_eval`: Whether to compare also the trigger attributes ("create", "terminate", "obfuscate") in AB tests or not.
        - `all_diifs`: If given, shows all the diffs in the universe, regardless of whether there is a difference.
        - `n_runs`: The number of times to average performance runs over.
        - `strict_perf`: Whether to _not_ generate equality tests for performance tests.
        - `output_perf_path`: An (optional) path to write timing results to.
        - `clingo_only`: If given, does not run eFLINT timings during performance tests.

        # Returns
        The intended exit code. `0` means success, anything else means failure.
    """

    color_question_mark = _supports_color()
    green = "\033[92;1m" if color_question_mark else ""
    red = "\033[91;1m" if color_question_mark else ""
    blue = "\033[94;1m" if color_question_mark else ""
    bold = "\033[1m" if color_question_mark else ""
    clear = "\033[0m" if color_question_mark else ""

    pdebug(f"tests            : {tests}")
    pdebug(f"types            : {types}")
    pdebug(f"spec_suffixes    : {spec_suffixes}")
    pdebug(f"same_suffixes    : {same_suffixes}")
    pdebug(f"diff_suffixes    : {diff_suffixes}")
    pdebug(f"perf_suffixes    : {perf_suffixes}")
    pdebug(f"eflint_core      : " + ("None" if eflint_core is None else f"\"{eflint_core}\""))
    pdebug(f"cabal_exec       : \"{cabal_exec}\"")
    pdebug(f"full_eval        : {full_eval}")
    pdebug(f"all_diffs        : {all_diffs}")
    pdebug(f"n_runs           : {n_runs}")
    pdebug(f"strict_perf      : {strict_perf}")
    pdebug(f"output_perf_path : \"{output_perf_path}\"")
    pdebug(f"clingo_only      : {clingo_only}")

    # Load the eflint core
    core_lib = None
    if eflint_core is not None:
        if eflint_core == '-':
            core_lib = sys.stdin.read()
        else:
            with open(eflint_core, "r") as h:
                core_lib = h.read()

    # Find the tests
    compare_tests = find_tests(tests, types, spec_suffixes, same_suffixes, diff_suffixes, perf_suffixes, strict_perf)

    # Run 'em
    tests_ok = 0
    tests_fail = 0
    tests_perf = 0
    timings = {}
    for (name, spec, scen, test_ty) in compare_tests:
        print(f"Running {test_ty} test {bold}{name}{clear}... ")
        pdebug(f"Test \"{name}\" spec = \"{spec}\", scen = \"{scen}\"")

        # Decide on a correctness test or a performance benchmark
        if test_ty == "same" or test_ty == "diff":
            # Get the eFLINT answer
            pdebug("Obtaining eFLINT answer...", start="\n")
            eflint = run_spec_scen_eflint(spec, scen, cabal_exec, full_eval)

            # Get the Clingo spec & scenario combined
            pdebug("Obtaining Clingo answer...")
            clingo = run_spec_scen_clingo(spec, scen, cabal_exec, full_eval, core_lib=core_lib)

            # Now compare!
            any_diff = False
            diffs = Diff.list(eflint, clingo)
            max_column_width = max([diff.max_column_width() for diff in diffs])
            max_state = len(diffs)
            for i, diff in enumerate(diffs):
                any_diff |= bool(diff)

            # Print the diffs, if desired
            if all_diffs or (test_ty == "same" and any_diff) or (test_ty == "diff" and not any_diff):
                for i, diff in enumerate(diffs):
                    diff.show(i + 1, max_state, max_column_width)
                    if i == len(diffs) - 1:
                        print(f"{len(str(max_state)) * ' '} +-{max_column_width * '-'}-+-{max_column_width * '-'}-+")

            # Either print OK or FAIL
            if (test_ty == "same" and not any_diff) or (test_ty == "diff" and any_diff):
                print(f" > Test {green}OK{clear}")
                tests_ok += 1
            else:
                print(f" > Test {red}FAIL{clear}")
                tests_fail += 1
        elif test_ty == "perf":
            eflint_total = (0.0 if not clingo_only else None)
            clingo_1_total = 0.0
            timings[scen] = []
            for i in range(n_runs):
                # Time eFLINT's answer
                eflint_time = None
                if not clingo_only:
                    eflint_start = time.time()
                    pdebug("Timing eFLINT answer...", start="\n")
                    _ = run_spec_scen_eflint(spec, scen, cabal_exec, full_eval)
                    eflint_time = time.time() - eflint_start
                    eflint_total += eflint_time

                # Time Clingo's single-threaded answer
                clingo_1_start = time.time()
                pdebug("Timing Clingo single-threaded answer...", start="\n")
                _ = run_spec_scen_clingo(spec, scen, cabal_exec, full_eval, core_lib=core_lib)
                clingo_1_time = time.time() - clingo_1_start
                clingo_1_total += clingo_1_time

                # Report it
                if not clingo_only:
                    pdebug(f"eFLINT: {eflint_time:.2f}s, Clingo 1T: {clingo_1_time:.2f}s ({i+1}/{n_runs})")
                else:
                    pdebug(f"Clingo 1T: {clingo_1_time:.2f}s ({i+1}/{n_runs})")
                timings[scen].append((i+1,eflint_time, clingo_1_time))
            if not clingo_only:
                print(f" > Performance: {bold}eFLINT{clear} {blue}{eflint_total/n_runs:.2f}s{clear}, {bold}Clingo 1T{clear} {blue}{clingo_1_total/n_runs:.2f}s{clear} (average of {n_runs} runs)")
            else:
                print(f" > Performance: {bold}Clingo 1T{clear} {blue}{clingo_1_total/n_runs:.2f}s{clear} (average of {n_runs} runs)")
            tests_perf += 1

        else:
            raise RuntimeError(f"Unknown test type \"{test_ty}\"")

    # Done!
    print(f"{tests_ok} test(s) pass, {tests_fail} test(s) fail, {tests_perf} performance test(s)")
    if output_perf_path is not None:
        pdebug(f"Writing timing results to '{output_perf_path}'...")
        with open(output_perf_path, "w") as h:
            h.write(f"name,run,{'eflint_time_s,' if not clingo_only else ''}clingo_1_time_s\n")
            for scen in timings:
                for run, eflint, clingo_1 in timings[scen]:
                    if not clingo_only:
                        h.write(f"{scen},{run},{eflint},{clingo_1}\n")
                    else:
                        h.write(f"{scen},{run},{clingo_1}\n")
        print(f" > Written timing results to {bold}{output_perf_path}{clear}")
    return 0



# Actual entrypoint
if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--test", default=["./tests/clingo"], nargs='*', type=str, help="The file or directory to search for test cases in. You can either point to a scene file, or to a directory containing scene files. In either case, the spec file is assumed to be there next to it.")
    parser.add_argument("-T", "--types", default=["same","diff","perf"], nargs="*", type=str, help="Types of tests to run when looking for files. You can choose from 'same', 'diff' or 'perf'.")
    parser.add_argument("-S", "--spec-suffix", default=[".spec.eflint"], nargs="+", type=str, help="Suffix(es) of specification files. Any file who's name ends with one of the given suffixes is considered a specification to be given as direct input to the eFLINT reasoner.")
    parser.add_argument("-s", "--same-suffix", default=[".same$n$.eflint"], nargs="+", type=set, help="Suffix(es) of scenario files. Any file who's name ends with one of the given suffixes is considered a scenario for which eFLINT and Clingo must give the same knowledge bases. It is run with a specification with the same prefix. Use '$n$' to mean any number.")
    parser.add_argument("-d", "--diff-suffix", default=[".diff$n$.eflint"], nargs="+", type=set, help="Suffix(es) of scenario files. Any file who's name ends with one of the given suffixes is considered a scenario for which eFLINT and Clingo must give DIFFERENT knowledge bases. It is run with a specification with the same prefix. Use '$n$' to mean any number.")
    parser.add_argument("-p", "--perf-suffix", default=[".perf$n$.eflint"], nargs="+", type=set, help="Suffix(es) of scenario files. Any file who's name ends with one of the given suffixes is considered a scenario for which we time both eFLINT and Clingo's runtime. It is run with a specification with the same prefix. Use '$n$' to mean any number.")
    parser.add_argument("-c", "--cabal-exec", default="cabal", type=str, help="The command to execute `cabal` with. This is used to build & run the interpreter.")
    parser.add_argument("-f", "--full-eval", action="store_true", help="If given, does a full AB test. This means that `create`, `terminate` and `obfuscate` are compared as well.")
    parser.add_argument("-a", "--all-diffs", action="store_true", help="If given, shows all diffs instead of hiding the ones who are the same.")
    parser.add_argument("-n", "--n-runs", type=int, default=10, help="The number of times to run a benchmark for to arrive at an average time.")
    parser.add_argument("-P", "--strict-perf", action="store_true", help="If given, does not run correctness tests for performance files.")
    parser.add_argument("-o", "--output-perf", type=str, help="If given, outputs a CSV file with the performance statistics to the given path.")
    parser.add_argument("-e", "--eflint-core", type=str, help="Do not use the builtin eFLINT core specification, but instead load it from a file. Use '-' to load from stdin instead.")
    parser.add_argument("-C", "--clingo-only", action="store_true", help="If given, does not run the eFLINT-side when doing performance tests. Will still run it during correctness tests to AB test the Clingo side.")
    parser.add_argument("--correctness", action="store_true", help="Alias for only running 'same' and 'diff'-tests.")
    parser.add_argument("--performance", action="store_true", help="Alias for only running 'perf'-tests. Implies '--strict-perf'.")
    # parser.add_argument("-i", "--incremental-model", action="store_true", help="If given, Clingo states are computed by incrementally passing the scenario to the compiler. This allows one to see states for which Clingo still computes, even if a later state destroyes it.")
    parser.add_argument("--debug", action="store_true", help="If given, shows additional debug prints. Also shows additional symbols in the diffs which are not compared for equality as they are considered auxillary.")
    parser.add_argument("--trace", action="store_true", help="If given, shows all debug prints (implies '--debug').")

    args = parser.parse_args()
    DEBUG = args.debug or args.trace
    TRACE = args.trace
    if args.correctness:
        args.types = ["same", "diff"]
    if args.performance:
        args.types = ["perf"]
        args.strict_perf = True

    exit(main(args.test, args.types, args.spec_suffix, args.same_suffix, args.diff_suffix, args.perf_suffix, args.eflint_core, shlex.split(args.cabal_exec), args.full_eval, args.all_diffs, args.n_runs, args.strict_perf, args.output_perf, args.clingo_only))
