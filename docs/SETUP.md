# 처음 설정 — pkg.sosomlab.com을 띄우기까지 (순서대로)

> 각 단계의 **[사용자]** 는 GitHub·Cloudflare 화면이나 관리자 권한이 필요해 직접 해야 하는 일, **[세션]** 은 Claude 세션이 하는 일이다.

## 1. 서명 키 — ✅ 완료(10-05)

- [세션] Linux VM에서 RSA 4096 서명 키 생성 · 파일 = `~/.config/sosomlab-linux-repo/` → [KEYS.md](KEYS.md).
- [사용자] `signing-private.asc`와 `revocation-cert.rev`를 비밀번호 관리자 등 안전한 곳에 백업(KEYS.md §3).

## 2. 저장소 골격 — ✅ 완료(10-05)

- [세션] 골격 생성 · Nexa Clip 등록(`apps/nexa-clip.toml`) · 로컬 생성·서명·apt 검증(`scripts/test_apt_local.sh` — 서명 검증 + GitHub 리다이렉트 내려받기 통과 · 변조 색인 거부 확인).
- [사용자] GitHub에 `SosomLab/linux-repo`(공개) 생성 — ✅ · [세션] 원격 연결 — ✅.

## 3. GitHub 시크릿 — [사용자]

`SosomLab/linux-repo` → Settings → Secrets and variables → Actions → **New repository secret** 3개:

| 이름 | 값 | 어디서 |
|---|---|---|
| `LINUX_REPO_GPG_PRIVATE_KEY` | `~/.config/sosomlab-linux-repo/signing-private.asc` **전문**(`-----BEGIN PGP PRIVATE KEY BLOCK-----`부터 끝 줄까지) | 이 VM. 터미널에서 `gh secret set LINUX_REPO_GPG_PRIVATE_KEY -R SosomLab/linux-repo < ~/.config/sosomlab-linux-repo/signing-private.asc`로 넣어도 된다(화면에 안 찍힘) |
| `CLOUDFLARE_API_TOKEN` | 4단계에서 만드는 토큰 | Cloudflare |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 계정 ID | Cloudflare 대시보드 → Workers & Pages 오른쪽(또는 계정 홈 URL의 32자리) |

## 4. Cloudflare — [사용자]

1. **API 토큰**: 우측 상단 프로필 → My Profile → API Tokens → Create Token → **Custom token**
   - 권한: `Account` · `Cloudflare Pages` · **Edit** (이것 하나)
   - Account Resources: Include · 해당 계정
   - 만든 토큰 문자열 → 3단계 `CLOUDFLARE_API_TOKEN`.
2. **Pages 프로젝트 만들기**: Workers & Pages → Create → **Pages** → **Use direct upload**(“Upload assets”)
   - 프로젝트 이름: **`linux-repo`**(워크플로가 이 이름으로 배포한다)
   - 처음 화면에서 파일을 올리라고 하면 빈 폴더 대신 아무 `index.html` 하나로 첫 배포를 해 두거나, 프로젝트만 만들고 닫는다(실제 내용은 CI가 올림).
   - ⚠️ Git 연결(Connect to Git) 방식이 아니다 — 서명 개인 키를 Cloudflare 빌드에 넣지 않기 위해 GitHub Actions가 서명까지 끝낸 결과만 올린다.
3. **사용자 지정 도메인**: 프로젝트 `linux-repo` → Custom domains → Set up a custom domain → `pkg.sosomlab.com`
   - `sosomlab.com`이 같은 계정의 zone이면 CNAME이 자동으로 추가된다(활성화까지 수 분).
4. **캐시 규칙 걸지 않기**: `sosomlab.com` zone의 Caching → Cache Rules에 `pkg.sosomlab.com`을 덮는 규칙이 없게 둔다(색인은 `_headers`로 `no-cache` · 옛 색인과 섞이면 apt 해시 불일치).

## 5. 첫 배포

1. [세션] 커밋 → [사용자 승인] push(`main`).
2. [사용자 또는 세션(gh)] Actions → `publish` → **Run workflow**.
3. [세션] 확인: `https://pkg.sosomlab.com/` 안내 화면 · `repo.json` · `apt/dists/stable/InRelease` · 리다이렉트(`/apt/pool/…` → GitHub 302).

## 6. 설치 시험

- [세션] 실제 도메인으로 root 없이 검증: `scripts/test_apt_local.sh`와 같은 방식(주소만 실제).
- [사용자] 이 VM에서 실제 설치(관리자 암호 필요):
  ```sh
  sudo curl -fsSLo /usr/share/keyrings/sosomlab-archive-keyring.gpg https://pkg.sosomlab.com/sosomlab-archive-keyring.gpg
  sudo curl -fsSLo /etc/apt/sources.list.d/sosomlab.sources https://pkg.sosomlab.com/apt/sosomlab.sources
  sudo apt update && sudo apt install nexa-clip
  ```
  지금 설치본(로컬 `.deb` 0.1.6 표시)이 저장소의 0.1.7로 올라간다 — 실행 중이면 앱을 한 번 재시작.

## 7. 앱 저장소와 잇기

- 앱 릴리스 끝에 발행 신호 → [ADDING-AN-APP.md](ADDING-AN-APP.md) §4. Nexa Clip은 그 저장소의 개발 세션이 `release.yml`에 넣는다.
- [사용자] `LINUX_REPO_DISPATCH_TOKEN`(fine-grained · `SosomLab/linux-repo` Contents Read/write) 발급 → `SosomLab/nexa-clip` 시크릿에 등록.
- RPM: 앱 릴리스가 `.rpm`을 만들기 시작하면 `apps/<앱>.toml`의 `[rpm]`을 켠다(생성기 RPM 경로는 아직 실기 전).
