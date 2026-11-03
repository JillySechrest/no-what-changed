"""nwc <pr-url> [--apply]: dry run by default."""

import argparse
import os
import sys

from .diff_filter import filter_diff
from .github import GitHub, parse_pr_url
from .render import add_entry, already_recorded, format_entry
from .summarize import Entry, summarize

BOT_LABEL = "nwc-changelog"
CHANGELOG = "CHANGELOG.md"


def is_bot_pr(pr: dict) -> bool:
    user = pr.get("user", {}) or {}
    head = (pr.get("head", {}) or {}).get("ref", "")
    return user.get("type") == "Bot" or head.startswith("nwc/changelog-")


def build_entry(gh: GitHub, owner: str, repo: str, number: int, client, model: str):
    pr = gh.get_pr(owner, repo, number)
    diff, truncated = filter_diff(gh.get_diff(owner, repo, number))
    if not diff.strip():
        entry = Entry("Changed", pr["title"] + " (no reviewable code changes)")
    else:
        entry = summarize(pr["title"], pr.get("body") or "", diff, truncated, client, model)
    entry.pr_number = number
    return pr, entry


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="nwc")
    p.add_argument("pr_url")
    p.add_argument("--apply", action="store_true", help="open a PR against CHANGELOG.md")
    p.add_argument("--model", default=os.environ.get("NWC_MODEL", "gpt-4o-mini"))
    args = p.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN")
    if not token or not os.environ.get("OPENAI_API_KEY"):
        print("GITHUB_TOKEN and OPENAI_API_KEY are required.", file=sys.stderr)
        return 2

    from openai import OpenAI

    owner, repo, number = parse_pr_url(args.pr_url)
    gh = GitHub(token)
    pr = gh.get_pr(owner, repo, number)
    if is_bot_pr(pr):
        print("Skipping: this is a changelog bot PR.")
        return 0

    pr, entry = build_entry(gh, owner, repo, number, OpenAI(), args.model)
    print(f"### {entry.category}\n{format_entry(entry)}")
    if not args.apply:
        print("\n(dry run; pass --apply to open a PR)")
        return 0

    base = pr["base"]["ref"]
    current, sha = gh.get_file(owner, repo, CHANGELOG, base)
    if already_recorded(current, number):
        print(f"PR #{number} is already in {CHANGELOG}; nothing to do.")
        return 0
    branch = f"nwc/changelog-{number}"
    gh.create_branch(owner, repo, branch, gh.branch_sha(owner, repo, base))
    gh.put_file(
        owner, repo, CHANGELOG, branch, add_entry(current, entry),
        f"docs: changelog entry for #{number}", sha,
    )
    url = gh.open_pr(
        owner, repo, branch, base, f"docs: changelog entry for #{number}",
        f"Generated from the diff of #{number}. Edit freely before merging.",
    )
    print(f"Opened {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
