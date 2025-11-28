"""
서울시 전체 동 매물 검색 스크립트
모든 동을 순회하며 매물 정보를 CSV로 저장
"""
import requests
import csv
import time
import sys
import os
from math import ceil
from datetime import datetime

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

# 서울시 구별 동 목록
SEOUL_DISTRICTS = {
    '강남구': ['개포동', '논현동', '대치동', '도곡동', '삼성동', '세곡동', '수서동', '신사동', '압구정동', '역삼동', '율현동', '일원동', '자곡동', '청담동'],
    '강동구': ['강일동', '고덕동', '길동', '둔촌동', '명일동', '상일동', '성내동', '암사동', '천호동'],
    '강북구': ['미아동', '번동', '수유동', '우이동'],
    '강서구': ['가양동', '개화동', '공항동', '과해동', '내발산동', '등촌동', '마곡동', '방화동', '염창동', '오곡동', '오쇠동', '외발산동', '화곡동'],
    '관악구': ['남현동', '봉천동', '신림동'],
    '광진구': ['광장동', '구의동', '군자동', '능동', '자양동', '중곡동', '화양동'],
    '구로구': ['가리봉동', '개봉동', '고척동', '구로동', '궁동', '신도림동', '오류동', '온수동', '천왕동', '항동'],
    '금천구': ['가산동', '독산동', '시흥동'],
    '노원구': ['공릉동', '상계동', '월계동', '중계동', '하계동'],
    '도봉구': ['도봉동', '방학동', '쌍문동', '창동'],
    '동대문구': ['답십리동', '신설동', '용두동', '이문동', '장안동', '전농동', '제기동', '청량리동', '회기동', '휘경동'],
    '동작구': ['노량진동', '대방동', '동작동', '본동', '사당동', '상도동', '신대방동', '흑석동'],
    '마포구': ['공덕동', '구수동', '노고산동', '당인동', '대흥동', '도화동', '동교동', '마포동', '망원동', '상수동', '상암동', '서교동', '성산동', '신공덕동', '신수동', '신정동', '아현동', '연남동', '염리동', '용강동', '중동', '창전동', '토정동', '합정동', '현석동'],
    '서대문구': ['남가좌동', '냉천동', '대신동', '대현동', '미근동', '봉원동', '북가좌동', '북아현동', '신촌동', '연희동', '영천동', '옥천동', '창천동', '천연동', '충정로', '합동', '현저동', '홍은동', '홍제동'],
    '서초구': ['내곡동', '반포동', '방배동', '서초동', '신원동', '양재동', '염곡동', '우면동', '원지동', '잠원동'],
    '성동구': ['금호동', '도선동', '마장동', '사근동', '상왕십리동', '성수동', '송정동', '옥수동', '용답동', '응봉동', '하왕십리동', '행당동', '홍익동'],
    '성북구': ['길음동', '돈암동', '동선동', '동소문동', '보문동', '삼선동', '상월곡동', '석관동', '성북동', '안암동', '장위동', '정릉동', '종암동', '하월곡동'],
    '송파구': ['가락동', '거여동', '마천동', '문정동', '방이동', '삼전동', '석촌동', '송파동', '신천동', '오금동', '잠실동', '장지동', '풍납동'],
    '양천구': ['목동', '신월동', '신정동'],
    '영등포구': ['당산동', '대림동', '도림동', '문래동', '신길동', '양평동', '여의도동', '영등포동'],
    '용산구': ['갈월동', '남영동', '동빙고동', '동자동', '문배동', '보광동', '산천동', '서계동', '서빙고동', '신계동', '신창동', '용문동', '용산동', '원효로', '이촌동', '이태원동', '주성동', '청암동', '청파동', '한강로', '한남동', '효창동', '후암동'],
    '은평구': ['갈현동', '구산동', '녹번동', '대조동', '불광동', '수색동', '신사동', '역촌동', '응암동', '증산동', '진관동'],
    '종로구': ['가회동', '견지동', '경운동', '계동', '공평동', '관수동', '관철동', '교남동', '교북동', '구기동', '궁정동', '권농동', '낙원동', '내수동', '내자동', '누상동', '누하동', '당주동', '도렴동', '돈의동', '동숭동', '명륜동', '묘동', '무악동', '봉익동', '부암동', '사간동', '사직동', '삼청동', '서린동', '세종로', '소격동', '송월동', '송현동', '수송동', '숭인동', '신교동', '신문로', '신영동', '안국동', '연건동', '연지동', '예지동', '옥인동', '와룡동', '운니동', '원남동', '원서동', '이화동', '익선동', '인사동', '인의동', '장사동', '재동', '적선동', '종로', '중학동', '창성동', '창신동', '청운동', '청진동', '체부동', '충신동', '통의동', '통인동', '팔판동', '평동', '평창동', '필운동', '행촌동', '혜화동', '홍지동', '홍파동', '화동', '효자동', '효제동', '훈정동'],
    '중구': ['광희동', '남대문로', '남산동', '남창동', '남학동', '다동', '만리동', '명동', '무교동', '무학동', '묵정동', '방산동', '봉래동', '북창동', '산림동', '삼각동', '서소문동', '소공동', '수표동', '수하동', '순화동', '신당동', '쌍림동', '예관동', '예장동', '오장동', '을지로동', '인현동', '입정동', '장교동', '장충동', '저동', '정동', '주교동', '주자동', '중림동', '초동', '충무로', '충정로', '태평로', '필동', '황학동', '회현동', '흥인동'],
    '중랑구': ['망우동', '면목동', '묵동', '상봉동', '신내동', '중화동'],
}


