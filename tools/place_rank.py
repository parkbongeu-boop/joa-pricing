"""네이버 플레이스 순위 체크 - 조아패밀리 김포점 / 비앤제이스튜디오

각 업체 플레이스에 등록된 대표키워드를 매번 새로 읽어와서
'김포 + 대표키워드'로 검색했을 때의 순위를 알려준다.

사용법: python3 tools/place_rank.py
표준 라이브러리만 사용 (설치 필요 없음)
"""
import json
import re
import urllib.request

# 순위를 볼 업체 (네이버 플레이스 ID)
STORES = {
    "조아패밀리 김포점": "1997247203",
    "비앤제이스튜디오": "10986277",
}

# 대표키워드 외에 두 업체 모두 같이 볼 공통 키워드
COMMON_KEYWORDS = ["김포 가족사진", "김포 사진관"]

# 대표키워드 앞에 붙일 지역명
REGION = "김포"

# 검색 기준 위치 (김포 풍무동)
X, Y = "126.7357", "37.6124"
MAX_RANK = 300
PAGE = 70

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
QUERY = ("query getPlaces($input: PlaceListInput) { placeList(input: $input) "
         "{ businesses { total items { id name } } } }")


def rep_keywords(place_id):
    """플레이스에 등록된 대표키워드 (최대 5개)"""
    req = urllib.request.Request(
        f"https://m.place.naver.com/place/{place_id}/home",
        headers={"user-agent": UA, "referer": "https://m.search.naver.com/"},
    )
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    m = re.search(r'"keywordList":(\[[^\]]*\])', html)
    return json.loads(m.group(1)) if m else []


def fetch(keyword, start):
    body = [{
        "operationName": "getPlaces",
        "variables": {"input": {
            "query": keyword, "start": start, "display": PAGE,
            "deviceType": "mobile", "isNx": False,
            "businessType": "place", "x": X, "y": Y,
        }},
        "query": QUERY,
    }]
    req = urllib.request.Request(
        "https://api.place.naver.com/graphql",
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "user-agent": UA,
            "referer": "https://m.place.naver.com/",
        },
    )
    data = json.loads(urllib.request.urlopen(req, timeout=20).read())
    biz = data[0]["data"]["placeList"]["businesses"]
    return biz["total"], biz["items"]


def ranks(keyword):
    found, start, total = {}, 1, None
    while start <= MAX_RANK:
        total, items = fetch(keyword, start)
        for i, item in enumerate(items):
            for name, pid in STORES.items():
                if item["id"] == pid and name not in found:
                    found[name] = start + i
        if len(found) == len(STORES) or len(items) < PAGE:
            break
        start += PAGE
    return total, found


def label(rank, total):
    if rank:
        return f"{rank}위"
    if total is not None and total <= MAX_RANK:
        return "노출 안 됨"
    return f"{MAX_RANK}위 밖"


def main():
    cache = {}

    def lookup(kw):
        if kw not in cache:
            try:
                cache[kw] = ranks(kw)
            except Exception as e:  # 한 키워드 실패해도 나머지는 계속
                cache[kw] = e
        return cache[kw]

    print("네이버 플레이스 순위 (김포 풍무동 기준)")
    for name, pid in STORES.items():
        try:
            reps = rep_keywords(pid)
        except Exception as e:
            reps = []
            print(f"\n{name} 대표키워드 조회 실패 {e}")
        print(f"\n■ {name}")
        print(f"  대표키워드 {', '.join(reps) if reps else '없음'}")
        for kw in [f"{REGION} {k}" for k in reps] + COMMON_KEYWORDS:
            res = lookup(kw)
            if isinstance(res, Exception):
                print(f"  {kw}  조회 실패 {res}")
                continue
            total, found = res
            print(f"  {kw}  {label(found.get(name), total)}  (전체 {total}곳)")


if __name__ == "__main__":
    main()
