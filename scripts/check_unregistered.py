#!/usr/bin/env python3
"""미등록 앱 탐지 — SosomLab 조직의 공개 저장소 중 최신 정식 릴리스에 `.deb`(또는 `.rpm`)를 올리면서
apps/*.toml에 등록되지 않은 것을 찾아 Actions 경고(::warning::)와 실행 요약에 적는다.

왜: 2026-10-09 nexa-beep이 Linux 설치본을 릴리스하고 있었는데 여기 등록이 빠져, 사용자가
`sudo apt install nexa-beep`을 해도 apt가 "이미 최신(옛 .deb 버전)"으로 아무것도 하지 않았다.
앱 쪽이 등록을 잊어도 저장소 쪽이 매 발행마다 알아채게 한다(경고만 · 발행은 막지 않는다).

    python3 scripts/check_unregistered.py [--org SosomLab] [--apps apps] [--strict]
    --strict = 미등록이 있으면 종료 코드 1(기본은 경고만).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path


def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "sosomlab-linux-repo", "Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--org", default="SosomLab")
    ap.add_argument("--apps", type=Path, default=Path("apps"))
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    registered = {tomllib.loads(p.read_text())["github"].lower() for p in a.apps.glob("*.toml")}
    repos: list[dict] = []
    page = 1
    while True:
        chunk = http_json(f"https://api.github.com/orgs/{a.org}/repos?type=public&per_page=100&page={page}")
        if not chunk:
            break
        repos += chunk
        page += 1

    missing: list[tuple[str, str, list[str]]] = []
    for repo in repos:
        full = repo["full_name"]
        if full.lower() in registered or repo.get("archived"):
            continue
        try:
            rel = http_json(f"https://api.github.com/repos/{full}/releases/latest")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # 릴리스 없음
            raise
        linux = sorted(x["name"] for x in rel.get("assets", []) if x["name"].endswith((".deb", ".rpm")))
        if linux:
            missing.append((full, rel["tag_name"], linux))

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = ["## 미등록 앱 점검", ""]
    if missing:
        lines += ["| 저장소 | 최신 릴리스 | Linux 자산 | 조치 |", "| --- | --- | --- | --- |"]
        for full, tag, assets in missing:
            print(f"::warning::{full} {tag}: Linux 패키지 자산({', '.join(assets)})을 릴리스하지만 apps/*.toml에 등록되지 않았다 — docs/ADDING-AN-APP.md", flush=True)
            lines.append(f"| `{full}` | {tag} | {', '.join(f'`{x}`' for x in assets)} | `apps/<패키지>.toml` 추가(ADDING-AN-APP.md) |")
    else:
        lines.append(f"`{a.org}` 공개 저장소 {len(repos)}개 중 Linux 패키지를 릴리스하면서 미등록인 앱 **없음** · 등록 {len(registered)}개.")
    lines.append("")
    text = "\n".join(lines)
    print(text, file=sys.stderr)
    if summary:
        Path(summary).open("a", encoding="utf-8").write(text + "\n")
    return 1 if (missing and a.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
