"""
직방 매물 검색 CLI 스크립트
사용법: python search_properties.py [지역명]

예시:
  python search_properties.py 망원동
  python search_properties.py "서울 마포구 망원동"
  python search_properties.py "강남구 역삼동"
"""
import requests
import csv
import time
import sys
from math import ceil

try:
    import pygeohash as pgh
except ImportError:
    print("pygeohash 설치 필요: pip install pygeohash")
    sys.exit(1)

# 직방 API 헤더
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/json',
    'origin': 'https://www.zigbang.com',
    'referer': 'https://www.zigbang.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'x-zigbang-platform': 'www',
}


def search_location(query: str) -> dict:
    """직방 API로 지역 검색하여 좌표 정보 획득"""
    url = 'https://apis.zigbang.com/v3/search'
    params = {'q': query, 'type': 'dong'}
    
    print(f'[1/5] 지역 검색 중: {query}')
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    
    if not data.get('success') or not data.get('items'):
        raise ValueError(f"'{query}' 지역을 찾을 수 없습니다.")
    
    # type이 'address'인 항목 우선 (동/구 정보)
    for item in data['items']:
        if item.get('type') == 'address':
            result = {
                'name': item.get('name'),
                'description': item.get('description'),
                'lat': item.get('lat'),
                'lng': item.get('lng'),
            }
            print(f'      → 찾음: {result["description"]} ({result["lat"]:.4f}, {result["lng"]:.4f})')
            return result
    
    # 없으면 첫 번째 결과
    item = data['items'][0]
    result = {
        'name': item.get('name'),
        'description': item.get('description'),
        'lat': item.get('lat'),
        'lng': item.get('lng'),
    }
    print(f'      → 찾음: {result["description"]} ({result["lat"]:.4f}, {result["lng"]:.4f})')
    return result


def fetch_item_ids(lat: float, lng: float, radius_km: float = 1.5) -> list:
    """지역 좌표 기준 매물 item_ids 조회"""
    url = 'https://apis.zigbang.com/v2/items/oneroom'
    
    # geohash 생성
    geohash = pgh.encode(lat, lng, precision=4)
    
    # bbox 범위 계산
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * 0.85)
    
    lat_north = lat + lat_delta
    lat_south = lat - lat_delta
    lng_east = lng + lng_delta
    lng_west = lng - lng_delta
    
    params = {
        'geohash': geohash,
        'depositMin': '0',
        'rentMin': '0',
        'salesTypes[0]': '전세',
        'salesTypes[1]': '월세',
        'latNorth': str(lat_north),
        'latSouth': str(lat_south),
        'lngEast': str(lng_east),
        'lngWest': str(lng_west),
        'domain': 'zigbang',
        'checkAnyItemWithoutFilter': 'true',
    }
    
    print(f'[2/5] 매물 ID 조회 중... (geohash: {geohash})')
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    
    items = data.get('items') if isinstance(data, dict) else data
    if not items:
        return []
    
    # bbox 범위 내의 매물만 필터링
    filtered_items = []
    for it in items:
        item_lat = it.get('lat', 0)
        item_lng = it.get('lng', 0)
        if (lat_south <= item_lat <= lat_north and 
            lng_west <= item_lng <= lng_east):
            iid = it.get('itemId') or it.get('item_id')
            if iid:
                filtered_items.append(int(iid))
    
    unique_ids = sorted(set(filtered_items))
    print(f'      → 전체 응답: {len(items)}개 / 범위 내 매물: {len(unique_ids)}개')
    return unique_ids


