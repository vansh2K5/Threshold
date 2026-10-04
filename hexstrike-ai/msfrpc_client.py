"""Minimal client for Metasploit's RPC daemon (msfrpcd).

Phase B2 of exploit-shell-session-fix.md: metasploit_run's resource-script
approach (a fresh msfconsole process per call) can't hand a live session off
to a LATER, separate HTTP call — the session lives inside that one
short-lived process and dies with it. msfrpcd is one persistent Metasploit
framework instance that many calls can attach to, so a session opened by one
request is still there for a different request minutes later.

Talks msgpack-RPC directly (Metasploit's actual wire protocol) rather than
pulling in a full RPC framework — only 4 methods are needed here
(auth.login, session.list, session.shell_write, session.shell_read), each a
few lines against a single HTTP endpoint.

msfrpcd is started by docker-entrypoint.sh bound to 127.0.0.1 only, inside
this same container, with a password generated fresh per container start —
nothing outside this one container process group can ever reach it.
"""

from __future__ import annotations

import os
import time
from typing import Any

import msgpack
import requests

_RPC_URL = "https://127.0.0.1:55553/api/"
_HEADERS = {"Content-Type": "binary/message-pack"}


class MsfRpcError(Exception):
    """Raised on an RPC transport failure or an explicit error result from
    msfrpcd itself — callers must not guess a plausible result past this."""


def _decode_bytes(value: Any) -> Any:
    """msfrpcd (Ruby's older msgpack encoding) sends string data using
    msgpack's ambiguous "raw" family, which msgpack-python's raw=False
    doesn't reliably auto-decode to str the way it does for its OWN
    use_bin_type=True-packed data — confirmed live: unpackb was still
    returning bytes keys/values (b'result', b'success', ...). Decoded
    recursively here instead of trusting the unpacker's guess."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value
    if isinstance(value, dict):
        return {_decode_bytes(k): _decode_bytes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_bytes(v) for v in value]
    return value


def _call(method: str, *params: Any) -> Any:
    body = msgpack.packb([method, *params], use_bin_type=True)
    try:
        # msfrpcd's SSL cert is self-signed and this traffic never leaves
        # 127.0.0.1 inside this one container — verify=False is scoped to
        # exactly that, not a general "skip cert checks" pattern.
        resp = requests.post(_RPC_URL, data=body, headers=_HEADERS, verify=False, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise MsfRpcError(f"msfrpcd request failed for {method}: {exc}") from exc
    result = _decode_bytes(msgpack.unpackb(resp.content, raw=False))
    if isinstance(result, dict) and result.get("error"):
        raise MsfRpcError(
            f"msfrpcd returned an error for {method}: "
            f"{result.get('error_message') or result.get('error_class') or result}"
        )
    return result


_token: str | None = None


def _auth_token() -> str:
    """Logs in once per process and caches the token — auth.login itself is
    the one call that must never be gated behind an existing token."""
    global _token
    if _token is not None:
        return _token
    password = os.environ.get("MSF_RPC_PASSWORD")
    if not password:
        raise MsfRpcError("MSF_RPC_PASSWORD is not set — msfrpcd was not started correctly")
    result = _call("auth.login", "msf", password)
    if result.get("result") != "success":
        raise MsfRpcError(f"msfrpcd auth.login failed: {result}")
    _token = result["token"]
    return _token


def list_sessions() -> dict[str, dict]:
    """Returns msfrpcd's live session table: {session_id: {type, session_host,
    session_port, target_host, tunnel_peer, via_exploit, info, ...}}."""
    return _call("session.list", _auth_token())


def run_command_in_session(
    session_id: str, command: str, read_seconds: float = 5.0, poll_interval: float = 0.5
) -> str:
    """Writes one command into a live shell session and collects whatever it
    prints back over read_seconds. Not a full interactive TTY — one command
    per call, matching this project's one-shot tool-loop shape elsewhere
    (agents/_common.py), and matching the human-approval gate: one proposed
    command, one approval, one execution.
    """
    token = _auth_token()
    _call("session.shell_write", token, session_id, command + "\n")

    output_parts: list[str] = []
    deadline = time.monotonic() + read_seconds
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        read_result = _call("session.shell_read", token, session_id)
        data = read_result.get("data") or ""
        if data:
            output_parts.append(data)
    return "".join(output_parts)


def kill_session(session_id: str) -> None:
    _call("session.stop", _auth_token(), session_id)
