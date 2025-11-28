import json
import math
import time
import sys
import os
from typing import List, Tuple
import requests

from logic.zigbang_items_fetch import fetch_items

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/json',
    'origin': 'https://www.zigbang.com',
    'referer': 'https://www.zigbang.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'x-zigbang-platform': 'www',
}

ENDPOINTS = [
    'https://apis.zigbang.com/v2/items/oneroom',
    'https://apis.zigbang.com/v2/items/oneroom/vip',
]


def geocode_region(region: str) -> Tuple[float, float]:
    url = 'https://nominatim.openstreetmap.org/search'
    params = {'q': region, 'format': 'json', 'limit': 1}
    r = requests.get(url, params=params, headers={
                     'User-Agent': HEADERS['user-agent']}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError('지오코딩 결과가 없습니다')
    return float(data[0]['lat']), float(data[0]['lon'])


def generate_grid(lat: float, lng: float, radius_km: float = 1.0, steps: int = 3) -> List[Tuple[float, float]]:
    # steps: number of points per axis (odd: center included)
    points = []
    # 1 deg lat ~ 111 km
    lat_degree_km = 111.0
    lon_degree_km = 111.0 * math.cos(math.radians(lat))

    span_lat = radius_km / lat_degree_km
    span_lng = radius_km / lon_degree_km

    if steps <= 1:
        return [(lat, lng)]

    for i in range(steps):
        for j in range(steps):
            frac_i = (i / (steps - 1) - 0.5) * 2  # -1 .. 1
            frac_j = (j / (steps - 1) - 0.5) * 2
            p_lat = lat + frac_i * span_lat
            p_lng = lng + frac_j * span_lng
            points.append((p_lat, p_lng))
    return points


def try_query_point(lat: float, lng: float, radius: float = 1.0) -> List[int]:
    found_ids = set()
    params_candidates = [
        {'lat': lat, 'lng': lng, 'radius': radius, 'zoom_level': 15},
        {'centerLat': lat, 'centerLng': lng, 'radius': radius, 'zoom_level': 15},
        {'x': lng, 'y': lat, 'radius': radius},
    ]
    for ep in ENDPOINTS:
        for params in params_candidates:
            try:
                r = requests.get(ep, params=params,
                                 headers=HEADERS, timeout=10)
            except Exception:
                continue
            if r.status_code != 200:
                continue
            try:
                j = r.json()
            except Exception:
                continue
            # 탐색 가능한 구조들
            items = None
            if isinstance(j, dict):
                if 'items' in j and isinstance(j['items'], list):
                    items = j['items']
                elif 'data' in j and isinstance(j['data'], dict) and 'items' in j['data']:
                    items = j['data']['items']
                else:
                    # 응답이 딕셔너리지만 다른 구조일 수 있음; 시도해보기
                    for v in j.values():
                        if isinstance(v, list):
                            items = v
                            break
            elif isinstance(j, list):
                items = j

            if not items:
                continue

            for it in items:
                # 여러 키 시도
                iid = it.get('item_id') if isinstance(it, dict) else None
                if not iid:
                    if isinstance(it, dict):
                        iid = it.get('id') or it.get(
                            'itemId') or it.get('item_id')
                if iid:
                    found_ids.add(int(iid))
    return sorted(found_ids)


def collect_itemids_for_region(region: str, radius_km: float = 1.0, steps: int = 3, pause: float = 0.5) -> List[int]:
    print(f'[{region}] 지오코딩...')
    lat, lng = geocode_region(region)
    print(f'  좌표: {lat},{lng} — 그리드 생성({steps}x{steps}, 반경 {radius_km}km)')
    points = generate_grid(lat, lng, radius_km=radius_km, steps=steps)
    all_ids = set()
    for idx, (plat, plng) in enumerate(points, 1):
        print(f'  포인트 {idx}/{len(points)}: {plat:.6f},{plng:.6f} 조회 중...')
        ids = try_query_point(plat, plng, radius=radius_km)
        print(f'    발견: {len(ids)}')
        for i in ids:
            all_ids.add(i)
        time.sleep(pause)
    return sorted(all_ids)


def save_regions_map(map_obj: dict, path: str = 'regions_itemids.json'):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(map_obj, f, ensure_ascii=False, indent=2)
    print(f'지역별 itemId 맵 저장: {path}')


def main():
    if len(sys.argv) > 1:
        regions = sys.argv[1:]
    else:
        regions = ['서울특별시 마포구 망원동']

    regions_map = {}
    for region in regions:
        try:
            ids = collect_itemids_for_region(
                region, radius_km=0.8, steps=3, pause=0.6)
        except Exception as e:
            print(f'  오류: {e}')
            ids = []
        regions_map[region] = ids

    save_regions_map(regions_map)

    # 자동으로 상세 정보 가져오기
    print('수집된 itemIds로 상세 정보를 요청합니다...')
    for region, ids in regions_map.items():
        if not ids:
            print(f'  {region}: itemIds 없음, 건너뜁니다')
            continue
        chunks = [ids[i:i+50] for i in range(0, len(ids), 50)]
        combined = []
        for ch in chunks:
            try:
                items = fetch_items(ch)
            except Exception as e:
                print(f'    상세 요청 실패: {e}')
                continue
            combined.extend(items)
            time.sleep(0.5)
        # 저장
        safe = region.replace(' ', '_').replace('/', '_')
        out = f'zigbang_items_{safe}.csv'
        # reuse zigbang_items_fetch.save_to_csv? it was not exported; write simple csv here
        if combined:
            from logic.zigbang_items_fetch import parse_item
            parsed = [parse_item(it) for it in combined]
            # write csv
            import csv as _csv
            fieldnames = ['item_id', 'title', 'address', 'deposit', 'rent', 'size_m2',
                          'floor', 'service_type', 'manage_cost', 'reg_date', 'lat', 'lng', 'thumbnail']
            with open(out, 'w', encoding='utf-8', newline='') as f:
                w = _csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                for p in parsed:
                    w.writerow({k: p.get(k, '') for k in fieldnames})
            print(f'  상세 저장: {out} (항목 수: {len(parsed)})')
        else:
            print(f'  {region}: 상세 항목 없음')


if __name__ == '__main__':
    main()
