#!/usr/bin/env python3
"""pkg.sosomlab.com 저장소 트리를 만든다 — 등록된 앱의 최신 릴리스로 APT(+RPM) 색인을 생성하고 서명한다.

사용:
    python3 scripts/build_repo.py --key <서명 키 지문> [--out public] [--apps apps] [--site site]

- 앱 목록 = apps/*.toml(파일 하나 = 앱 하나 · 형식은 apps/nexa-clip.toml 주석).
- 패키지 파일은 싣지 않는다. 색인의 Filename/href 경로를 `_redirects`가 GitHub Release 자산으로 302 보낸다
  (apt 3.x가 GitHub의 2단 리다이렉트를 끝까지 따라가는 것을 10-05 실측). 무결성은 서명된 색인의 해시가 지킨다.
- 최신 정식 릴리스 하나만 싣는다(가장 단순 · Pages 배포는 사이트 전체 교체).
- 외부 의존 없음(표준 라이브러리 + dpkg-deb · gpg · RPM이 있을 때만 createrepo_c).
- `[deb]` 자산이 릴리스에 없으면 실패한다. `[rpm]` 자산은 없으면 경고만 하고 건너뛴다(앱이 .rpm을 아직 안 만들어도
  APT 발행은 계속된다). RPM이 하나도 없으면 dnf 저장소 파일과 사이트의 RPM 안내(`<!--RPM-->…<!--/RPM-->`)를 빼고 낸다.
- GITHUB_TOKEN 환경 변수가 있으면 API 호출에 쓴다(없으면 미인증 60회/시간).
"""

from __future__ import annotations

import argparse
import email.utils
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
from pathlib import Path

SUITE = "stable"
COMPONENT = "main"
ORIGIN = "SosomLab"
KEYRING_NAME = "sosomlab-archive-keyring"


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def http_get(url: str, accept: str | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "sosomlab-linux-repo"})
    if accept:
        req.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def latest_release(repo: str) -> dict:
    """최신 정식 릴리스(초안·사전 배포 제외)."""
    return json.loads(http_get(f"https://api.github.com/repos/{repo}/releases/latest", "application/vnd.github+json"))


def hashes(data: bytes) -> dict[str, str]:
    return {
        "MD5sum": hashlib.md5(data).hexdigest(),
        "SHA1": hashlib.sha1(data).hexdigest(),
        "SHA256": hashlib.sha256(data).hexdigest(),
    }


def deb_control(path: Path) -> str:
    """.deb의 control 문단을 그대로 꺼낸다(끝 빈 줄 제거)."""
    out = subprocess.run(["dpkg-deb", "--field", str(path)], check=True, capture_output=True, text=True).stdout
    return out.rstrip("\n")


def gpg(args: list[str], key: str) -> None:
    subprocess.run(["gpg", "--batch", "--yes", "--local-user", key, *args], check=True)