def search_location(query: str) -> dict:
    """직방 API로 지역 검색"""
    url = 'https://apis.zigbang.com/v3/search'
    params = {'q': query, 'type': 'dong'}
    
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    
    if not data.get('success') or not data.get('items'):
        return None
    
    for item in data['items']:
        if item.get('type') == 'address':
            return {
                'name': item.get('name'),
                'description': item.get('description'),
                'lat': item.get('lat'),
                'lng': item.get('lng'),
            }
    
    item = data['items'][0]
    return {
        'name': item.get('name'),
        'description': item.get('description'),
        'lat': item.get('lat'),
        'lng': item.get('lng'),
    }


def fetch_item_ids(lat: float, lng: float, radius_km: float = 1.0) -> list:
    """지역 좌표 기준 매물 item_ids 조회"""
    url = 'https://apis.zigbang.com/v2/items/oneroom'
    
    geohash = pgh.encode(lat, lng, precision=4)
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
    
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    
    items = data.get('items') if isinstance(data, dict) else data
    if not items:
        return []
    
    filtered_items = []
    for it in items:
        item_lat = it.get('lat', 0)
        item_lng = it.get('lng', 0)
        if (lat_south <= item_lat <= lat_north and 
            lng_west <= item_lng <= lng_east):
            iid = it.get('itemId') or it.get('item_id')
            if iid:
                filtered_items.append(int(iid))
    
    return sorted(set(filtered_items))


