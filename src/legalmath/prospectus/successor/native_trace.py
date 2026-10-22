"""Finite strace path-event accounting, with no host-currentness inference.

Supports complete -f -yy file/process records from the retained OCR trace.
Unknown grammar and interrupted calls stay unresolved rather than disappearing.
No path is stat-ed, resolved or opened by this parser.
"""
import ast
from collections import Counter
import re

from .contracts import digest

VERSION = "native-trace-accounting.v1"
_PREFIX = re.compile(r"^(?:\[pid\s+(\d+)\]|(\d+))\s+(.*)$")
_CALL = re.compile(r"^(\w+)\((.*)\)\s+=\s+(.*)$")
_RESULT = re.compile(r"^(-?\d+)(?:<[^<>]*>)?(?:\s+([A-Z][A-Z0-9_]+)(?:\s+\(.*\))?)?$")
_FD = re.compile(r"^(?:AT_FDCWD|\d+)<(/[^<>]*)>$")
_STRING = re.compile(r'"(?:[^"\\]|\\(?:[\\"abfnrtv]|[0-7]{1,3}|x[0-9a-fA-F]{2}))*"')
_DIRECT = {"stat": "metadata", "lstat": "metadata", "access": "access_check",
           "readlink": "link_target", "execve": "execute"}
_AT = {"newfstatat": "metadata", "openat": "open"}


def _arguments(value):
    result, start, stack, quoted, escape = [], 0, [], False, False
    pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
    for i, char in enumerate(value):
        if quoted:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in pairs:
            stack.append(pairs[char])
        elif char in pairs.values():
            if not stack or stack.pop() != char:
                raise ValueError("Unbalanced argument delimiters")
        elif char == "," and not stack:
            result.append(value[start:i].strip())
            start = i + 1
    if quoted or stack:
        raise ValueError("Incomplete quoted argument or structure")
    result.append(value[start:].strip())
    return result


def _path(token):
    if not _STRING.fullmatch(token):
        raise ValueError("Path argument is truncated or uses unsupported quoting")
    value = ast.literal_eval(token)
    if "\x00" in value:
        raise ValueError("NUL in decoded path")
    return value


def _base(token):
    match = _FD.fullmatch(token)
    if not match or match[1].endswith(" (deleted)") or "\\" in match[1]:
        raise ValueError("No unambiguous decoded absolute descriptor base")
    return match[1]


def event(raw, number):
    item = {"line": number, "raw": raw, "status": "UNRESOLVED", "path": None}
    prefix = _PREFIX.fullmatch(raw)
    if not prefix:
        return {**item, "reason": "Unsupported trace prefix"}
    item["pid"] = int(prefix[1] or prefix[2])
    body = prefix[3]
    if re.fullmatch(r"\+\+\+ exited with \d+ \+\+\+", body):
        return {**item, "status": "PROCESS_EVENT", "reason": "Process exit marker"}
    if "<unfinished ...>" in body or body.startswith("<..."):
        return {**item, "reason": "Interrupted call requires explicit reconstruction"}
    call = _CALL.fullmatch(body)
    if not call:
        return {**item, "reason": "Unsupported call or event syntax"}
    name, argument_text, result = call.groups()
    item["syscall"] = name
    if name == "exit_group" and re.fullmatch(r"\d+", argument_text) and result == "?":
        return {**item, "status": "PROCESS_EVENT", "reason": "Process exit call"}
    if name not in _DIRECT and name not in _AT:
        return {**item, "reason": "Unsupported syscall"}
    outcome = _RESULT.fullmatch(result)
    if not outcome:
        return {**item, "reason": "Unsupported return value"}
    rc, errno = int(outcome[1]), outcome[2]
    item.update(return_value=rc, errno=errno, operation=(_DIRECT | _AT)[name])
    if (rc == -1 and not errno) or rc < -1 or (rc >= 0 and errno):
        return {**item, "reason": "Inconsistent return/error syntax"}
    try:
        args = _arguments(argument_text)
        counts = {"stat": 2, "lstat": 2, "access": 2, "readlink": 3,
                  "execve": 3, "newfstatat": 4}
        if len(args) != counts.get(name, len(args)) or (name == "openat" and len(args) not in (3, 4)):
            raise ValueError("Unexpected argument count")
        quoted = _path(args[1] if name in _AT else args[0])
        base = None
        if name in _AT:
            if not quoted:
                if name != "newfstatat" or "AT_EMPTY_PATH" not in args[3].split("|"):
                    raise ValueError("Empty path without supported AT_EMPTY_PATH semantics")
                base = _base(args[0])
                path, role = base, "descriptor_object"
            elif not quoted.startswith("/"):
                base = _base(args[0])
                path, role = base.rstrip("/") + "/" + quoted, "relative_to_decoded_base"
            else:
                path, role = quoted, "absolute_path_argument"
        elif quoted.startswith("/"):
            path, role = quoted, "absolute_path_argument"
        else:
            raise ValueError("Relative path lacks a supported decoded base")
        kind = None
        if name in {"stat", "lstat", "newfstatat"}:
            metadata = args[2] if name == "newfstatat" else args[1]
            match = re.search(r"\bst_mode=(S_IF[A-Z]+)\b", metadata)
            kind = match[1] if match and rc == 0 else None
        item.update(path=path, path_argument=quoted, path_role=role, descriptor_base=base,
                    observed_type=kind, dynamic_namespace=path.startswith(("/proc/", "/dev/")))
        if rc >= 0:
            item["status"] = "PATH_OPERATION_SUCCEEDED"
        elif errno == "ENOENT":
            item["status"] = "PATH_OPERATION_ENOENT"
        else:
            item["status"] = "PATH_OPERATION_FAILED"
        if name == "openat":
            item["open_flags"] = args[2]
        if name == "readlink" and rc >= 0:
            # The return buffer is a separate observation, never another input
            # path. Truncated/unrecognized buffers are explicit.
            try:
                item["reported_link_target"] = _path(args[1])
            except ValueError:
                item["reported_link_target"] = None
                item["link_target_issue"] = "Truncated or unsupported return buffer"
    except (ValueError, SyntaxError) as exc:
        item.update(status="UNRESOLVED", path=None, reason=str(exc))
    return item


def account(raw, expected_sha256=None):
    if not isinstance(raw, bytes):
        raise ValueError("Original trace bytes required")
    actual = digest(raw)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ValueError("Trace bytes changed")
    text = raw.decode("utf-8")
    # split on LF only: escaped or literal control characters must not silently
    # create additional records. Original bytes are bound separately.
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    events = [event(line, i) for i, line in enumerate(lines, 1)]
    counts = dict(sorted(Counter(e["status"] for e in events).items()))
    return {"version": VERSION, "trace_sha256": actual, "line_count": len(lines),
            "events": events, "counts": counts,
            "complete_native_closure": False, "native_reuse_allowed": False,
            "limits": ["Finite retained trace accounting; unseen operations and inputs remain unknown",
                       "Successful metadata/open operations do not establish file-content reads",
                       "ENOENT may concern a path component; no present-day absence is inferred",
                       "Decoded descriptor paths are observations, not immutable file identities",
                       "No current filesystem, confinement, race-freedom or portability validation"]}
