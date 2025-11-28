"""
직방 매물 상세 정보 조회 스크립트
item_id로 개별 매물의 상세 정보를 조회하여 저장

사용법:
  python fetch_item_details.py 46979267                    # 단일 item_id
  python fetch_item_details.py 46979267 46979268 46979269  # 여러 item_id
  python fetch_item_details.py --file item_ids.txt         # 파일에서 읽기
  python fetch_item_details.py --csv zigbang_강남구.csv     # CSV의 item_id 컬럼 사용
"""
import requests
import json
import csv
import time
import sys
import os
from datetime import datetime

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'origin': 'https://www.zigbang.com',
    'referer': 'https://www.zigbang.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'x-zigbang-platform': 'www',
}


def fetch_item_detail(item_id: int) -> dict:
    """개별 매물 상세 정보 조회"""
    url = f'https://apis.zigbang.com/v3/items/{item_id}'
    params = {
        'version': '',
        'domain': 'zigbang',
    }
    
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_detail(data: dict) -> dict:
    """상세 정보에서 필요한 필드 추출"""
    item = data.get('item', {})
    agent = data.get('agent', {})
    realtor = data.get('realtor', {})
    subways = data.get('subways', [])
    
    # 가격 정보
    price = item.get('price', {})
    
    # 면적 정보
    area = item.get('area', {})
    
    # 층 정보
    floor_info = item.get('floor', {})
    
    # 관리비 정보
    manage_cost = item.get('manageCost', {})
    manage_detail = item.get('manageCostDetail', {})
    
    # 주소 정보
    address_origin = item.get('addressOrigin', {})
    
    # 위치 정보
    location = item.get('location', {}) or item.get('randomLocation', {})
    
    # 지하철 정보
    subway_names = [f"{s.get('name', '')}({s.get('description', '')})" for s in subways]
    
    # 옵션 정보
    options = item.get('options', [])
    
    # 주변 편의시설
    neighborhoods = item.get('neighborhoods', {})
    amenities = [a.get('title', '') for a in neighborhoods.get('amenities', [])]
    
    return {
        # 기본 정보
        'item_id': item.get('itemId'),
        'sales_type': item.get('salesType'),  # 월세, 전세, 매매
        'service_type': item.get('serviceType'),  # 원룸, 오피스텔 등
        'room_type': item.get('roomType'),  # 분리형원룸 등
        'residence_type': item.get('residenceType'),  # 단독주택, 다세대 등
        'status': item.get('status'),
        
        # 가격 정보
        'deposit': price.get('deposit'),  # 보증금 (만원)
        'rent': price.get('rent'),  # 월세 (만원)
        
        # 면적 정보
        'area_m2': area.get('전용면적M2'),
        
        # 층 정보
        'floor': floor_info.get('floor'),
        'all_floors': floor_info.get('allFloors'),
        
        # 관리비
        'manage_cost': manage_cost.get('amount'),  # 관리비 (만원)
        'manage_cost_includes': ', '.join(manage_cost.get('includes', [])),
        'manage_cost_not_includes': ', '.join(manage_cost.get('notIncludes', [])),
        
        # 주소
        'local1': address_origin.get('local1', ''),
        'local2': address_origin.get('local2', ''),
        'local3': address_origin.get('local3', ''),
        'full_address': address_origin.get('fullText', ''),
        'jibun_address': item.get('jibunAddress', ''),
        
        # 위치 (좌표)
        'lat': location.get('lat'),
        'lng': location.get('lng'),
        
        # 제목 및 설명
        'title': item.get('title'),
        'description': item.get('description', '')[:500] if item.get('description') else '',  # 500자 제한
        
        # 옵션
        'options': ', '.join(options),
        
        # 기타 정보
        'room_direction': item.get('roomDirection'),  # 방향 (S, N, E, W 등)
        'direction_criterion': item.get('directionCriterion'),
        'parking': item.get('parkingAvailableText'),
        'elevator': item.get('elevator'),
        'bathroom_count': item.get('bathroomCount'),
        'movein_date': item.get('moveinDate'),
        'approve_date': item.get('approveDate'),
        
        # 지하철
        'subways': ', '.join(subway_names),
        
        # 주변 편의시설
        'amenities': ', '.join(amenities),
        
        # 중개사 정보
        'agent_name': agent.get('agentName'),
        'agent_title': agent.get('agentTitle'),
        'agent_phone': agent.get('agentPhone'),
        'agent_address': agent.get('agentAddress'),
        
        # 태그
        'tags': ', '.join(data.get('tags', [])),
        
        # 이미지
        'thumbnail': item.get('imageThumbnail'),
        'images': ', '.join(item.get('images', [])[:5]),  # 최대 5개
        
        # 메타 정보
        'updated_at': item.get('updatedAt'),
        'is_premium': item.get('isPremium'),
    }


