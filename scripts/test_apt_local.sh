#!/usr/bin/env bash
# 배포 전 로컬 검증 — root 권한 없이 apt가 public/ 저장소를 **서명 검증 + 리다이렉트**로 끝까지 받는지 본다.
#   bash scripts/test_apt_local.sh [public] [패키지=nexa-clip]
# 시스템 apt 상태·키링은 건드리지 않는다(모든 Dir를 임시 폴더로 돌린다). 설치는 하지 않고 내려받기까지만.
set -euo pipefail
PUB="$(cd "${1:-public}" && pwd)"
PKG="${2:-nexa-clip}"
PORT=18574
W="$(mktemp -d)"
trap 'kill $SRV 2>/dev/null || true; rm -rf "$W"' EXIT
mkdir -p "$W/state/lists/partial" "$W/cache/archives/partial" "$W/get"
: > "$W/state/status"
python3 "$(dirname "$0")/serve_local.py" "$PUB" "$PORT" >"$W/srv.log" 2>&1 & SRV=$!
sleep 1
# 실제 배포와 같은 sources 파일에서 주소만 로컬로 바꾼다 · 키는 public/의 키링.
sed -e "s#https://pkg.sosomlab.com#http://127.0.0.1:$PORT#" -e "s#^Signed-By: .*#Signed-By: $PUB/sosomlab-archive-keyring.gpg#" \
  "$PUB/apt/sosomlab.sources" > "$W/sosomlab.sources"
O=(-o "Dir::State=$W/state" -o "Dir::State::Lists=$W/state/lists" -o "Dir::State::status=$W/state/status"
   -o "Dir::Cache=$W/cache" -o "Dir::Cache::pkgcache=" -o "Dir::Cache::srcpkgcache="
   -o "Dir::Etc::SourceList=/dev/null" -o "Dir::Etc::SourceParts=$W" -o "Debug::NoLocking=1")
apt-get "${O[@]}" update
(cd "$W/get" && apt-get "${O[@]}" download "$PKG")
ls -l "$W/get"
sha256sum "$W/get/"*.deb
grep -E '^(GET|"GET)|" 30[12] ' "$W/srv.log" | tail -n 8 || true
echo "OK — 서명 검증 + 리다이렉트 내려받기 통과"
