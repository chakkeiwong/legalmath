"""Immutable content storage; a database can reference only durable bytes."""
import os
from pathlib import Path
import re
import tempfile

from ..canonical import raw_digest
from ..errors import LegalMathError


class BlobStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, digest):
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise LegalMathError("E_SCHEMA")
        return self.root / digest[:2] / digest[2:]

    def put(self, data):
        ident = raw_digest(data)
        path = self.path(ident)
        path.parent.mkdir(parents=True, exist_ok=True)
        rootfd = os.open(self.root, os.O_DIRECTORY)
        try:
            os.fsync(rootfd)
        finally:
            os.close(rootfd)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            try:
                os.link(tmp, path)  # publish without ever replacing existing bytes
            except FileExistsError:
                if self.get(ident) != data:
                    raise LegalMathError("E_INTEGRITY")
            dirfd = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
        finally:
            os.unlink(tmp)
        return ident

    def get(self, ident):
        try:
            data = self.path(ident).read_bytes()
        except FileNotFoundError as exc:
            raise LegalMathError("E_INTEGRITY") from exc
        if raw_digest(data) != ident:
            raise LegalMathError("E_HASH_MISMATCH")
        return data
