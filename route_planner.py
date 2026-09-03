"""
Pre-compute road-following route polylines using Amap Driving API.
Usage: set AMAP_WEB_API_KEY=<key> && python route_planner.py
Output: route_polylines.json
"""
import json
import os
import sys
import time

# Fix Windows GBK encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    print("Error: requests library not found. Run: pip install requests")
    sys.exit(1)

KEY = os.environ.get("AMAP_WEB_API_KEY")
if not KEY:
    print("Error: AMAP_WEB_API_KEY environment variable not set.")
    print("Usage: set AMAP_WEB_API_KEY=<your_key> && python route_planner.py")
    sys.exit(1)

# Import route definitions from build_map
from build_map import tq, jb, hq, geo as stops_geo

# Destination
DEST = stops_geo.get('所部', {'lng': 126.502544, 'lat': 45.700566})

# ─────────────────────────────────────────────────────────────
# 强制走向（手动干预高德自动选路）
# 有些路线要求在特定路口转/不转，但高德按"最快"自己走。可在这里
# 注入"途经点"坐标，强制路线经过这个路口（经过该点自然就按你想的转）。
#
# 格式：{ '路线名(须与build_map完全一致)': {
#           '某站点名': [(经, 纬), ...],      # 「该站之后」强制经过的路口坐标
#           '_dest':    [(经, 纬), ...],      # 「最后一站 → 所部」虚线这一段强制经过
#        } }
# 想强制末段到所部的某个路口，用 '_dest'。可多条、多坐标。
# ─────────────────────────────────────────────────────────────
FORCED = {
    # 示例（通勤）：9号在"涧桥西畔"之后强制经过某个路口
    # '9号·金域蓝城→王岗 ⭐': {
    #     '涧桥西畔': [(126.580, 45.690)],
    #     '_dest':    [(126.520, 45.705)],
    # },
    # 加班/红旗线：所部→最后一站(最靠所部那段)用 '_start'；
    #          指定"前向第 j 站"之后强制经过某点用 '站点名':[点]。
}


def get_driving_polyline(origin_lng, origin_lat, dest_lng, dest_lat, waypoints=None):
    """
    Call Amap driving direction API.
    Returns polyline as [[lat, lng], ...] for Leaflet, or None on failure.
    """
    params = {
        'key': KEY,
        'origin': '%s,%s' % (origin_lng, origin_lat),
        'destination': '%s,%s' % (dest_lng, dest_lat),
        'strategy': 0,          # fastest route
        'extensions': 'all',    # include polyline in steps
    }
    if waypoints:
        # Format: lng1,lat1;lng2,lat2;...
        params['waypoints'] = ';'.join('%s,%s' % (w[0], w[1]) for w in waypoints)

    try:
        resp = requests.get(
            'https://restapi.amap.com/v3/direction/driving',
            params=params, timeout=10
        )
        data = resp.json()

        if data.get('status') != '1':
            print('    API error: status=%s, info=%s' % (data.get('status'), data.get('info', '')))
            return None

        route = data.get('route', {})
        paths = route.get('paths', [])
        if not paths:
            print('    No paths found')
            return None

        path = paths[0]
        steps = path.get('steps', [])
        if not steps:
            print('    No steps in path')
            return None

        # Decode polyline from all steps
        all_coords = []
        for step in steps:
            poly_str = step.get('polyline', '')
            if not poly_str:
                continue
            # Amap polyline format: "lng1,lat1;lng2,lat2;..."
            for point in poly_str.split(';'):
                parts = point.split(',')
                if len(parts) == 2:
                    # Convert to Leaflet [lat, lng] format
                    all_coords.append([float(parts[1]), float(parts[0])])

        if all_coords:
            return all_coords
        else:
            print('    Empty polyline')
            return None

    except requests.exceptions.Timeout:
        print('    Request timed out')
    except requests.exceptions.RequestException as e:
        print('    Request error: %s' % e)
    except Exception as e:
        print('    Unexpected error: %s' % e)

    return None


