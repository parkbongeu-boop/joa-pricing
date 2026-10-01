"""네이버 플레이스 순위 체크 - 조아패밀리 김포점 / 비앤제이스튜디오

사용법: python3 tools/place_rank.py
표준 라이브러리만 사용 (설치 필요 없음)
"""
import json
import urllib.request

# 순위를 볼 업체 (네이버 플레이스 ID)
STORES = {
    "조아패밀리 김포점": "1997247203",
    "비앤제이스튜디오": "10986277",
}

# 순위를 볼 검색 키워드
KEYWORDS = [
    "김포 가족사진",
    "김포 아기사진",
    "김포 사진관",
    "김포 돌사진",
    "김포 백일사진",
    "풍무동 사진관",
]

# 검색 기준 위치 (김포 풍무동)
X, Y = "126.7357", "37.6124"
MAX_RANK = 300
PAGE = 70

QUERY = ("query getPlaces($input: PlaceListInput) { placeList(input: $input) "
         "{ businesses { total items { id name } } } }")


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
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
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


def main():
    print("네이버 플레이스 순위")
    for kw in KEYWORDS:
        try:
            total, found = ranks(kw)
        except Exception as e:  # 한 키워드 실패해도 나머지는 계속
            print(f"\n[{kw}] 조회 실패 {e}")
            continue
        print(f"\n[{kw}] 전체 {total}곳")
        for name in STORES:
            r = found.get(name)
            if r:
                label = f"{r}위"
            elif total <= MAX_RANK:
                label = "노출 안 됨"
            else:
                label = f"{MAX_RANK}위 밖"
            print(f"  {name}  {label}")


if __name__ == "__main__":
    main()
