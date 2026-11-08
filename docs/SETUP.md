# 처음 설정 — pkg.sosomlab.com을 띄우기까지 (순서대로)

> 각 단계의 **[사용자]** 는 GitHub·Cloudflare 화면이나 관리자 권한이 필요해 직접 해야 하는 일, **[세션]** 은 Claude 세션이 하는 일이다.

## 1. 서명 키 — ✅ 완료(10-05)

- [세션] Linux VM에서 RSA 4096 서명 키 생성 · 파일 = `~/.config/sosomlab-linux-repo/` → [KEYS.md](KEYS.md).
- [사용자] `signing-private.asc`와 `revocation-cert.rev`를 비밀번호 관리자 등 안전한 곳에 백업(KEYS.md §3).

## 2. 저장소 골격 — ✅ 완료(10-05)

- [세션] 골격 생성 · Nexa Clip 등록(`apps/nexa-clip.toml`) · 로컬 생성·서명·apt 검증(`scripts/test_apt_local.sh` — 서명 검증 + GitHub 리다이렉트 내려받기 통과 · 변조 색인 거부 확인).
- [사용자] GitHub에 `SosomLab/linux-repo`(공개) 생성 — ✅ · [세션] 원격 연결 — ✅.

## 3. GitHub 시크릿 — [사용자] — ✅ 완료(10-05)

`SosomLab/linux-repo` → Settings → Secrets and variables → Actions → **New repository secret** 3개:

| 이름 | 값 | 어디서 |
|---|---|---|
| `LINUX_REPO_GPG_PRIVATE_KEY` | `~/.config/sosomlab-linux-repo/signing-private.asc` **전문**(`-----BEGIN PGP PRIVATE KEY BLOCK-----`부터 끝 줄까지) | 이 VM. 터미널에서 `gh secret set LINUX_REPO_GPG_PRIVATE_KEY -R SosomLab/linux-repo < ~/.config/sosomlab-linux-repo/signing-private.asc`로 넣어도 된다(화면에 안 찍힘) |
| `CLOUDFLARE_API_TOKEN` | 4단계에서 만드는 토큰 | Cloudflare |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 계정 ID | Cloudflare 대시보드 → Workers & Pages 오른쪽(또는 계정 홈 URL의 32자리) |

## 4. Cloudflare — [사용자] — ✅ 완료(10-05)

1. **API 토큰**: 우측 상단 프로필 → My Profile → API Tokens → Create Token → **Custom token**
   - 권한: `Account` · `Cloudflare Pages` · **Edit** (이것 하나)
   - Account Resources: Include · 해당 계정
   - 만든 토큰 문자열 → 3단계 `CLOUDFLARE_API_TOKEN`.
2. **Pages 프로젝트 만들기**: Workers & Pages → Create → (새 “Create an app” 화면이면 맨 아래 **Continue to Pages**) → **Use direct upload**(“Upload assets”)
   - ⚠️ 새 화면의 “Upload your static files”는 Pages가 아니라 Worker를 만든다 — 고르지 않는다.
   - 프로젝트 이름: **`linux-repo`**(워크플로가 이 이름으로 배포한다)
   - 처음 화면에서 파일을 올리라고 하면 빈 폴더 대신 아무 `index.html` 하나로 첫 배포를 해 두거나, 프로젝트만 만들고 닫는다(실제 내용은 CI가 올림).
   - ⚠️ Git 연결(Connect to Git) 방식이 아니다 — 서명 개인 키를 Cloudflare 빌드에 넣지 않기 위해 GitHub Actions가 서명까지 끝낸 결과만 올린다.
3. **사용자 지정 도메인**: 프로젝트 `linux-repo` → Custom domains → Set up a custom domain → `pkg.sosomlab.com`
   - `sosomlab.com`이 같은 계정의 zone이면 CNAME이 자동으로 추가된다(활성화까지 수 분).
4. **캐시 규칙 걸지 않기**: `sosomlab.com` zone의 Caching → Cache Rules에 `pkg.sosomlab.com`을 덮는 규칙이 없게 둔다(색인은 `_headers`로 `no-cache` · 옛 색인과 섞이면 apt 해시 불일치).

## 5. 첫 배포 — ✅ 완료(10-05 · 실도메인 apt 서명 검증 + GitHub 302 내려받기 통과)

1. [세션] 커밋 → [사용자 승인] push(`main`).
2. [사용자 또는 세션(gh)] Actions → `publish` → **Run workflow**.
3. [세션] 확인: `https://pkg.sosomlab.com/` 안내 화면 · `repo.json` · `apt/dists/stable/InRelease` · 패키지 내려받기(`/apt/pool/…` — 11-08부터 사이트가 직접 서빙 · 그 전엔 GitHub 302 · §10).

