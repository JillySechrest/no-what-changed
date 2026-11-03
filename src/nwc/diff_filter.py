"""Drop noise from a unified diff and cap its size."""

import re

NOISE_PATTERNS = [
    r"(^|/)package-lock\.json$",
    r"(^|/)yarn\.lock$",
    r"(^|/)pnpm-lock\.yaml$",
    r"(^|/)poetry\.lock$",
    r"(^|/)uv\.lock$",
    r"(^|/)Cargo\.lock$",
    r"(^|/)(vendor|node_modules|dist|build)/",
    r"\.min\.(js|css)$",
    r"\.(png|jpg|jpeg|gif|svg|ico|woff2?)$",
    r"(^|/)CHANGELOG\.md$",
]
_NOISE = [re.compile(p) for p in NOISE_PATTERNS]
_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")

TRUNCATION_MARKER = "\n[diff truncated]\n"


def split_files(diff: str) -> list[tuple[str, str]]:
    """Split a unified diff into (path, text) chunks."""
    chunks: list[tuple[str, list[str]]] = []
    for line in diff.splitlines(keepends=True):
        match = _HEADER.match(line.rstrip("\n"))
        if match:
            chunks.append((match.group(2), [line]))
        elif chunks:
            chunks[-1][1].append(line)
    return [(path, "".join(lines)) for path, lines in chunks]


def is_noise(path: str) -> bool:
    return any(p.search(path) for p in _NOISE)


def filter_diff(diff: str, max_chars: int = 40_000) -> tuple[str, bool]:
    """Return (filtered_diff, truncated). Noise files are removed first."""
    kept = [text for path, text in split_files(diff) if not is_noise(path)]
    out = ""
    for text in kept:
        if len(out) + len(text) > max_chars:
            remaining = max_chars - len(out)
            if remaining > 0:
                out += text[:remaining]
            return out + TRUNCATION_MARKER, True
        out += text
    return out, False
