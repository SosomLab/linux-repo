# 서명 키 — 위치 · 백업 · 다른 PC로 옮기기 · 갱신 · 폐기

> pkg.sosomlab.com의 APT(·RPM) 색인을 서명하는 GPG 키. **개인 키가 새면 누구나 우리 이름으로 가짜 패키지 색인을 만들 수 있다** — 이 문서대로만 다룬다.

## 1. 지금 키

| 항목 | 값 |
|---|---|
| 지문 | `2522614046FAEE116F4A2FD706236F6AA8EB8FD6` |
| 짧은 ID | `06236F6AA8EB8FD6` |
| 사용자 ID | `SosomLab Linux Repository (pkg.sosomlab.com) <kiros33@sosomlab.com>` |
| 종류 | RSA 4096 · 서명 전용 · **비밀번호 없음**(CI 자동 서명용 — 대신 보관을 엄격히) |
| 만든 날 · 만료 | 2026-10-05 · **2028-10-04**(만료 전 연장 — §5) |
| 만든 곳 | Linux VM(`~/.gnupg` 키링) |

RSA를 고른 이유: RPM 쪽(구형 rpm 4.14 · RHEL 8 계열)이 Ed25519 서명을 못 읽는다.

## 2. 파일 위치(만든 PC)

`~/.config/sosomlab-linux-repo/`(폴더·파일 권한 600 · 저장소 밖)

| 파일 | 무엇 | 비밀 |
|---|---|---|
| `signing-private.asc` | **개인 키**(armor) — GitHub 시크릿 `LINUX_REPO_GPG_PRIVATE_KEY`에 이 파일 전문을 넣는다 | 🔴 비밀 |
| `revocation-cert.rev` | **폐기 인증서** — 키를 잃거나 샜을 때 폐기 선언용 | 🔴 비밀(쓰면 키가 즉시 무효) |
| `signing-public.asc` | 공개 키(armor) | 공개 |
| `sosomlab-archive-keyring.gpg` | 공개 키(바이너리 · apt용) — 사이트에 같은 이름으로 실린다 | 공개 |
| `fingerprint.txt` | 지문 | 공개 |

키링 자체도 `~/.gnupg`에 들어 있다(`gpg --list-secret-keys pkg.sosomlab.com`).

## 3. 백업(지금 한 번 · 사용자)

1. `signing-private.asc`와 `revocation-cert.rev` **두 파일**을 비밀번호 관리자(보안 메모 첨부) 또는 암호화한 외장 저장소에 넣는다.
2. 두 파일을 **같은 곳에만 두지 않는다**(폐기 인증서는 키를 잃었을 때 쓰는 것이라 따로 보관이 원칙).
3. 클라우드 동기화 폴더·메일·메신저·저장소에는 **평문으로 두지 않는다**.

## 4. 다른 PC에서 쓰기(로컬 서명이 필요할 때만)

평소 서명은 **CI(GitHub Actions)** 가 하므로 다른 PC에 키가 꼭 있어야 하는 것은 아니다. 로컬에서 `scripts/build_repo.py`를 돌려 볼 때만 옮긴다.

```sh
# 옮길 PC에서(백업한 signing-private.asc를 안전한 경로로 가져온 뒤)
gpg --batch --import signing-private.asc
gpg --list-secret-keys --keyid-format long pkg.sosomlab.com   # 지문 2522…8FD6 확인
shred -u signing-private.asc                                     # 가져온 뒤 평문 파일은 지운다(mac은 rm -P)
# 필요하면 신뢰 표시(서명만 할 거면 없어도 된다)
echo "2522614046FAEE116F4A2FD706236F6AA8EB8FD6:6:" | gpg --import-ownertrust
```

- 복사 경로: USB(암호화) · `scp`(SSH) · 비밀번호 관리자 첨부. **메일·메신저·공유 드라이브 평문 금지.**
- mac: `brew install gnupg` 뒤 같은 명령. Windows: Gpg4win의 `gpg` 같은 명령.

## 5. 만료 연장(2028-10 전 · 사용자 또는 세션)

만료되면 apt가 서명을 거부한다(`EXPKEYSIG`) → **만료 한두 달 전에 연장**하고 공개 키를 다시 배포한다.

```sh
gpg --quick-set-expire 2522614046FAEE116F4A2FD706236F6AA8EB8FD6 2y
gpg --armor --export-secret-keys 2522614046FAEE116F4A2FD706236F6AA8EB8FD6 > signing-private.asc   # → 시크릿 갱신
```

공개 키는 다음 발행 때 CI가 사이트에 새로 싣는다. 사용자는 키 파일을 다시 받아야 한다(`/usr/share/keyrings/sosomlab-archive-keyring.gpg` 덮어쓰기 — 사이트 안내 1줄).

## 6. 키가 샜거나 잃었을 때

1. 새 키를 만든다(이 문서 §1 조건 · `gpg --batch --gen-key`).
2. GitHub 시크릿을 새 개인 키로 바꾸고 publish를 수동 실행 → 사이트에 새 공개 키가 실린다.
3. 옛 키는 폐기: `gpg --import revocation-cert.rev` 뒤 공개 키를 내보내 사이트 공지(사용자에게 키 파일 재설치 안내).
