#!/usr/bin/env python3
"""카카오톡 '나에게 보내기'로 글을 보낸다.

쓰는 법
    echo 보낼 글 | python3 tools/kakao_send.py
    python3 tools/kakao_send.py 보낼 글

열쇠는 아래 순서로 찾는다 (화면에 절대 찍지 않는다)
    1. 환경변수 KAKAO_REST_KEY · KAKAO_REFRESH_TOKEN (· KAKAO_CLIENT_SECRET)
    2. 대표님 PC 파일 %USERPROFILE%\\.kakao_token.json  (카톡열쇠받기.bat 이 만든다)

KAKAO_DRY_RUN=1 이면 보내지 않고 나눈 글만 보여 준다 (시험용).
파이썬 기본 기능만 쓴다. 설치할 것 없음.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TOKEN_FILE = Path.home() / ".kakao_token.json"
MAX_LEN = 200  # 카카오 기본 텍스트 메시지 한 번에 200자
LINK = os.environ.get("KAKAO_LINK", "https://m.naver.com")


class KakaoError(Exception):
    pass


def split_text(text, limit=MAX_LEN):
    """줄 단위로 묶어 limit 글자 이하 조각으로 나눈다. 한 줄이 길면 그 줄을 자른다."""
    chunks, cur = [], ""
    for line in text.strip().splitlines():
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        cand = f"{cur}\n{line}" if cur else line
        if len(cand) > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = cand
    if cur:
        chunks.append(cur)
    return chunks


def load_keys():
    rest = os.environ.get("KAKAO_REST_KEY")
    refresh = os.environ.get("KAKAO_REFRESH_TOKEN")
    secret = os.environ.get("KAKAO_CLIENT_SECRET")
    if rest and refresh:
        return {"rest_key": rest, "refresh_token": refresh, "client_secret": secret}, False
    if TOKEN_FILE.exists():
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        if data.get("rest_key") and data.get("refresh_token"):
            return data, True
    raise KakaoError("카톡 열쇠가 없어요 · 카톡열쇠받기를 먼저 해 주세요")


def post(url, fields, token=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode())
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {}
        return {"_http": e.code, **body}
    except urllib.error.URLError as e:
        raise KakaoError(f"카카오 서버에 연결이 안 돼요 ({e.reason}) · 네트워크 허용을 확인해 주세요")


def access_token(keys, from_file):
    fields = {"grant_type": "refresh_token", "client_id": keys["rest_key"],
              "refresh_token": keys["refresh_token"]}
    if keys.get("client_secret"):
        fields["client_secret"] = keys["client_secret"]
    res = post(TOKEN_URL, fields)
    if "access_token" not in res:
        if res.get("error") == "invalid_grant":
            raise KakaoError("카톡 열쇠가 만료됐어요 · 카톡열쇠받기를 다시 해 주세요")
        raise KakaoError(f"카톡 열쇠 갱신 실패 ({res.get('error_code') or res.get('error') or res.get('_http')})")
    # 갱신 열쇠가 새로 나오면 PC 파일에는 바꿔 저장한다 (클라우드 비밀값은 대표님이 바꿈)
    if from_file and res.get("refresh_token"):
        keys["refresh_token"] = res["refresh_token"]
        TOKEN_FILE.write_text(json.dumps(keys, ensure_ascii=False), encoding="utf-8")
    return res["access_token"]


def send(text, keys=None, from_file=False):
    chunks = split_text(text)
    if not chunks:
        raise KakaoError("보낼 글이 비어 있어요")
    if os.environ.get("KAKAO_DRY_RUN") == "1":
        for i, c in enumerate(chunks, 1):
            print(f"--- {i}/{len(chunks)} ({len(c)}자)\n{c}")
        return len(chunks)
    if keys is None:
        keys, from_file = load_keys()
    token = access_token(keys, from_file)
    for c in chunks:
        tpl = {"object_type": "text", "text": c,
               "link": {"web_url": LINK, "mobile_web_url": LINK}}
        res = post(SEND_URL, {"template_object": json.dumps(tpl, ensure_ascii=False)}, token)
        if res.get("result_code") != 0:
            raise KakaoError(f"카톡 보내기 실패 ({res.get('code') or res.get('_http')} {res.get('msg', '')})".strip())
    return len(chunks)


def read_input():
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    raw = sys.stdin.buffer.read()
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        n = send(read_input())
    except KakaoError as e:
        print(e)
        sys.exit(1)
    print(f"카톡 보냄 ({n}개)")


if __name__ == "__main__":
    main()