def save_to_csv(items: list, filename: str):
    """CSV 파일로 저장"""
    if not items:
        print('저장할 항목이 없습니다.')
        return
    
    fieldnames = list(items[0].keys())
    
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            writer.writerow(item)
    
    print(f'✅ CSV 저장 완료: {filename} ({len(items)}개)')


def save_to_json(items: list, filename: str):
    """JSON 파일로 저장 (전체 원본 데이터)"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    
    print(f'✅ JSON 저장 완료: {filename} ({len(items)}개)')


def load_item_ids_from_file(filepath: str) -> list:
    """텍스트 파일에서 item_id 목록 읽기"""
    with open(filepath, 'r') as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]


def load_item_ids_from_csv(filepath: str) -> list:
    """CSV 파일에서 item_id 컬럼 읽기"""
    item_ids = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row.get('item_id')
            if item_id and str(item_id).isdigit():
                item_ids.append(int(item_id))
    return item_ids


def main():
    print('=' * 60)
    print('  직방 매물 상세 정보 조회')
    print('=' * 60)
    
    # 인자 파싱
    item_ids = []
    
    if len(sys.argv) < 2:
        print('\n사용법:')
        print('  python fetch_item_details.py 46979267')
        print('  python fetch_item_details.py 46979267 46979268')
        print('  python fetch_item_details.py --file item_ids.txt')
        print('  python fetch_item_details.py --csv zigbang_강남구.csv')
        return
    
    if sys.argv[1] == '--file':
        filepath = sys.argv[2]
        item_ids = load_item_ids_from_file(filepath)
        print(f'\n파일에서 {len(item_ids)}개 item_id 로드: {filepath}')
    elif sys.argv[1] == '--csv':
        filepath = sys.argv[2]
        item_ids = load_item_ids_from_csv(filepath)
        print(f'\nCSV에서 {len(item_ids)}개 item_id 로드: {filepath}')
    else:
        item_ids = [int(arg) for arg in sys.argv[1:] if arg.isdigit()]
        print(f'\n{len(item_ids)}개 item_id 입력됨')
    
    if not item_ids:
        print('❌ item_id를 찾을 수 없습니다.')
        return
    
    print(f'\n총 {len(item_ids)}개 매물 조회 시작...\n')
    
    # 상세 정보 조회
    raw_data = []  # 원본 JSON 저장용
    parsed_data = []  # 파싱된 데이터 저장용
    success_count = 0
    fail_count = 0
    
    for idx, item_id in enumerate(item_ids, start=1):
        try:
            data = fetch_item_detail(item_id)
            raw_data.append(data)
            
            parsed = parse_detail(data)
            parsed_data.append(parsed)
            
            success_count += 1
            print(f'  [{idx}/{len(item_ids)}] {item_id}: ✅ {parsed.get("title", "")[:30]}...')
            
        except Exception as e:
            fail_count += 1
            print(f'  [{idx}/{len(item_ids)}] {item_id}: ❌ {e}')
        
        time.sleep(0.5)  # API 부하 방지
    
    # 결과 저장
    print('\n' + '=' * 60)
    
    if parsed_data:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # CSV 저장 (파싱된 데이터)
        csv_filename = f'zigbang_details_{timestamp}.csv'
        save_to_csv(parsed_data, csv_filename)
        
        # JSON 저장 (원본 데이터)
        json_filename = f'zigbang_details_{timestamp}.json'
        save_to_json(raw_data, json_filename)
    
    print(f'\n📊 결과:')
    print(f'   - 성공: {success_count}개')
    print(f'   - 실패: {fail_count}개')


if __name__ == '__main__':
    main()

