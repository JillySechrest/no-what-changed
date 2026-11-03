"""Thin GitHub REST wrapper. Uses only the standard library."""

import base64
import json
import re
import urllib.error
import urllib.request

API = "https://api.github.com"
PR_URL = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)")


def parse_pr_url(url: str) -> tuple[str, str, int]:
    m = PR_URL.search(url)
    if not m:
        raise ValueError(f"not a GitHub PR URL: {url}")
    return m.group(1), m.group(2), int(m.group(3))


class GitHub:
    def __init__(self, token: str):
        self.token = token

    def _request(self, method: str, path: str, body=None, accept="application/vnd.github+json"):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(API + path, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", accept)
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.read().decode()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"GitHub {method} {path} failed: {e.code} {e.read().decode()}") from e

    def get_pr(self, owner: str, repo: str, number: int) -> dict:
        return json.loads(self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}"))

    def get_diff(self, owner: str, repo: str, number: int) -> str:
        return self._request(
            "GET", f"/repos/{owner}/{repo}/pulls/{number}", accept="application/vnd.github.diff"
        )

    def get_file(self, owner: str, repo: str, path: str, ref: str) -> tuple[str, str | None]:
        try:
            raw = self._request("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
        except RuntimeError as e:
            if " 404 " in str(e):
                return "", None
            raise
        data = json.loads(raw)
        return base64.b64decode(data["content"]).decode(), data["sha"]

    def branch_sha(self, owner: str, repo: str, branch: str) -> str:
        raw = self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        return json.loads(raw)["object"]["sha"]

    def create_branch(self, owner: str, repo: str, branch: str, sha: str) -> None:
        self._request(
            "POST", f"/repos/{owner}/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha}
        )

    def put_file(self, owner, repo, path, branch, content, message, sha=None) -> None:
        body = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", body)

    def open_pr(self, owner, repo, head, base, title, body) -> str:
        raw = self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            {"head": head, "base": base, "title": title, "body": body},
        )
        return json.loads(raw)["html_url"]
