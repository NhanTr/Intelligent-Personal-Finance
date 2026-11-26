"""Check PR routing locally or from a GitHub pull_request event (stdlib only)."""

import argparse
import json
import os
from pathlib import Path
import re
import sys


WORK_BRANCH = re.compile(
    r"(?:feat|fix|docs|chore|refactor|test)/"
    r"(?P<member>khoa|nhan|duy)-(?P<task>[knd][1-9][0-9]*)-"
    r"[a-z0-9]+(?:-[a-z0-9]+)*"
)
# The initial repository setup precedes the regular work-package branches.
SETUP_BRANCH = re.compile(r"chore/khoa-repo-workflow-[0-9]{8}-[0-9]{6}")
TASK_PREFIX = {"khoa": "k", "nhan": "n", "duy": "d"}


def validate_pr(
    *, base: str, head: str, base_repository: str,
    head_repository: str, repository: str,
) -> None:
    if not repository or not base_repository or not head_repository:
        raise ValueError("Repository metadata is required; missing or deleted source is rejected.")
    if any(name.casefold() != repository.casefold()
           for name in (base_repository, head_repository)):
        raise ValueError("Both branches must belong to this repository; fork PRs are rejected.")
    if base == "main":
        if head != "develop":
            raise ValueError("Only develop from this repository may open a PR into main.")
        return
    if base != "develop":
        raise ValueError("PR target must be develop (work) or main (release).")
    if SETUP_BRANCH.fullmatch(head):
        return
    match = WORK_BRANCH.fullmatch(head)
    if not match or match["task"][0] != TASK_PREFIX[match["member"]]:
        raise ValueError(
            "Use <type>/<member>-<task>-<description>, for example "
            "feat/khoa-k2-import-csv; task prefix must match the member."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-path", type=Path, default=os.getenv("GITHUB_EVENT_PATH"))
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--base-repository")
    parser.add_argument("--head-repository")
    args = parser.parse_args(argv)
    try:
        if args.event_path:
            event = json.loads(args.event_path.read_text(encoding="utf-8"))
            pr = event["pull_request"]
            base, head = pr["base"], pr["head"]
            values = {
                "base": base["ref"], "head": head["ref"],
                "base_repository": (base.get("repo") or {}).get("full_name", ""),
                "head_repository": (head.get("repo") or {}).get("full_name", ""),
                "repository": args.repository,
            }
        else:
            values = {
                "base": args.base, "head": args.head,
                "base_repository": args.base_repository,
                "head_repository": args.head_repository,
                "repository": args.repository,
            }
            if not all(values.values()):
                raise ValueError("Supply --event-path or all five branch/repository arguments.")
        validate_pr(**values)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"branch-policy: FAIL: {error}", file=sys.stderr)
        return 1
    print(f"branch-policy: PASS: {values['head']} -> {values['base']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
