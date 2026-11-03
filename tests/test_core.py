import json
from types import SimpleNamespace

import pytest

from nwc.cli import is_bot_pr
from nwc.diff_filter import filter_diff, split_files
from nwc.github import parse_pr_url
from nwc.render import add_entry
from nwc.summarize import Entry, parse_entry, summarize

DIFF = (
    "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@\n-x = 1\n+x = 2\n"
    "diff --git a/package-lock.json b/package-lock.json\n@@\n+noise\n"
    "diff --git a/CHANGELOG.md b/CHANGELOG.md\n@@\n+self\n"
)


def test_split_and_filter_drops_noise():
    assert [p for p, _ in split_files(DIFF)] == ["app.py", "package-lock.json", "CHANGELOG.md"]
    out, truncated = filter_diff(DIFF)
    assert "app.py" in out and "noise" not in out and "self" not in out
    assert not truncated


def test_filter_truncates():
    out, truncated = filter_diff(DIFF, max_chars=30)
    assert truncated and out.endswith("[diff truncated]\n")


def test_parse_entry_validates():
    e = parse_entry(json.dumps({"category": "Bogus", "summary": "Does a thing."}))
    assert e.category == "Changed"
    with pytest.raises(ValueError):
        parse_entry(json.dumps({"category": "Added", "summary": " "}))


def test_summarize_uses_client():
    payload = json.dumps({"category": "Fixed", "summary": "Fixes x.", "scope_creep_note": ""})
    msg = SimpleNamespace(content=payload)
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=msg)])
            )
        )
    )
    assert summarize("t", "b", "d", False, client, "m").category == "Fixed"


def test_add_entry_to_empty_creates_structure():
    out = add_entry("", Entry("Added", "New thing.", pr_number=1))
    assert "## [Unreleased]" in out and "### Added\n- New thing. (#1)" in out


def test_add_entry_orders_categories_and_appends():
    base = add_entry("", Entry("Fixed", "Fix.", pr_number=1))
    out = add_entry(base, Entry("Added", "Add.", pr_number=2))
    assert out.index("### Added") < out.index("### Fixed")
    out = add_entry(out, Entry("Added", "Add more.", "Also did y.", pr_number=3))
    assert out.index("- Add. (#2)") < out.index("- Add more. (#3)") < out.index("### Fixed")
    assert "  - Also changed: Also did y." in out


def test_add_entry_idempotent_and_preserves_releases():
    existing = "# Changelog\n\n## [Unreleased]\n\n## [0.1.0]\n\n- old\n"
    out = add_entry(existing, Entry("Added", "New.", pr_number=5))
    assert out.index("(#5)") < out.index("## [0.1.0]") and "- old" in out
    assert add_entry(out, Entry("Added", "New.", pr_number=5)) == out


def test_add_entry_without_unreleased_section():
    out = add_entry("# Changelog\n\n## [0.1.0]\n\n- old\n", Entry("Added", "N.", pr_number=2))
    assert out.index("## [Unreleased]") < out.index("## [0.1.0]")


def test_parse_pr_url():
    assert parse_pr_url("https://github.com/a/b/pull/12") == ("a", "b", 12)
    with pytest.raises(ValueError):
        parse_pr_url("https://example.com")


def test_bot_pr_detection():
    assert is_bot_pr({"user": {"type": "Bot"}, "head": {"ref": "x"}})
    assert is_bot_pr({"user": {"type": "User"}, "head": {"ref": "nwc/changelog-3"}})
    assert not is_bot_pr({"user": {"type": "User"}, "head": {"ref": "feat/x"}})
