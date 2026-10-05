# linux-repo — pkg.sosomlab.com

SosomLab 앱의 **서명된 Linux 패키지 저장소**(APT · RPM). 사용자는 저장소를 한 번 등록하면 `apt install` / `apt upgrade`(또는 `dnf`)로 SosomLab 앱을 설치·갱신한다.

```sh
sudo curl -fsSLo /usr/share/keyrings/sosomlab-archive-keyring.gpg https://pkg.sosomlab.com/sosomlab-archive-keyring.gpg
sudo curl -fsSLo /etc/apt/sources.list.d/sosomlab.sources https://pkg.sosomlab.com/apt/sosomlab.sources
sudo apt update && sudo apt install nexa-clip
```

RPM(Fedora · RHEL 계열) — 앱 릴리스에 `.rpm`이 있을 때만 발행된다(없으면 생성기가 경고하고 건너뛰며, 사이트의 dnf 안내도 빠진다):

```sh
sudo curl -fsSLo /etc/yum.repos.d/sosomlab.repo https://pkg.sosomlab.com/rpm/sosomlab.repo
sudo dnf install nexa-clip
```

## 구조

| 경로 | 무엇 |
|---|---|
| `apps/*.toml` | **앱 등록**(파일 하나 = 앱 하나) — [docs/ADDING-AN-APP.md](docs/ADDING-AN-APP.md) |
| `scripts/build_repo.py` | 등록 앱의 최신 GitHub Release로 색인 생성 · GPG 서명 · `_redirects` 생성 → `public/` |
| `scripts/test_apt_local.sh` · `serve_local.py` | 배포 전 로컬 검증(root 없이 apt가 서명 검증 + 리다이렉트로 받는지) |
| `site/` | 사이트 정적 파일(`index.html` 설치 안내 · `404.html` 없는 경로는 진짜 404 · `_headers` 캐시 금지 · `_redirects` 머리) |
| `.github/workflows/publish.yml` | 생성 → Cloudflare Pages(`linux-repo` 프로젝트) 배포 · 수동 / 앱 릴리스 신호 / 하루 1회 · 실행 Summary에 요청 · 진행 기록 |
| `docs/SETUP.md` | 처음 설정 순서(사용자 할 일 포함) |
| `docs/KEYS.md` | 서명 키 위치 · 백업 · 다른 PC · 연장 · 폐기 |

## 설계 요점

- **패키지 파일은 싣지 않는다** — 색인의 `Filename`을 `_redirects`가 앱 GitHub Release 자산으로 302 보낸다(apt 3.x가 GitHub 2단 리다이렉트를 따라감 · 10-05 실측). 무결성 = 서명된 `InRelease`의 해시.
- **최신 정식 릴리스 하나만** 싣는다(Pages 배포 = 사이트 전체 교체 · 단순함 우선).
- 서명은 **GitHub Actions**에서만(개인 키 = 시크릿) · Cloudflare는 결과물만 받는다(Direct Upload).
- ⚠️ 한 번 발행한 Release 자산은 지우거나 다시 올리지 않는다.

## 로컬에서 돌려 보기(서명 키가 있는 PC)

```sh
python3 scripts/build_repo.py --key 2522614046FAEE116F4A2FD706236F6AA8EB8FD6
bash scripts/test_apt_local.sh public nexa-clip
```

조사·결정 배경: SosomLab/nexa-clip `docs/35-linux-distribution-channels.md`(§3-1 자체 APT · §3-14 Cloudflare Pages).
