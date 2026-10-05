# 앱 등록 — 다른 SosomLab 앱을 pkg.sosomlab.com에 올리는 법

> Nexa Clip이 첫 등록 앱이다(`apps/nexa-clip.toml`). 다른 앱(Beep · Dir …)도 **같은 순서**로 등록한다.

## 앱 쪽 전제

1. **GitHub Release에 `.deb`가 올라간다** — 정식 릴리스(초안·사전 배포 아님) · 자산 이름이 버전만 바뀌는 고정 규칙(예 `nexa-beep-{version}-linux-x64.deb`).
2. `.deb` 안 `Package:` 이름이 등록 파일의 `package`와 같다(apt가 이 이름으로 설치).
3. 한 번 올린 Release 자산은 **지우거나 다시 올리지 않는다**(서명된 색인의 해시가 그 파일을 가리킨다 · 바꾸면 그 버전 설치가 깨진다).
4. RPM까지 내려면 앱 릴리스가 `.rpm`도 만들고(자산 이름 규칙 동일 · `.rpm` 안 `Name:` = `package`) 등록 파일에 `[rpm]`을 둔다. `[rpm]` 자산이 릴리스에 없으면 생성기는 경고만 하고 건너뛴다(`[deb]` 자산이 없으면 실패).

## 등록 순서

1. `apps/<패키지 이름>.toml`을 만든다 — `apps/nexa-clip.toml`을 복사해 `package` · `github` · `summary` · `[deb]` 자산 규칙만 바꾼다.
2. 로컬 확인(서명 키가 있는 PC — [KEYS.md §4](KEYS.md)):
   ```sh
   python3 scripts/build_repo.py --key 2522614046FAEE116F4A2FD706236F6AA8EB8FD6
   bash scripts/test_apt_local.sh public <패키지 이름>   # 서명 검증 + 리다이렉트 내려받기 통과 확인
   ```
3. 커밋·push → Actions의 `publish`를 수동 실행(또는 다음 정기 실행).
4. 앱 저장소 release 워크플로 끝에 **발행 신호** 잡을 단다(릴리스가 **공개된 뒤** 저장소가 바로 갱신되게):
   ```yaml
     linux-repo:
       needs: [meta, publish]            # 릴리스 공개 잡 뒤 — 앱 워크플로의 잡 이름에 맞춘다
       if: github.ref_type == 'tag' && needs.meta.outputs.prerelease != 'true'
       runs-on: ubuntu-latest
       steps:
         - name: pkg.sosomlab.com 갱신 신호
           env:
             TOKEN: ${{ secrets.LINUX_REPO_DISPATCH_TOKEN }}
           run: |
             if [ -z "$TOKEN" ]; then echo "::notice::LINUX_REPO_DISPATCH_TOKEN 없음 — 정기 실행이 반영"; exit 0; fi
             curl -fsS -X POST https://api.github.com/repos/SosomLab/linux-repo/dispatches \
               -H "Authorization: Bearer $TOKEN" \
               -H "Accept: application/vnd.github+json" \
               -d "{\"event_type\":\"app-released\",\"client_payload\":{\"app\":\"<패키지 이름>\",\"tag\":\"$GITHUB_REF_NAME\",\"repo\":\"$GITHUB_REPOSITORY\",\"run_url\":\"$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID\"}}"
   ```
   `client_payload`는 linux-repo `publish` 실행의 **요청 기록**(Summary)에 그대로 남는다 — 누가(`repo` · `run_url`) 무엇을(`app` · `tag`) 요청했는지. 실행 이름에도 `app` · `tag`가 붙는다. 같은 실행의 **진행 기록**에서 단계별 결과와 버전 변화를 본다.
   ⚠️ 스텝 `if:`에서는 `secrets`를 읽을 수 없다(워크플로 전체가 문법 오류) — 그래서 토큰 유무는 셸에서 본다.
   `LINUX_REPO_DISPATCH_TOKEN` = `SosomLab/linux-repo`에 **Contents: Read and write**(fine-grained · dispatch에 필요) 권한만 준 토큰 · 앱 저장소 시크릿에 등록.
   토큰 확인(로컬): `read -rs T; curl -s -o /dev/null -w '%{http_code}\n' -X POST -H "Authorization: Bearer $T" -H "Accept: application/vnd.github+json" https://api.github.com/repos/SosomLab/linux-repo/dispatches -d '{"event_type":"app-released"}'` → `204`면 정상(linux-repo의 publish가 한 번 돈다).
   신호가 없어도 하루 한 번 정기 실행이 최신 릴리스를 잡는다.
5. 사이트 `https://pkg.sosomlab.com/`의 패키지 표에 새 앱이 보이면 끝. 사용자는 저장소를 이미 등록했다면 `sudo apt install <패키지 이름>`만 하면 된다.
