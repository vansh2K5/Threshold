# syntax=docker/dockerfile:1
# HexStrike tool backend (fat): the Flask REST server + pentest CLI tools.
# TOOLSET=curated installs a focused subset (covers the web-facing tools needed
# for the bundled Juice Shop target). TOOLSET=full installs the Kali
# metapackages (multi-GB, slow first build).
#
# NOTE: this tool list is a first cut and is UNVERIFIED against a live build
# (Docker was not available on the authoring machine). Some tools referenced by
# the mcp_client role allowlist are not apt-packaged on Kali (they need go/pip
# installs) and can be added here as needed, or use TOOLSET=full.
FROM kalilinux/kali-rolling

ARG TOOLSET=curated
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    API_PORT=8888

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3.13 python3.13-venv python3.13-dev curl ca-certificates \
      build-essential libffi-dev libssl-dev \
 && rm -rf /var/lib/apt/lists/*
# Explicit python3.13, not the bare "python3" meta-package: kali-rolling's
# python3 now resolves to 3.14, for which several deps in requirements.txt
# (angr and friends, cffi via cryptography) have NO prebuilt wheel yet —
# pip either falls back to a slow/failing source build (cffi: "No working
# compiler found" even with a compiler, since some transitive pins predate
# 3.14 entirely) or backtracks through dozens of releases hunting for one
# that has a cp314 wheel and never finds it (angr: observed hanging past
# 5 minutes cycling through 9.2.209..213). 3.13 has prebuilt wheels for both
# — verified directly against PyPI before this line was added.
#
# python3.13-venv (not python3-pip): Kali doesn't ship a per-version pip
# package, and stdlib ensurepip has no bundled wheel on Debian/Kali by
# policy. get-pip.py below is pip's own official bootstrap, run against
# python3.13 specifically so pip installs match the interpreter used to run
# hexstrike_server.py — anything else risks a python3.14-targeted pip
# silently installing packages the app's own interpreter can't import.
RUN curl -fsS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py \
 && python3.13 /tmp/get-pip.py --break-system-packages \
 && rm /tmp/get-pip.py

RUN apt-get update && \
    if [ "$TOOLSET" = "full" ]; then \
      apt-get install -y --no-install-recommends kali-linux-headless ; \
    else \
      apt-get install -y --no-install-recommends \
        nmap masscan dnsutils whatweb nikto wafw00f \
        gobuster ffuf feroxbuster dirb wfuzz \
        sqlmap hydra john hashcat \
        nuclei amass subfinder \
        smbmap enum4linux nbtscan \
        libimage-exiftool-perl binwalk foremost steghide radare2 gdb \
        seclists metasploit-framework ; \
    fi \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/hexstrike
COPY requirements.txt /opt/hexstrike/requirements.txt
# --ignore-installed: the apt tool install above pulls in some Python libs as
# transitive dependencies (observed: python3-pyparsing, via one of the CLI
# tools) into the same dist-packages path python3.13 also sees. Those apt
# packages have no pip RECORD file, so pip's normal "upgrade in place" logic
# fails with "Cannot uninstall pyparsing: ... no RECORD file was found" —
# verified against a live build. --ignore-installed tells pip to install
# fresh (shadowing the apt copy) instead of trying to manage it.
RUN python3.13 -m pip install --no-cache-dir --break-system-packages --ignore-installed \
      -r requirements.txt
COPY hexstrike_server.py /opt/hexstrike/hexstrike_server.py
COPY templates/ /opt/hexstrike/templates/

EXPOSE 8888
HEALTHCHECK --interval=10s --timeout=5s --retries=18 --start-period=30s \
  CMD curl -fsS http://localhost:8888/health || exit 1
CMD ["python3.13", "hexstrike_server.py"]