def fetch_details(item_ids: list, chunk_size: int = 10) -> list:
    """item_ids로 상세 정보 조회 (재시도 로직 포함)"""
    if not item_ids:
        return []
    
    url = 'https://apis.zigbang.com/house/property/v1/items/list'
    all_items = []
    total_chunks = ceil(len(item_ids) / chunk_size)
    
    print(f'[3/5] 상세 정보 조회 중... ({total_chunks}개 청크, 각 {chunk_size}개)')
    
    for idx, i in enumerate(range(0, len(item_ids), chunk_size), start=1):
        chunk = item_ids[i:i+chunk_size]
        payload = {'itemIds': chunk}
        
        # 최대 3회 재시도
        for attempt in range(1, 4):
            try:
                resp = requests.post(url, headers=HEADERS, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get('items', [])
                    all_items.extend(items)
                    print(f'      청크 {idx}/{total_chunks}: {len(items)}개')
                    break
                elif resp.status_code in (429, 500, 502, 503, 504):
                    # 서버 오류는 재시도
                    if attempt < 3:
                        time.sleep(1 * attempt)
                        continue
                    print(f'      청크 {idx}/{total_chunks}: 실패 (HTTP {resp.status_code})')
                else:
                    print(f'      청크 {idx}/{total_chunks}: 실패 (HTTP {resp.status_code})')
                    break
            except Exception as e:
                if attempt < 3:
                    time.sleep(1 * attempt)
                    continue
                print(f'      청크 {idx}/{total_chunks}: 오류 - {e}')
        
        time.sleep(1.0)  # API 부하 방지
    
    print(f'[4/5] 상세 정보 수집 완료: {len(all_items)}개')
    return all_items


def parse_item(item: dict) -> dict:
    """매물 정보 파싱"""
    item_id = item.get('item_id') or item.get('id') or item.get('itemId')
    addr_orig = item.get('addressOrigin') or {}
    address = item.get('address') or addr_orig.get('fullText', '')
    
    size_m2 = item.get('size_m2')
    if not size_m2:
        size_m2 = (item.get('전용면적') or {}).get('m2') or (item.get('공급면적') or {}).get('m2')
    
    location = item.get('location') or item.get('random_location') or {}
    
    return {
        'item_id': item_id,
        'title': item.get('title'),
        'address': address,
        'local1': addr_orig.get('local1', ''),
        'local2': addr_orig.get('local2', ''),
        'local3': addr_orig.get('local3', ''),
        'deposit': item.get('deposit'),
        'rent': item.get('rent'),
        'size_m2': size_m2,
        'floor': item.get('floor'),
        'service_type': item.get('service_type') or item.get('serviceType'),
        'manage_cost': item.get('manage_cost') or item.get('manageCost'),
        'lat': location.get('lat') or item.get('lat'),
        'lng': location.get('lng') or item.get('lng'),
        'thumbnail': item.get('images_thumbnail'),
    }


def save_csv(items: list, filename: str):
    """CSV 파일 저장"""
    if not items:
        print('저장할 매물이 없습니다.')
        return
    
    parsed = [parse_item(it) for it in items]
    
    fieldnames = [
        'item_id', 'title', 'address', 'local1', 'local2', 'local3',
        'deposit', 'rent', 'size_m2', 'floor', 'service_type', 'manage_cost',
        'lat', 'lng', 'thumbnail'
    ]
    
    print(f'[5/5] CSV 저장 중: {filename}')
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in parsed:
            writer.writerow({k: p.get(k, '') for k in fieldnames})
    
    print(f'\n✅ 완료! {len(parsed)}개 매물 저장됨')
    print(f'   파일: {filename}')


def main():
    print('=' * 50)
    print('  직방 매물 검색 CLI')
    print('=' * 50)
    
    # 지역명 입력 받기
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        print('\n지역명을 입력하세요 (예: 망원동, 강남구 역삼동)')
        query = input('지역명: ').strip()
    
    if not query:
        print('지역명을 입력해주세요.')
        return
    
    print()
    
    try:
        # 1. 지역 검색
        location = search_location(query)
        
        # 2. 매물 ID 조회 (반경 1.5km)
        item_ids = fetch_item_ids(location['lat'], location['lng'], radius_km=1.5)
        
        if not item_ids:
            print('\n❌ 해당 지역에서 매물을 찾지 못했습니다.')
            return
        
        # 3. 상세 정보 조회
        items = fetch_details(item_ids)
        
        # 4. CSV 저장
        safe_name = location['description'].replace(' ', '_')
        filename = f'zigbang_{safe_name}.csv'
        save_csv(items, filename)
        
    except ValueError as e:
        print(f'\n❌ 오류: {e}')
    except Exception as e:
        print(f'\n❌ 오류 발생: {e}')


if __name__ == '__main__':
    main()
