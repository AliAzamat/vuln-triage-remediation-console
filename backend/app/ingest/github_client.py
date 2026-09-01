"""Fetch a repo's tree at an EXACT commit. A scan is only reproducible against a
pinned sha — 'scan main' is meaningless once main moves."""
from __future__ import annotations

import io
import os
import zipfile
import httpx

GITHUB_API = "https://api.github.com"


def resolve_commit(owner: str, name: str, ref: str = "HEAD") -> str:
    """Resolve a branch/tag/HEAD to a concrete commit sha, so the scan is pinned."""
    token = os.environ["GITHUB_TOKEN"]
    r = httpx.get(
        f"{GITHUB_API}/repos/{owner}/{name}/commits/{ref}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["sha"]


def download_tree(owner: str, name: str, sha: str, dest: str) -> str:
    """Download the repo tarball at `sha` and unzip it to `dest`. Returns the root
    path the scanner runs against. Pinned to sha = byte-identical every re-run."""
    token = os.environ["GITHUB_TOKEN"]
    r = httpx.get(
        f"{GITHUB_API}/repos/{owner}/{name}/zipball/{sha}",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True, timeout=120,
    )
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        zf.extractall(dest)
        root = zf.namelist()[0].split("/")[0]  # GitHub wraps in a top dir
    return os.path.join(dest, root)