def main():
    # Check for route name filter from CLI
    filter_name = sys.argv[1] if len(sys.argv) > 1 else None

    # Load existing polylines to preserve unchanged routes
    result = {}
    if os.path.exists('route_polylines.json'):
        with open('route_polylines.json', 'r', encoding='utf-8') as f:
            result = json.load(f)

    total_ok = 0
    total_fail = 0
    grand_total = 0
    updated = 0

    all_routes = [('tq', tq), ('jb', jb), ('hq', hq)]

    for category, routes in all_routes:
        for r in routes:
            route_name, color, stops = r

            # Filter: match start of route name (e.g. "1号" won't match "11号")
            if filter_name and not route_name.startswith(filter_name):
                grand_total += 1
                continue

            # Collect valid coords for this route
            coords = []
            valid_names = []   # 保留下来的站点名（与 coords 一一对应）
            for s in stops:
                c = stops_geo.get(s[0])
                if c:
                    coords.append((c['lng'], c['lat']))
                    valid_names.append(s[0])

            forced = FORCED.get(route_name, {})
            forced_note = []

            grand_total += 1
            entry = {'polyline': None, 'to_dest': None}

            if len(coords) >= 2:
                if category in ('jb', 'hq'):
                    # 加班/红旗线路：由所部开往终点（反向）
                    origin = (DEST['lng'], DEST['lat'])
                    destination = coords[0]
                    waypoints = list(reversed(coords[1:])) if len(coords) > 1 else None
                    # '_start' = 所部→最后一站(最靠所部那段)，把强制点插在最前
                    fstart = forced.get('_start', [])
                    if fstart:
                        wps = list(fstart) + (waypoints or [])
                        waypoints = wps
                        forced_note.append('_start')
                    # 指定"前向/真实第 j 站"之后强制经过某点：反向绘制里该站位于
                    # waypoints 的 index = len-1-j；强制点插在其后。
                    if waypoints:
                        _w = list(waypoints)
                        for j in range(1, len(coords)):
                            name = valid_names[j]
                            pts = forced.get(name, [])
                            if pts:
                                insert_at = len(coords) - j      # coords[j]之后 → index len-j
                                insert_at = min(max(insert_at, 1), min(len(_w), insert_at))
                                _w[insert_at:insert_at] = pts
                                waypoints = _w
                                forced_note.append(name)
                else:
                    origin = coords[0]
                    destination = coords[-1]
                    # 按行程顺序插入强制路口点：age -> 起点, 之后每隔一站的 'X站' 点插在其后
                    wps = []
                    for i in range(len(coords) - 1):   # 0..len-2
                        if i >= 1:
                            wps.append(coords[i])       # 中间站本身作为途经点
                        for pt in forced.get(valid_names[i], []):
                            wps.append(pt)
                            forced_note.append(valid_names[i])
                    waypoints = wps if wps else None
                dest_forced = forced.get('_dest', [])

                wp_info = (' +%d wp' % len(waypoints)) if waypoints else ''
                print('[%d/%d] %s %s (%d stops%s)...' % (
                    grand_total, 44, category.upper(), route_name, len(coords), wp_info))

                if forced_note or dest_forced:
                    print('    [强制点] 经 %s%s' % (
                        '、'.join(dict.fromkeys(forced_note)) if forced_note else '',
                        ' + 末段(dest)' if dest_forced else ''))

                # Route polyline
                poly = get_driving_polyline(
                    origin[0], origin[1],
                    destination[0], destination[1],
                    waypoints
                )
                if poly:
                    entry['polyline'] = poly
                    total_ok += 1
                    print('    route: %d points OK' % len(poly))
                else:
                    total_fail += 1
                    print('    route: FAILED (will use straight lines)')

                # Last stop -> destination (加班/红旗线反向，起点已是所部，无需此连线)
                if category in ('jb', 'hq'):
                    entry['to_dest'] = None
                else:
                    dest_poly = get_driving_polyline(
                        destination[0], destination[1],
                        DEST['lng'], DEST['lat'],
                        waypoints=dest_forced if dest_forced else None
                    )
                    if dest_poly:
                        entry['to_dest'] = dest_poly
                        print('    to_dest: %d points OK' % len(dest_poly))
                    else:
                        print('    to_dest: FAILED')

                time.sleep(0.25)  # Rate limiting (slower to avoid QPS errors)
            else:
                print('[%d/%d] %s %s: SKIPPED (< 2 valid stops)' % (
                    grand_total, 44, category.upper(), route_name))

            result[route_name] = entry
            updated += 1

    # Save results
    with open('route_polylines.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    print('\n' + '=' * 50)
    if filter_name:
        print('Updated %d route(s) matching "%s".' % (updated, filter_name))
    else:
        print('Updated all %d routes.' % updated)
    print('%d routes computed, %d failed.' % (total_ok, total_fail))
    if total_fail:
        print('Failed routes will use straight lines as fallback.')
    print('Output: route_polylines.json')


if __name__ == '__main__':
    main()
