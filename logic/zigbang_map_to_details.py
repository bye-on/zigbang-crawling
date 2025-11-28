import requests
import csv
import time
import sys
from math import ceil
from zigbang_items_fetch import parse_item

HEADERS_GET = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
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

HEADERS_POST = HEADERS_GET.copy()
HEADERS_POST.update({'content-type': 'application/json'})


def map_query(bbox_params: dict):
    """지도 API(v2/items/oneroom)로 bbox를 주고 itemId 목록(및 좌표)을 받음."""
    url = 'https://apis.zigbang.com/v2/items/oneroom'
    resp = requests.get(url, params=bbox_params,
                        headers=HEADERS_GET, timeout=15)
    resp.raise_for_status()
    j = resp.json()
    items = j.get('items') if isinstance(j, dict) else j
    if not items:
        return []
    results = []
    for it in items:
        # API 응답 샘플: {lat, lng, itemId, itemBmType}
        iid = it.get('itemId') or it.get('item_id')
        if not iid:
            continue
        results.append(
            {'itemId': int(iid), 'lat': it.get('lat'), 'lng': it.get('lng')})
    return results


def fetch_details_by_ids(item_ids, chunk_size=15, max_retries=3, delay_between_chunks=1.0):
    """POST /house/property/v1/items/list로 상세정보를 받아옴 (chunk 처리).

    - chunk_size: 한 번에 전송할 itemId 수
    - max_retries: 실패 시 재시도 횟수
    - delay_between_chunks: 청크 사이 대기 시간(초)
    """
    url = 'https://apis.zigbang.com/house/property/v1/items/list'
    all_items = []
    total_chunks = ceil(len(item_ids) / chunk_size) if item_ids else 0
    for idx, i in enumerate(range(0, len(item_ids), chunk_size), start=1):
        chunk = item_ids[i:i+chunk_size]
        payload = {'itemIds': chunk}
        resp = None
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    url, headers=HEADERS_POST, json=payload, timeout=25)
            except Exception as e:
                print(f'    청크 {idx}/{total_chunks} 요청 오류 (시도 {attempt}): {e}')
                if attempt < max_retries:
                    time.sleep(1 * attempt)
                    continue
                else:
                    break

            if resp.status_code == 200:
                success = True
                break
            # 5xx나 429는 재시도
            if resp.status_code in (429, 500, 502, 503, 504):
                print(
                    f'    청크 {idx}/{total_chunks} 서버 오류 {resp.status_code} (시도 {attempt}) - 재시도')
                if attempt < max_retries:
                    time.sleep(1 * attempt)
                    continue
                else:
                    break
            # 기타 4xx는 재시도하지 않음
            print(
                f'    청크 {idx}/{total_chunks} 요청 실패: HTTP {resp.status_code} - 응답: {resp.text[:200]}')
            break

        if not success:
            print(f'    청크 {idx}/{total_chunks} 실패로 건너뜁니다')
            time.sleep(delay_between_chunks)
            continue

        try:
            data = resp.json()
        except Exception as e:
            print(f'    청크 {idx}/{total_chunks} JSON 파싱 실패: {e}')
            time.sleep(delay_between_chunks)
            continue

        items = data.get('items', [])
        all_items.extend(items)
        print(f'  상세 청크 {idx}/{total_chunks} 가져옴: {len(items)} 항목')
        time.sleep(delay_between_chunks)

    return all_items


def save_parsed_items(parsed_items, out_path='zigbang_map_details.csv'):
    if not parsed_items:
        print('저장할 항목이 없습니다.')
        return
    fieldnames = ['item_id', 'address', 'deposit', 'rent',
                  'manage_cost', 'service_type', 'size_m2', 'lat', 'lng']
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for it in parsed_items:
            writer.writerow({k: it.get(k, '') for k in fieldnames})
    print(f'저장 완료: {out_path} (항목 수: {len(parsed_items)})')


def main():
    # 간단한 CLI: 네 개의 좌표를 args로 받거나, 기본 샘플 bbox 사용
    if len(sys.argv) == 5:
        lngEast, lngWest, latSouth, latNorth = sys.argv[1:5]
        params = {
            'lngEast': lngEast,
            'lngWest': lngWest,
            'latSouth': latSouth,
            'latNorth': latNorth,
            'domain': 'zigbang',
            'checkAnyItemWithoutFilter': 'true',
            'depositMin': '0',
            'rentMin': '0',
        }
    else:
        print('사용법: python zigbang_map_to_details.py <lngEast> <lngWest> <latSouth> <latNorth>')
        print('샘플 bbox로 실행합니다 (사용자 제공 예시)')
        params = {
            'geohash': 'wydj',
            'depositMin': '0',
            'rentMin': '0',
            'salesTypes[0]': '전세',
            'salesTypes[1]': '월세',
            'lngEast': '126.91202684097959',
            'lngWest': '126.89079894874561',
            'latSouth': '37.547755583927504',
            'latNorth': '37.568063759615704',
            'domain': 'zigbang',
            'checkAnyItemWithoutFilter': 'true',
        }

    print('지도 API로 itemId 수집 중...')
    map_items = map_query(params)
    if not map_items:
        print('지도 API에서 item을 찾지 못했습니다.')
        return

    # 고유한 itemId 추출
    unique_ids = sorted({it['itemId'] for it in map_items})
    print(f'수집된 itemId 수: {len(unique_ids)}')

    # 상세 정보 요청
    detailed = fetch_details_by_ids(unique_ids)
    # parse_item으로 평탄화
    parsed = [parse_item(it) for it in detailed]

    # map에서 받은 좌표를 parsed에 병합(아이디 기준)
    coord_map = {it['itemId']: (it.get('lat'), it.get('lng'))
                 for it in map_items}
    for p in parsed:
        iid = p.get('item_id')
        if iid in coord_map:
            lat, lng = coord_map[iid]
            p['lat'] = p.get('lat') or lat
            p['lng'] = p.get('lng') or lng

    save_parsed_items(parsed)


if __name__ == '__main__':
    main()
