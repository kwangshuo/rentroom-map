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
            for s in stops:
                c = stops_geo.get(s[0])
                if c:
                    coords.append((c['lng'], c['lat']))

            grand_total += 1
            entry = {'polyline': None, 'to_dest': None}

            if len(coords) >= 2:
                origin = coords[0]
                destination = coords[-1]
                waypoints = coords[1:-1] if len(coords) > 2 else None

                wp_info = (' +%d wp' % len(waypoints)) if waypoints else ''
                print('[%d/%d] %s %s (%d stops%s)...' % (
                    grand_total, 44, category.upper(), route_name, len(coords), wp_info))

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

                # Last stop -> destination
                dest_poly = get_driving_polyline(
                    destination[0], destination[1],
                    DEST['lng'], DEST['lat']
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
