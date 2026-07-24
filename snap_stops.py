"""
Snap stop coordinates from compound centers to nearest road points.
Uses route polylines (which follow actual roads) as reference.
"""
import json, sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('stops_geo_v2.json', 'r', encoding='utf-8') as f:
    v2 = json.load(f)

with open('route_polylines.json', 'r', encoding='utf-8') as f:
    rp = json.load(f)

from build_map import tq, jb, hq


def dist_km(lat1, lng1, lat2, lng2):
    """Haversine distance in meters."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def nearest_point_on_polyline(lat, lng, polyline):
    """Find the closest point on a polyline to (lat,lng). Returns (lat,lng,distance_m)."""
    best_lat, best_lng, best_dist = None, None, float('inf')
    for pt in polyline:
        d = dist_km(lat, lng, pt[0], pt[1])
        if d < best_dist:
            best_dist = d
            best_lat, best_lng = pt[0], pt[1]
    return best_lat, best_lng, best_dist


# Build mapping: stop_name -> list of route names
stop_routes = {}
for routes, cat in [(tq,'tq'), (jb,'jb'), (hq,'hq')]:
    for r in routes:
        rname, color, stops = r
        for s in stops:
            sname = s[0]
            if sname not in stop_routes:
                stop_routes[sname] = []
            stop_routes[sname].append(rname)

# For each stop, find the best road position across all its routes
snapped = {}
stats = {'snapped': 0, 'kept': 0, 'no_polyline': 0}

for sname, route_names in stop_routes.items():
    if sname not in v2 or not v2[sname]:
        continue

    orig = v2[sname]
    best_snap = None
    best_dist = float('inf')

    # Try to snap using each route's polyline
    for rname in route_names:
        entry = rp.get(rname)
        if not entry or not entry.get('polyline'):
            continue
        poly = entry['polyline']
        snap_lat, snap_lng, d = nearest_point_on_polyline(orig['lat'], orig['lng'], poly)
        if d < best_dist:
            best_dist = d
            best_snap = (snap_lat, snap_lng)

    if best_snap and best_dist < 200:  # Only snap if within 200m
        old = (orig['lat'], orig['lng'])
        v2[sname] = {'lng': best_snap[1], 'lat': best_snap[0]}
        if best_dist > 20:
            stats['snapped'] += 1
            if best_dist > 50:
                print(f'  SNAPPED ({best_dist:.0f}m): {sname}')
        else:
            stats['kept'] += 1
    else:
        stats['no_polyline'] += 1
        if best_dist > 200:
            print(f'  TOO FAR ({best_dist:.0f}m): {sname}')

with open('stops_geo_v2.json', 'w', encoding='utf-8') as f:
    json.dump(v2, f, ensure_ascii=False, indent=2)

print(f'\nResults: {stats["snapped"]} snapped to road, {stats["kept"]} already on road, {stats["no_polyline"]} skipped')
