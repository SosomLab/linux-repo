#!/usr/bin/env python3
"""로컬 시험용 서버 — public/을 서빙하고 `_redirects`(정확 일치 줄만)를 Cloudflare Pages처럼 흉내 낸다.

사용: python3 scripts/serve_local.py [public] [포트=18574]
배포 전에 apt가 서명 검증·리다이렉트를 끝까지 통과하는지 확인하는 용도(scripts/test_apt_local.sh).
"""

import http.server
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "public").resolve()
port = int(sys.argv[2]) if len(sys.argv) > 2 else 18574
rules = {}
for line in (root / "_redirects").read_text().splitlines():
    parts = line.split()
    if len(parts) >= 2 and not line.lstrip().startswith("#"):
        rules[parts[0]] = (parts[1], int(parts[2]) if len(parts) > 2 else 302)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(root), **k)

    def do_GET(self):
        if self.path in rules:
            dest, code = rules[self.path]
            self.send_response(code)
            self.send_header("Location", dest)
            self.end_headers()
            return
        super().do_GET()


http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
