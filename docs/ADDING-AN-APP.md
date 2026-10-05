# 앱 등록 — 다른 SosomLab 앱을 pkg.sosomlab.com에 올리는 법

> Nexa Clip이 첫 등록 앱이다(`apps/nexa-clip.toml`). 다른 앱(Beep · Dir …)도 **같은 순서**로 등록한다.

## 앱 쪽 전제

1. **GitHub Release에 `.deb`가 올라간다** — 정식 릴리스(초안·사전 배포 아님) · 자산 이름이 버전만 바뀌는 고정 규칙(예 `nexa-beep-{version}-linux-x64.deb`).
2. `.deb` 안 `Package:` 이름이 등록 파일의 `package`와 같다(apt가 이 이름으로 설치).
3. 한 번 올린 Release 자산은 **지우거나 다시 올리지 않는다**(서명된 색인의 해시가 그 파일을 가리킨다 · 바꾸면 그 버전 설치가 깨진다).
4. RPM까지 내려면 앱 릴리스가 `.rpm`도 만든다(자산 이름 규칙 동일).

## 등록 순서

1. `apps/<패키지 이름>.toml`을 만든다 — `apps/nexa-clip.toml`을 복사해 `package` · `github` · `summary` · `[deb]` 자산 규칙만 바꾼다.
2. 로컬 확인(서명 키가 있는 PC — [KEYS.md §4](KEYS.md)):
   ```sh
   python3 scripts/build_repo.py --key 2522614046FAEE116F4A2FD706236F6AA8EB8FD6
   bash scripts/test_apt_local.sh public <패키지 이름>   # 서명 검증 + 리다이렉트 내려받기 통과 확인
   ```
3. 커밋·push → Actions의 `publish`를 수동 실행(또는 다음 정기 실행).
4. 앱 저장소 release 워크플로 끝에 **발행 신호**를 단다(릴리스마다 저장소가 바로 갱신되게):
   ```yaml
   - name: pkg.sosomlab.com 갱신 신호
     if: ${{ secrets.LINUX_REPO_DISPATCH_TOKEN != '' }}
     run: |
       curl -fsS -X POST https://api.github.com/repos/SosomLab/linux-repo/dispatches \
         -H "Authorization: Bearer ${{ secrets.LINUX_REPO_DISPATCH_TOKEN }}" \
         -H "Accept: application/vnd.github+json" \
         -d '{"event_type":"app-released","client_payload":{"app":"<패키지 이름>"}}'
   ```
   `LINUX_REPO_DISPATCH_TOKEN` = `SosomLab/linux-repo`에 **Contents: Read and write**(fine-grained · dispatch에 필요) 권한만 준 토큰 · 앱 저장소 시크릿에 등록.
   신호가 없어도 하루 한 번 정기 실행이 최신 릴리스를 잡는다.
5. 사이트 `https://pkg.sosomlab.com/`의 패키지 표에 새 앱이 보이면 끝. 사용자는 저장소를 이미 등록했다면 `sudo apt install <패키지 이름>`만 하면 된다.
