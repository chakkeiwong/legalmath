"""Retain the failed 339 fixture as evidence, outside current test collection.

The active replacement is test_reference_requirement_raw_copies.py: it constructs
TextUnit source data and rejects the old JSON-string hash. The historical file
remains byte-for-byte frozen by reviews/original-acceptance-copy-339/freeze.json.
The exact failed084 oracle is also retained; its complete active replacement is test_reference_address_projection.py.
"""
from pathlib import Path
import hashlib

def pytest_ignore_collect(collection_path,config):
    historical=Path(__file__).with_name('test_reference_requirement_copies.py')
    if collection_path==historical:
        expected='6ab98f2199d36d6208b06d237e16c241168e666c90faec00fd74ecbd16d11ed0'
        if hashlib.sha256(historical.read_bytes()).hexdigest()==expected:
            return True
    obsolete=Path(__file__).with_name("test_reference_addresses.py")
    if collection_path==obsolete and hashlib.sha256(obsolete.read_bytes()).hexdigest()=='01bafe5ded5f248da19c9119349a58876ca001200431abf489163bef74a43ed8':
        return True
    return None