def fetch_details(item_ids: list, chunk_size: int = 10) -> list:
    """item_ids로 상세 정보 조회"""
    if not item_ids:
        return []
    
    url = 'https://apis.zigbang.com/house/property/v1/items/list'
    all_items = []
    
    for i in range(0, len(item_ids), chunk_size):
        chunk = item_ids[i:i+chunk_size]
        payload = {'itemIds': chunk}
        
        for attempt in range(1, 4):
            try:
                resp = requests.post(url, headers=HEADERS, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get('items', [])
                    all_items.extend(items)
                    break
                elif resp.status_code in (429, 500, 502, 503, 504):
                    if attempt < 3:
                        time.sleep(1 * attempt)
                        continue
                else:
                    break
            except Exception:
                if attempt < 3:
                    time.sleep(1 * attempt)
                    continue
        
        time.sleep(0.8)
    
    return all_items


def parse_item(item: dict, gu: str, dong: str) -> dict:
    """매물 정보 파싱"""
    item_id = item.get('item_id') or item.get('id') or item.get('itemId')
    addr_orig = item.get('addressOrigin') or {}
    address = item.get('address') or addr_orig.get('fullText', '')
    
    size_m2 = item.get('size_m2')
    if not size_m2:
        size_m2 = (item.get('전용면적') or {}).get('m2') or (item.get('공급면적') or {}).get('m2')
    
    location = item.get('location') or item.get('random_location') or {}
    
    return {
        'search_gu': gu,
        'search_dong': dong,
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


def main():
    print('=' * 60)
    print('  서울시 전체 동 매물 검색')
    print('=' * 60)
    
    # 출력 디렉토리
    output_dir = 'seoul_data'
    os.makedirs(output_dir, exist_ok=True)
    
    # 전체 매물 저장용
    all_items = []
    all_item_ids = set()  # 중복 제거용
    
    # 통계
    total_dongs = sum(len(dongs) for dongs in SEOUL_DISTRICTS.values())
    processed = 0
    success_count = 0
    fail_count = 0
    
    print(f'\n총 {len(SEOUL_DISTRICTS)}개 구, {total_dongs}개 동 검색 시작...\n')
    
    for gu, dongs in SEOUL_DISTRICTS.items():
        print(f'\n[{gu}] ({len(dongs)}개 동)')
        print('-' * 40)
        
        gu_items = []
        
        for dong in dongs:
            processed += 1
            query = f"서울 {gu} {dong}"
            
            try:
                # 1. 지역 검색
                location = search_location(query)
                if not location:
                    print(f'  {dong}: ❌ 지역 못찾음')
                    fail_count += 1
                    continue
                
                # 2. 매물 ID 조회
                item_ids = fetch_item_ids(location['lat'], location['lng'], radius_km=1.0)
                
                # 중복 제거
                new_ids = [iid for iid in item_ids if iid not in all_item_ids]
                
                if not new_ids:
                    print(f'  {dong}: 0개 (중복 제외)')
                    success_count += 1
                    continue
                
                # 3. 상세 정보 조회
                items = fetch_details(new_ids)
                
                # 파싱 및 저장
                for it in items:
                    parsed = parse_item(it, gu, dong)
                    gu_items.append(parsed)
                    all_items.append(parsed)
                    all_item_ids.add(parsed['item_id'])
                
                print(f'  {dong}: {len(items)}개 ({processed}/{total_dongs})')
                success_count += 1
                
            except Exception as e:
                print(f'  {dong}: ❌ 오류 - {e}')
                fail_count += 1
            
            time.sleep(0.5)
        
        # 구별 CSV 저장
        if gu_items:
            gu_filename = os.path.join(output_dir, f'zigbang_{gu}.csv')
            save_csv(gu_items, gu_filename)
            print(f'  → {gu} 저장: {len(gu_items)}개')
    
    # 전체 CSV 저장
    print('\n' + '=' * 60)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    all_filename = os.path.join(output_dir, f'zigbang_서울_전체_{timestamp}.csv')
    save_csv(all_items, all_filename)
    
    print(f'\n✅ 완료!')
    print(f'   - 검색 성공: {success_count}개 동')
    print(f'   - 검색 실패: {fail_count}개 동')
    print(f'   - 총 매물 수: {len(all_items)}개')
    print(f'   - 전체 파일: {all_filename}')
    print(f'   - 구별 파일: {output_dir}/ 폴더')


def save_csv(items: list, filename: str):
    """CSV 파일 저장"""
    if not items:
        return
    
    fieldnames = [
        'search_gu', 'search_dong', 'item_id', 'title', 'address', 
        'local1', 'local2', 'local3',
        'deposit', 'rent', 'size_m2', 'floor', 'service_type', 'manage_cost',
        'lat', 'lng', 'thumbnail'
    ]
    
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in items:
            writer.writerow({k: p.get(k, '') for k in fieldnames})


if __name__ == '__main__':
    main()

