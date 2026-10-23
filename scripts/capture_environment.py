"""Capture non-secret reproducibility artifacts for an experiment batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def worktree_fingerprint() -> tuple[str, list[str]]:
    digest = hashlib.sha256()
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--", ".", ":!results", ":!data"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    ).stdout
    digest.update(diff)
    untracked = command_output(["git", "ls-files", "--others", "--exclude-standard"])
    included = []
    if untracked and not untracked.startswith("unavailable:"):
        for relative in untracked.splitlines():
            path = Path(relative)
            lower_parts = [part.lower() for part in path.parts]
            if any(part in {"results", "data", "node_modules", ".venv", "__pycache__"} for part in lower_parts):
                continue
            if path.name.lower() == ".env" or path.name.lower().startswith(".env."):
                continue
            if any(re.search(r"secret|credential|api[_-]?key|access[_-]?token", part) for part in lower_parts):
                continue
            absolute = (ROOT / path).resolve()
            if ROOT not in absolute.parents or not absolute.is_file():
                continue
            try:
                content = absolute.read_bytes()
            except OSError:
                continue
            digest.update(relative.encode("utf-8", errors="replace"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(content).digest())
            included.append(relative.replace("\\", "/"))
    return digest.hexdigest(), sorted(included)


def command_output(argv: list[str]) -> str | None:
    try:
        return subprocess.check_output(argv, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable: {type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--config-notes", default="")
    args = parser.parse_args()
    batch = args.results_dir / "batches" / args.batch_id
    artifacts = batch / "environment"
    artifacts.mkdir(parents=True, exist_ok=True)
    for source, dest in (
        (ROOT / "docker-compose.yml", artifacts / "docker-compose.yml"),
        (ROOT / "pentest-agents" / "requirements.txt", artifacts / "requirements.txt"),
    ):
        if source.exists():
            shutil.copy2(source, dest)
    commit = command_output(["git", "rev-parse", "HEAD"])
    diff_hash, untracked_source_files = worktree_fingerprint()
    status = command_output(["git", "status", "--porcelain", "--untracked-files=no"])
    docker_images = command_output(["docker", "images", "--digests"])
    metadata = {
        "batch_id": args.batch_id,
        "captured_at": datetime.now(UTC).isoformat(),
        "host_os": platform.platform(),
        "host_uname": " ".join(platform.uname()),
        "docker_version": command_output(["docker", "--version"]),
        "docker_images_digests": docker_images,
        "python_version": sys.version,
        "repo_commit_hash_at_capture": commit,
        "repo_commit_hash_at_run": None,
        "tracked_worktree_diff_sha256_at_capture": diff_hash,
        "tracked_worktree_status_at_capture": status,
        "untracked_source_files_in_fingerprint": untracked_source_files,
        "provider_api_version_strings": "recorded per provider response when returned; otherwise null",
        "manual_config_changes": args.config_notes,
        "artifacts": [
            "environment/docker-compose.yml",
            "environment/requirements.txt",
        ],
        "secrets_captured": False,
    }
    batch.mkdir(parents=True, exist_ok=True)
    metadata_path = batch / "batch_metadata.json"
    if metadata_path.exists():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        existing.update(metadata)
        metadata = existing
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Captured reproducibility metadata under {batch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
