"""Unit tests for hexstrike_server.parse_msf_sessions_table.

Standalone by design: hexstrike-ai has no existing test suite (vendored
fork), and this parser is a pure function with no Flask/network
dependencies, so it's tested in isolation rather than standing up a full
test framework for the whole server module.

Run with: python -m pytest test_msf_session_parser.py -v
"""

import hexstrike_server as hs


SHELL_SESSION_TABLE = r"""
Active sessions
===============

  Id  Name  Type              Information  Connection
  --  ----  ----              -----------  ----------
  1         shell x86/linux                10.0.0.5:4444 -> 10.0.0.10:53211 (10.0.0.10)

"""

METERPRETER_SESSION_TABLE = r"""
Active sessions
===============

  Id  Name  Type                     Information                          Connection
  --  ----  ----                     -----------                          ----------
  2         meterpreter x64/windows  NT AUTHORITY\SYSTEM @ DESKTOP-ABC123  10.0.0.5:4444 -> 10.0.0.10:53212 (10.0.0.10)

"""

MULTI_SESSION_TABLE = r"""
Active sessions
===============

  Id  Name  Type              Information  Connection
  --  ----  ----              -----------  ----------
  1         shell x86/linux                10.0.0.5:4444 -> 10.0.0.10:53211 (10.0.0.10)
  2         shell x64/windows              10.0.0.5:4444 -> 10.0.0.11:53212 (10.0.0.11)

"""

NO_SESSIONS_OUTPUT = r"""
No active sessions.

"""

# A table-shaped line appearing in the exploit module's own progress log,
# BEFORE any real "Active sessions" header — must never be mistaken for a
# session row just because it happens to have similar column spacing.
LOG_NOISE_BEFORE_HEADER = r"""
[*] Started reverse TCP handler on 10.0.0.5:4444
  1         open  tcp   scanning                       10.0.0.10:21 (10.0.0.10)
[*] 10.0.0.10:21 - Command shell session 1 opened (10.0.0.5:4444 -> 10.0.0.10:53211)

Active sessions
===============

  Id  Name  Type              Information  Connection
  --  ----  ----              -----------  ----------
  1         shell x86/linux                10.0.0.5:4444 -> 10.0.0.10:53211 (10.0.0.10)

"""


def test_parses_a_plain_shell_session():
    sessions = hs.parse_msf_sessions_table(SHELL_SESSION_TABLE)
    assert sessions == [
        {
            "id": "1",
            "type": "shell",
            "raw_type": "shell x86/linux",
            "info": "",
            "connection": "10.0.0.5:4444 -> 10.0.0.10:53211 (10.0.0.10)",
        }
    ]


def test_parses_a_meterpreter_session_with_info():
    sessions = hs.parse_msf_sessions_table(METERPRETER_SESSION_TABLE)
    assert len(sessions) == 1
    assert sessions[0]["id"] == "2"
    assert sessions[0]["type"] == "meterpreter"
    assert sessions[0]["info"] == r"NT AUTHORITY\SYSTEM @ DESKTOP-ABC123"


def test_parses_multiple_session_rows():
    sessions = hs.parse_msf_sessions_table(MULTI_SESSION_TABLE)
    assert [s["id"] for s in sessions] == ["1", "2"]


def test_empty_output_is_no_sessions_not_a_parse_failure():
    assert hs.parse_msf_sessions_table("") == []
    assert hs.parse_msf_sessions_table(NO_SESSIONS_OUTPUT) == []


def test_header_and_separator_rows_are_not_mistaken_for_sessions():
    # Regression guard: "Id  Name  Type ..." and "--  ----  ----" must never
    # be parsed as a session row just because they're table-shaped.
    sessions = hs.parse_msf_sessions_table(SHELL_SESSION_TABLE)
    assert all(s["id"].isdigit() for s in sessions)


def test_table_shaped_log_lines_before_the_header_are_ignored():
    # Regression guard for a real false-positive risk: the captured stdout
    # is the WHOLE msfconsole run, not just the sessions -l output — a
    # coincidentally table-shaped exploit-log line before the real "Active
    # sessions" header must not be parsed as a session row.
    sessions = hs.parse_msf_sessions_table(LOG_NOISE_BEFORE_HEADER)
    assert len(sessions) == 1
    assert sessions[0]["id"] == "1"
    assert sessions[0]["connection"] == "10.0.0.5:4444 -> 10.0.0.10:53211 (10.0.0.10)"
