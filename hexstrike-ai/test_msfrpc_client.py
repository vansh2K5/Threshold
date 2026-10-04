"""Unit tests for msfrpc_client's byte-decoding fix.

Standalone by design, same rationale as test_msf_session_parser.py:
hexstrike-ai has no existing test suite (vendored fork).

Run with: python -m pytest test_msfrpc_client.py -v
"""

import msfrpc_client


def test_decode_bytes_converts_dict_keys_and_values():
    # Live-confirmed bug: msfrpcd (Ruby's older msgpack encoding) sends
    # string data in a way msgpack-python's raw=False doesn't reliably
    # auto-decode — unpackb was still returning bytes keys/values
    # (b'result', b'success') instead of str.
    raw = {b"result": b"success", b"token": b"abc123"}
    assert msfrpc_client._decode_bytes(raw) == {"result": "success", "token": "abc123"}


def test_decode_bytes_handles_nested_structures():
    raw = {
        b"sessions": {
            b"1": {b"type": b"shell", b"target_host": b"10.0.0.5"},
        }
    }
    decoded = msfrpc_client._decode_bytes(raw)
    assert decoded == {"sessions": {"1": {"type": "shell", "target_host": "10.0.0.5"}}}


def test_decode_bytes_passes_through_non_bytes_values():
    raw = {"already_str": "value", "a_bool": True, "a_num": 42, "a_list": [1, 2, b"x"]}
    assert msfrpc_client._decode_bytes(raw) == {
        "already_str": "value",
        "a_bool": True,
        "a_num": 42,
        "a_list": [1, 2, "x"],
    }
