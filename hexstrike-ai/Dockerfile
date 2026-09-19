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
      python3 python3-pip python3-venv curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

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
        seclists ; \
    fi \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/hexstrike
COPY requirements.txt /opt/hexstrike/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY hexstrike_server.py /opt/hexstrike/hexstrike_server.py

EXPOSE 8888
HEALTHCHECK --interval=10s --timeout=5s --retries=18 --start-period=30s \
  CMD curl -fsS http://localhost:8888/health || exit 1
CMD ["python3", "hexstrike_server.py"]