## 6. 설치 시험 — ✅ 완료(10-05 · 이 VM에 0.1.7 설치 · `apt-cache policy` 출처 = pkg.sosomlab.com)

- [세션] 실제 도메인으로 root 없이 검증: `scripts/test_apt_local.sh`와 같은 방식(주소만 실제).
- [사용자] 이 VM에서 실제 설치(관리자 암호 필요):
  ```sh
  sudo curl -fsSLo /usr/share/keyrings/sosomlab-archive-keyring.gpg https://pkg.sosomlab.com/sosomlab-archive-keyring.gpg
  sudo curl -fsSLo /etc/apt/sources.list.d/sosomlab.sources https://pkg.sosomlab.com/apt/sosomlab.sources
  sudo apt update && sudo apt install nexa-clip
  ```
  지금 설치본(로컬 `.deb` 0.1.6 표시)이 저장소의 0.1.7로 올라간다 — 실행 중이면 앱을 한 번 재시작.

## 7. 앱 저장소와 잇기 — ✅ 완료(10-05 · v0.1.8 릴리스 신호로 publish 자동 실행 · 실사이트 0.1.8 반영)

- 앱 릴리스 끝에 발행 신호 → [ADDING-AN-APP.md](ADDING-AN-APP.md) §4. Nexa Clip `release.yml`에 연결 — ✅ 완료(10-05 · v0.1.8 신호 → publish [37263714314](https://github.com/SosomLab/linux-repo/actions/runs/37263714314) 성공).
- [사용자] `LINUX_REPO_DISPATCH_TOKEN`(fine-grained · `SosomLab/linux-repo` Contents Read/write) 발급 → `SosomLab/nexa-clip` 시크릿에 등록 — ✅ 완료(10-05 · dispatch 204 · `repository_dispatch` publish 성공).
- [세션] `publish` 실행 기록 — 실행 화면 Summary에 **요청 기록**(종류 · 실행 주체 · 접수 시각 · 신호의 `client_payload`)과 **진행 기록**(단계별 결과 · 버전 변화 · 배포 여부)을 남기고, 외부 요청은 실행 이름에 앱 · 태그를 붙인다 — ✅ 완료(10-05 · v0.1.8 신호 실행에서 실이름 `publish · 외부 요청 · nexa-clip v0.1.8` · 요청 기록에 `app` · `tag` · `repo` · `run_url` 확인).
  - 보낸 쪽(저장소 · 실행 주소)까지 남으려면 신호가 `app` · `tag` · `repo` · `run_url`을 실어야 한다 → [ADDING-AN-APP.md](ADDING-AN-APP.md) §4 예시(갱신됨). Nexa Clip `release.yml`에 넣을 때 이 예시를 쓴다.
  - 기록은 Actions 실행에 붙어 GitHub 보존 기간(기본 90일)까지만 남는다.

## 8. RPM(dnf) — 발행 중 · dnf 실기만 남음

- [세션] 생성기 · 사이트 준비 — ✅ 완료(10-05 · `e2a9ba6`). `apps/nexa-clip.toml`의 `[rpm]`을 켰다.
  - CI의 RPM 경로(createrepo-c 설치 → `createrepo_c` 색인 → `repomd.xml.asc` 서명) — ✅ 동작 확인(11-08 · run [42467176929](https://github.com/SosomLab/linux-repo/actions/runs/42467176929) · `rpm/x86_64/repodata/repomd.xml` 200 · 색인에 등록 앱 6개 전부).
  - 릴리스에 `.rpm`이 없으면 생성기가 `::warning::`만 남기고 건너뛴다 — APT 발행은 그대로, 사이트의 dnf 안내(`<!--RPM-->` 블록)도 빠진다(v0.1.7 로컬 실행 + `test_apt_local.sh` 통과로 확인).
  - `.rpm`이 생기면 다음 발행부터 `rpm/sosomlab.repo` · 서명된 `repodata` · 사이트 dnf 설치·제거 안내가 저절로 나타난다.
- [세션] 사이트 `404.html` 추가 — ✅ 10-05. 없으면 Pages가 없는 경로에 200 + `index.html`을 준다(실측: `/rpm/sosomlab.repo` → HTML) → `.rpm` 발행 전에 dnf 안내를 따라 하면 HTML이 `/etc/yum.repos.d`에 저장된다. 이제 진짜 404 — 다음 배포부터.
- 앱 릴리스의 `.rpm` — ✅ 등록 앱 6개 모두 올린다(Nexa Clip은 `nexa-clip-{version}-linux-x64.rpm`).
- Fedora/Rocky에서 `dnf install` 실기(createrepo_c 색인 · `repomd.xml.asc` 서명 · 패키지 내려받기) — ⏳ 남음(이 PC엔 dnf가 없다).

## 9. 등록 앱 — 6개(11-08 현재 · `repo.json` 기준)

| 패키지 | 저장소 | 발행 버전 | 등록 |
|---|---|---|---|
| `nexa-clip` | SosomLab/nexa-clip | 0.2.8 | 10-05 |
| `nexa-sql` | SosomLab/nexa-sql | 0.7.0 | 10-05 |
| `nexa-dir` | SosomLab/nexa-dir3 | 0.30.2 | 10-05 |
| `nexa-coffee` | SosomLab/nexa-coffee | 0.1.5 | 10-09 |
| `nexa-markdown-viewer` | kiros33/sosomlab-nexa-viewer | 0.4.0 | 10-09 |
| `nexa-beep` | SosomLab/nexa-beep | 0.10.1 | 10-09 |

- [세션] 미등록 앱 점검 — `publish`가 조직 공개 저장소 중 `.deb`/`.rpm`을 릴리스하면서 `apps/*.toml`에 없는 앱을 `::warning::`과 Summary로 알린다(`scripts/check_unregistered.py`) — ✅ 10-09(11-08 실행: 공개 저장소 13개 중 미등록 없음).

## 10. 운영 이슈 · 조치

### 11-08 — 앱 발행 신호 실행 연속 실패 · 사용자 설치 504

| 시각(KST) | 일 | 조치 |
|---|---|---|
| 16:32 | nexa-clip v0.2.7 신호 실행 [42459212122](https://github.com/SosomLab/linux-repo/actions/runs/42459212122) 실패 — nexa-beep 저장소의 서버 릴리스 `beepd-v1.0.0`이 `releases/latest`가 돼 앱 `.deb`를 못 찾음(저장소 전체 생성이 멈춤) | `17383bf` — 앱 릴리스를 `tag_prefix`+숫자 태그로 골라냄 |
| 18:07 ~ 18:25 | nexa-beep v0.10.0 · nexa-clip v0.2.8 신호 실행과 수동 실행 연속 실패 — 자산 다운로드(`browser_download_url`) HTTP 504 | `675e2c1` 5xx·타임아웃 재시도(4회) → 그래도 504 → `92dd82a` GitHub API 자산 경로 우선(browser URL은 폴백) · 수동 실행 [42467176929](https://github.com/SosomLab/linux-repo/actions/runs/42467176929) 성공 — 색인에 nexa-clip 0.2.8 · nexa-beep 0.10.0 반영 |
| 18:30 | 색인은 정상이지만 **사용자 내려받기 실패** — `/apt/pool/…` 302가 가리키는 `github.com/…/releases/download/…`가 한국 edge(koreacentral)에서 **모든 자산 504**(nexa-clip 0.2.6~0.2.8 · nexa-beep · nexa-dir · nexa-sql · SHA256SUMS). API 자산 경로는 200 · githubstatus는 "All Systems Operational" | 패키지 파일을 **사이트에 직접 탑재**(25 MiB 넘는 파일만 302 · `e9c3ca6`) — 근거는 아래 · 다음 `publish` 실행부터 적용 |
| 18:39 | nexa-beep v0.10.1 신호 실행 [42468108324](https://github.com/SosomLab/linux-repo/actions/runs/42468108324) 성공(`92dd82a` API 경로 — 색인만 갱신 · 사용자 내려받기는 아직 302 → 504) | — |

- 탑재 방식 근거: 등록 앱 패키지가 모두 Pages 파일 한도(25 MiB)보다 작다(가장 큰 nexa-sql `.deb` 14.5 MB). CI가 색인 해시를 내려고 이미 받는 파일이라 추가 다운로드가 없다. 사용자 설치가 GitHub 다운로드 CDN 상태와 무관해진다.
- 재발 확인: `publish` Summary의 **배포 확인**이 첫 `.deb`를 pkg.sosomlab.com에서 끝까지 받아 본다.
- 탑재 방식 첫 배포 — ✅ 11-08 19:29 KST · run [42471586022](https://github.com/SosomLab/linux-repo/actions/runs/42471586022)(`4e36ccf` · 실은 패키지 12 · 리다이렉트 0). 실도메인에서 `.deb` 6개 전부 200 · nexa-clip 0.2.8 `.deb` SHA256이 서명 색인과 일치 · `.rpm` 200. 같은 실행에서 nexa-beep 0.10.1도 발행.
- 정기 실행 판정 — ✅ 11-08 19:30 KST run [42471702467](https://github.com/SosomLab/linux-repo/actions/runs/42471702467)(탑재 방식으로 생성 · 실은 패키지 12 · 버전 변화 없음 → `배포 필요: false`로 배포 건너뜀).
