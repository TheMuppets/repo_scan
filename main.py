#!/usr/bin/env python3
from collections import defaultdict
from subprocess import PIPE, run
import fnmatch
import json
import os
import sys
import urllib.request


DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


def check_lic(data: bytes) -> bool:
    return any(x in data for x in [b"com.sensetime", b"SenseTime"])


def check_megvii(data: bytes) -> bool:
    return any(x in data for x in [b"megface", b"megvii", b"MEGVII"])


def check_file(path: str) -> bool:
    _, file_name = os.path.split(path)
    ret = False

    for x, fn in {
        "*.lic": check_lic,
        "libmegface*": check_megvii,
        "libmegjpeg*": check_megvii,
        "libmegskeleton*": check_megvii,
        "libmegvii*": check_megvii,
        "libmgbeauty*": check_megvii,
        "libmgface*": check_megvii,
    }.items():
        if fnmatch.fnmatch(file_name.lower(), x):
            ret |= fn(open(path, "rb").read())

    return ret


def check_commit_range(repo_path: str, commits: list[str]) -> dict[list[str]]:
    bad_files = defaultdict(list)

    for commit in commits:
        run(["git", "reset", "--hard", commit], stdout=PIPE, stderr=PIPE, cwd=repo_path)

        for root, dirs, files in os.walk(f"{repo_path}/proprietary"):
            for f in files:
                file_path = os.path.join(root, f)
                file_path_rel = file_path[len(repo_path) + 1 :]

                if any(file_path_rel in x for x in bad_files.values()):
                    continue

                if check_file(file_path):
                    bad_files[commit].append(file_path_rel)

    return bad_files


def post_message(content: str) -> None:
    urllib.request.urlopen(
        urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            json.dumps(
                {
                    "username": "GitHub",
                    "avatar_url": "https://avatars.githubusercontent.com/u/9919?s=200&v=4",
                    "content": content,
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "TheMuppets/repo_scan",
            },
            method="POST",
        )
    )


def main() -> None:
    _, repo, branch, commits = sys.argv

    run(["git", "clone", "-b", branch, repo, "src"]).check_returncode()

    for commit, file_paths in check_commit_range("src", commits.split(",")).items():
        for file_path in file_paths:
            post_message(f"Sketchy file found: <{repo}/blob/{commit}/{file_path}>")


if __name__ == "__main__":
    main()