class Build:
    def __init__(self, out: Path, key: str):
        self.out = out
        self.key = key
        self.redirects: list[str] = []
        self.packages: dict[str, list[str]] = {}  # arch -> Packages 문단들
        self.rpm_assets: dict[str, list[tuple[str, str, Path]]] = {}  # arch -> (자산 이름, URL, 임시 파일)
        self.manifest: list[dict] = []

    # ── APT ────────────────────────────────────────────────────────────
    def add_deb(self, pkg: str, arch: str, asset_name: str, url: str, data: bytes, tmp: Path) -> None:
        f = tmp / asset_name
        f.write_bytes(data)
        control = deb_control(f)
        rel = f"pool/{COMPONENT}/{pkg[0]}/{pkg}/{asset_name}"
        h = hashes(data)
        stanza = (
            f"{control}\nFilename: {rel}\nSize: {len(data)}\n"
            f"MD5sum: {h['MD5sum']}\nSHA1: {h['SHA1']}\nSHA256: {h['SHA256']}"
        )
        self.packages.setdefault(arch, []).append(stanza)
        self.redirects.append(f"/apt/{rel} {url} 302")

    def write_apt(self) -> None:
        dist = self.out / "apt" / "dists" / SUITE
        files: list[tuple[str, bytes]] = []
        for arch, stanzas in sorted(self.packages.items()):
            body = ("\n\n".join(stanzas) + "\n").encode()
            d = dist / COMPONENT / f"binary-{arch}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "Packages").write_bytes(body)
            gz = gzip.compress(body, mtime=0)
            (d / "Packages.gz").write_bytes(gz)
            files += [(f"{COMPONENT}/binary-{arch}/Packages", body), (f"{COMPONENT}/binary-{arch}/Packages.gz", gz)]
        lines = [
            f"Origin: {ORIGIN}",
            f"Label: {ORIGIN}",
            f"Suite: {SUITE}",
            f"Codename: {SUITE}",
            f"Date: {email.utils.formatdate(usegmt=True)}",
            f"Architectures: {' '.join(sorted(self.packages))}",
            f"Components: {COMPONENT}",
            "Description: SosomLab Linux packages (pkg.sosomlab.com)",
        ]
        for field, algo in (("MD5Sum", "md5"), ("SHA1", "sha1"), ("SHA256", "sha256")):
            lines.append(f"{field}:")
            for name, data in files:
                lines.append(f" {hashlib.new(algo, data).hexdigest()} {len(data):>8} {name}")
        release = dist / "Release"
        release.write_text("\n".join(lines) + "\n")
        gpg(["--clearsign", "--output", str(dist / "InRelease"), str(release)], self.key)
        gpg(["--armor", "--detach-sign", "--output", str(dist / "Release.gpg"), str(release)], self.key)

    # ── RPM(앱 릴리스에 .rpm이 생기면 동작 · createrepo_c 필요) ───────────
    def add_rpm(self, arch: str, asset_name: str, url: str, data: bytes, tmp: Path) -> None:
        d = tmp / "rpm" / arch / "Packages"
        d.mkdir(parents=True, exist_ok=True)
        f = d / asset_name
        f.write_bytes(data)
        self.rpm_assets.setdefault(arch, []).append((asset_name, url, f))
        self.redirects.append(f"/rpm/{arch}/Packages/{asset_name} {url} 302")

    def write_rpm(self, tmp: Path) -> None:
        for arch, items in sorted(self.rpm_assets.items()):
            src = tmp / "rpm" / arch
            subprocess.run(["createrepo_c", "--quiet", str(src)], check=True)
            dst = self.out / "rpm" / arch
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src / "repodata", dst / "repodata", dirs_exist_ok=True)
            repomd = dst / "repodata" / "repomd.xml"
            # 패키지 파일은 GitHub 자산 그대로라 RPM 자체 서명은 없다 → repo_gpgcheck(메타데이터 서명)로 무결성을 지킨다.
            gpg(["--armor", "--detach-sign", "--output", str(repomd) + ".asc", str(repomd)], self.key)

    # ── 공통 산출물 ─────────────────────────────────────────────────────
    def write_common(self, site: Path) -> None:
        out = self.out
        # 공개 키 — apt는 바이너리(.gpg), dnf·사람은 armor(.asc).
        pub_bin = subprocess.run(["gpg", "--export", self.key], check=True, capture_output=True).stdout
        pub_asc = subprocess.run(["gpg", "--armor", "--export", self.key], check=True, capture_output=True).stdout
        (out / f"{KEYRING_NAME}.gpg").write_bytes(pub_bin)
        (out / f"{KEYRING_NAME}.asc").write_bytes(pub_asc)
        # apt 소스(deb822) · dnf 저장소 파일.
        (out / "apt").mkdir(parents=True, exist_ok=True)
        (out / "apt" / "sosomlab.sources").write_text(
            "Types: deb\n"
            "URIs: https://pkg.sosomlab.com/apt\n"
            f"Suites: {SUITE}\n"
            f"Components: {COMPONENT}\n"
            f"Signed-By: /usr/share/keyrings/{KEYRING_NAME}.gpg\n"
        )
        if self.rpm_assets:
            (out / "rpm").mkdir(parents=True, exist_ok=True)
            (out / "rpm" / "sosomlab.repo").write_text(
                "[sosomlab]\n"
                "name=SosomLab\n"
                "baseurl=https://pkg.sosomlab.com/rpm/$basearch\n"
                "enabled=1\n"
                "gpgcheck=0\n"
                "repo_gpgcheck=1\n"
                f"gpgkey=https://pkg.sosomlab.com/{KEYRING_NAME}.asc\n"
            )
        # 정적 파일(설치 안내 · 캐시 헤더) — 자리표시자 치환.
        fpr = self.key.upper()
        listing = "\n".join(
            f'<tr><td><code>{m["package"]}</code></td><td>{m["version"]}</td><td>{m["summary"]}</td></tr>'
            for m in self.manifest
        )
        for f in site.iterdir():
            if f.is_file():
                text = f.read_text()
                text = text.replace("{{FINGERPRINT}}", fpr).replace("{{PACKAGES}}", listing)
                # RPM 안내 블록 — dnf 저장소가 실제로 생겼을 때만 남긴다(없는 .repo 주소를 안내하지 않게).
                text = (text.replace("<!--RPM-->", "").replace("<!--/RPM-->", "") if self.rpm_assets
                        else re.sub(r"<!--RPM-->.*?<!--/RPM-->", "", text, flags=re.S))
                (out / f.name).write_text(text)
        static_redirects = (site / "_redirects").read_text() if (site / "_redirects").exists() else ""
        (out / "_redirects").write_text(static_redirects + "\n".join(self.redirects) + "\n")
        (out / "repo.json").write_text(json.dumps({"apps": self.manifest}, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--key", default=os.environ.get("LINUX_REPO_KEY"), help="서명 키 지문(또는 환경 변수 LINUX_REPO_KEY)")
    ap.add_argument("--apps", type=Path, default=Path("apps"))
    ap.add_argument("--site", type=Path, default=Path("site"))
    ap.add_argument("--out", type=Path, default=Path("public"))
    a = ap.parse_args()
    if not a.key:
        ap.error("서명 키 지문이 필요하다(--key 또는 LINUX_REPO_KEY)")
    if a.out.exists():
        shutil.rmtree(a.out)
    a.out.mkdir(parents=True)
    b = Build(a.out, a.key)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for app_file in sorted(a.apps.glob("*.toml")):
            app = tomllib.loads(app_file.read_text())
            rel = latest_release(app["github"])
            tag = rel["tag_name"]
            version = tag.removeprefix(app.get("tag_prefix", "v"))
            assets = {x["name"]: x["browser_download_url"] for x in rel["assets"]}
            log(f"{app['package']}: {tag}")
            for kind in ("deb", "rpm"):
                for arch, pattern in app.get(kind, {}).items():
                    name = pattern.format(version=version)
                    if name not in assets and kind == "rpm":
                        # Actions 경고 주석으로도 보이게(::warning::) — RPM 사용자는 이 버전을 못 받는다.
                        print(f"::warning::{app['package']} {tag}: RPM 자산 {name} 이(가) 릴리스에 없어 건너뛴다", flush=True)
                        continue
                    if name not in assets:
                        raise SystemExit(f"{app['package']} {tag}: 자산 {name} 이(가) 릴리스에 없다")
                    data = http_get(assets[name])
                    log(f"  {kind} {arch}: {name} ({len(data)} B)")
                    (b.add_deb(app["package"], arch, name, assets[name], data, tmp) if kind == "deb"
                     else b.add_rpm(arch, name, assets[name], data, tmp))
            b.manifest.append({"package": app["package"], "version": version, "tag": tag,
                               "summary": app.get("summary", ""), "github": app["github"]})
        if not b.packages and not b.rpm_assets:
            raise SystemExit("등록된 패키지가 없다")
        if b.packages:
            b.write_apt()
        if b.rpm_assets:
            b.write_rpm(tmp)
    b.write_common(a.site)
    log(f"완료 → {a.out}/ (앱 {len(b.manifest)} · 리다이렉트 {len(b.redirects)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
