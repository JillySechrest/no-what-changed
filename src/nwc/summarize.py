"""Turn a filtered diff into a structured changelog entry."""

import json
from dataclasses import dataclass

CATEGORIES = ["Added", "Changed", "Fixed", "Removed"]

SYSTEM_PROMPT = """You write changelog entries from code diffs.
Rules:
- Describe the behavior change a user or maintainer would notice. Not the files touched.
- The diff is the source of truth. The PR title and body are claims to check, not facts.
- Plain language. No marketing words. One or two sentences.
- If the diff does meaningfully more than the PR title claims, set scope_creep_note to one
  short sentence naming the extra change. Otherwise set it to an empty string.
- If the diff is truncated, say only what you can see.
Respond with JSON: {"category": "Added|Changed|Fixed|Removed", "summary": "...",
"scope_creep_note": "..."}"""


@dataclass
class Entry:
    category: str
    summary: str
    scope_creep_note: str = ""
    pr_number: int | None = None


def build_user_prompt(title: str, body: str, diff: str, truncated: bool) -> str:
    note = "\n(The diff was truncated for size.)" if truncated else ""
    return f"PR title: {title}\nPR body: {body or '(none)'}\n\nDiff:{note}\n{diff}"


def parse_entry(raw: str) -> Entry:
    data = json.loads(raw)
    category = data.get("category", "Changed")
    if category not in CATEGORIES:
        category = "Changed"
    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise ValueError("model returned an empty summary")
    return Entry(
        category=category,
        summary=summary,
        scope_creep_note=str(data.get("scope_creep_note", "")).strip(),
    )


def summarize(title: str, body: str, diff: str, truncated: bool, client, model: str) -> Entry:
    """`client` is an openai.OpenAI-compatible object."""
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(title, body, diff, truncated)},
        ],
    )
    return parse_entry(response.choices[0].message.content)
