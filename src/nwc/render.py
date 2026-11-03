"""Insert an entry into CHANGELOG.md under ## [Unreleased]."""

from .summarize import CATEGORIES, Entry

HEADER = (
    "# Changelog\n\nAll notable changes to this project are documented here.\n\n"
    "## [Unreleased]\n"
)


def format_entry(entry: Entry) -> str:
    ref = f" (#{entry.pr_number})" if entry.pr_number else ""
    line = f"- {entry.summary}{ref}"
    if entry.scope_creep_note:
        line += f"\n  - Also changed: {entry.scope_creep_note}"
    return line


def already_recorded(changelog: str, pr_number: int | None) -> bool:
    return pr_number is not None and f"(#{pr_number})" in changelog


def add_entry(changelog: str, entry: Entry) -> str:
    """Return updated changelog text. Idempotent per PR number."""
    if not changelog.strip():
        changelog = HEADER
    if already_recorded(changelog, entry.pr_number):
        return changelog
    if "## [Unreleased]" not in changelog:
        head, sep, rest = changelog.partition("\n## ")
        block = "## [Unreleased]\n\n"
        changelog = head.rstrip() + "\n\n" + block + (sep + rest if sep else "")

    start = changelog.index("## [Unreleased]")
    nxt = changelog.find("\n## ", start + 1)
    end = len(changelog) if nxt == -1 else nxt + 1
    section = changelog[start:end].rstrip("\n")
    after = changelog[end:]

    heading = f"### {entry.category}"
    lines = section.split("\n")
    if heading in lines:
        idx = lines.index(heading) + 1
        while idx < len(lines) and not lines[idx].startswith("### "):
            idx += 1
        while idx > 0 and lines[idx - 1].strip() == "":
            idx -= 1
        lines[idx:idx] = format_entry(entry).split("\n")
    else:
        order = {c: i for i, c in enumerate(CATEGORIES)}
        insert_at = len(lines)
        for i, ln in enumerate(lines):
            if ln.startswith("### ") and order.get(ln[4:], 99) > order[entry.category]:
                insert_at = i
                break
        new_block = ["", heading, format_entry(entry)]
        if insert_at < len(lines):
            new_block.append("")
        lines[insert_at:insert_at] = new_block
    result = "\n".join(lines).rstrip("\n") + "\n"
    return result + ("\n" + after if after else "")
