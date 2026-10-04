#!/bin/sh
set -e

# msfrpcd is Metasploit's RPC daemon — started here so hexstrike_server.py
# can drive persistent Metasploit sessions (post-exploit session tooling,
# msfrpc_client.py) across separate HTTP calls, instead of one msfconsole
# process per call (which can't hand a live session off to a later,
# separate request — see the exploit-shell-session-fix plan's Phase B2).
#
# Bound to 127.0.0.1 only, and this container never publishes/exposes
# port 55553 (docker-compose.yml) — nothing outside this one container's
# own process group can ever reach it. The password is generated fresh
# every container start and lives only in this container's own process
# environment — never written to disk, never logged.
export MSF_RPC_PASSWORD="$(python3.13 -c 'import secrets; print(secrets.token_urlsafe(32))')"
msfrpcd -P "$MSF_RPC_PASSWORD" -U msf -a 127.0.0.1 -p 55553 -n -f &

exec python3.13 hexstrike_server.py
