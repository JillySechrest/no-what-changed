# No, What Changed?

Nobody writes changelogs. Everyone agrees changelogs are useful. This bot reads the diff of a
merged PR, summarizes the behavior change, and opens a PR against `CHANGELOG.md`.

The diff is the source of truth. Commit messages are never summarized, because they lie more
often than diffs do. The PR title and body are treated as claims to check. If the diff does more
than the title says, the entry gets an `Also changed:` line.

## Status

v0.1. The pipeline is unit-tested with fixture diffs and a stubbed model. It has **not** yet been
run against a broad set of real PRs, so expect the scope-creep detection to be rough.

## Use as a GitHub Action

Add an `OPENAI_API_KEY` repository secret, then:

```yaml
on:
  pull_request:
    types: [closed]
permissions:
  contents: write
  pull-requests: write
jobs:
  changelog:
    if: github.event.pull_request.merged == true && !startsWith(github.event.pull_request.head.ref, 'nwc/changelog-')
    runs-on: ubuntu-latest
    steps:
      - uses: JillySechrest/no-what-changed@main
        with:
          pr-url: ${{ github.event.pull_request.html_url }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

The repo's Actions settings must allow workflows to create pull requests.

## Use as a CLI

```
pip install -e ".[dev]"
export GITHUB_TOKEN=... OPENAI_API_KEY=...
nwc https://github.com/OWNER/REPO/pull/12            # dry run, prints the entry
nwc https://github.com/OWNER/REPO/pull/12 --apply    # opens a PR against CHANGELOG.md
```

## Guardrails

- Skips PRs from bots and from its own `nwc/changelog-*` branches.
- Idempotent: a PR number already in the changelog is never added twice.
- Drops lockfiles, vendored and generated files, and `CHANGELOG.md` itself from the diff.
- Caps diff size at 40,000 characters and tells the model when it truncated.

## Limits

- It sees the diff, not your intent. It can describe what changed, not why.
- Large PRs get a partial view.
- Entries go under `[Unreleased]`. Cutting a release is still a human job.

## Develop

```
pytest -q
ruff check .
```

MIT licensed.
