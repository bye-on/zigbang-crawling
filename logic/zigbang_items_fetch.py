import requests
import csv
import sys

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/json',
    'origin': 'https://www.zigbang.com',
    'priority': 'u=1, i',
    'referer': 'https://www.zigbang.com/',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'x-zigbang-platform': 'www',
}


def fetch_items(item_ids):
    """POST 요청으로 여러 itemId의 상세 정보를 가져옵니다.

    반환값: API가 반환한 items 목록 (리스트 of dict)
    """
    url = 'https://apis.zigbang.com/house/property/v1/items/list'
    payload = {'itemIds': item_ids}

    resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get('items', [])


def parse_item(item: dict) -> dict:
    """응답 아이템에서 필요한 필드를 추출하여 평탄화합니다."""
    # 사용자 요청 필드: 매물 id, 주소, 보증금, 월세, 관리비, 매물 정보(타입), 위도, 경도
    item_id = item.get('item_id') or item.get('id') or item.get('itemId')
    address = item.get('address') or (item.get('address1') or (
        item.get('addressOrigin') or {}).get('fullText'))
    deposit = item.get('deposit')
    rent = item.get('rent')
    manage_cost = item.get('manage_cost') or item.get('manageCost')
    service_type = item.get('service_type') or item.get(
        'serviceType') or item.get('service')
    # 면적: 우선 'size_m2' 사용, 없으면 '전용면적'.m2 또는 '공급면적'.m2
    size_m2 = item.get('size_m2')
    if not size_m2:
        size_m2 = (item.get('전용면적') or {}).get(
            'm2') or (item.get('공급면적') or {}).get('m2')

    lat = (item.get('location') or {}).get('lat') or (
        item.get('random_location') or {}).get('lat') or item.get('lat')
    lng = (item.get('location') or {}).get('lng') or (
        item.get('random_location') or {}).get('lng') or item.get('lng')
    # Extract addressOrigin subfields into separate keys
    addr_orig = item.get('addressOrigin') or {}
    local1 = addr_orig.get('local1', '')
    local2 = addr_orig.get('local2', '')
    local3 = addr_orig.get('local3', '')
    address2 = addr_orig.get('address2', '')
    localText = addr_orig.get('localText', '')
    fullText = addr_orig.get('fullText', '')

    return {
        'item_id': item_id,
        'title': item.get('title'),
        'address': address,
        'local1': local1,
        'local2': local2,
        'local3': local3,
        'address2': address2,
        'localText': localText,
        'fullText': fullText,
        'deposit': deposit,
        'rent': rent,
        'size_m2': size_m2,
        'floor': item.get('floor'),
        'service_type': service_type,
        'manage_cost': manage_cost,
        'lat': lat,
        'lng': lng,
        'thumbnail': item.get('images_thumbnail'),
    }


def save_to_csv(items: list, out_path: str):
    if not items:
        print('저장할 항목이 없습니다.')
        return

    fieldnames = [
        'item_id', 'title', 'address',
        'local1', 'local2', 'local3', 'address2', 'localText', 'fullText',
        'deposit', 'rent', 'size_m2', 'floor', 'service_type', 'manage_cost',
        'lat', 'lng', 'thumbnail'
    ]
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for it in items:
            writer.writerow({k: it.get(k) for k in fieldnames})

    print(f'저장 완료: {out_path} (항목 수: {len(items)})')


def main():
    # 예시 itemIds(요청자 제공 샘플)
    item_ids = [
        46893661,
        46979712,
        47038095,
        47038075,
        47051364,
        47037322,
        47039228,
        46952994,
        47023277,
        46992009,
        47052853,
        46942681,
        46960595,
        47001382,
        47058889,
    ]

    try:
        raw_items = fetch_items(item_ids)
    except requests.HTTPError as e:
        print(f'API 요청 실패: {e} (상세: {getattr(e, "response", None)})')
        sys.exit(1)
    except Exception as e:
        print(f'요청 중 오류 발생: {e}')
        sys.exit(1)

    parsed = [parse_item(it) for it in raw_items]
    save_to_csv(parsed, 'zigbang_items.csv')


if __name__ == '__main__':
    main()
