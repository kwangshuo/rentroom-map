"""
取单个地点的坐标 — 用于手动校正站点时快速查询
用法:
  python geocode_one.py 哈尔滨香坊区轴承文化宫    # POI搜索
  python geocode_one.py -a 哈尔滨市香坊区红旗大街108号  # 地址geocode
  python geocode_one.py 轴承文化宫 --json         # 输出 stops_geo_v2.json 格式，方便直接粘贴

前提: 设置环境变量 AMAP_WEB_API_KEY
"""
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: requests library not found. pip install requests")
    sys.exit(1)

KEY = os.environ.get("AMAP_WEB_API_KEY")
if not KEY:
    print("Error: AMAP_WEB_API_KEY 未设置")
    print("用法: set AMAP_WEB_API_KEY=<key> && python geocode_one.py <关键词>")
    sys.exit(1)


def poi_search(keyword, city="哈尔滨"):
    """高德POI搜索"""
    resp = requests.get(
        "https://restapi.amap.com/v3/place/text",
        params={"key": KEY, "keywords": keyword, "city": city, "offset": 3},
        timeout=5
    )
    data = resp.json()
    if data.get("status") == "1" and data.get("pois"):
        return data["pois"]
    return []


def geo_search(address, city="哈尔滨"):
    """高德地理编码"""
    resp = requests.get(
        "https://restapi.amap.com/v3/geocode/geo",
        params={"key": KEY, "address": address, "city": city},
        timeout=5
    )
    data = resp.json()
    if data.get("status") == "1" and data.get("geocodes"):
        loc = data["geocodes"][0]["location"].split(",")
        return float(loc[0]), float(loc[1])
    return None


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    use_geocode = False    # -a: 直接用地址 geocode
    json_fmt = False       # --json: 输出 stops_geo_v2.json 格式
    keyword_parts = []

    for a in args:
        if a == "-a":
            use_geocode = True
        elif a == "--json":
            json_fmt = True
        else:
            keyword_parts.append(a)

    keyword = " ".join(keyword_parts)

    if use_geocode:
        # 地址 geocode
        print(f"🔍 地址编码: {keyword}\n")
        result = geo_search(keyword)
        if result:
            lng, lat = result
            if json_fmt:
                print(f'"{keyword}": {{ "lng": {lng:.6f}, "lat": {lat:.6f} }}')
            else:
                print(f"坐标: {lng:.6f}, {lat:.6f}")
                print(f"高德: https://uri.amap.com/marker?position={lng},{lat}")
        else:
            print("❌ 未找到")
            sys.exit(1)
    else:
        # POI 搜索
        print(f"🔍 POI搜索: {keyword}\n")
        pois = poi_search(keyword)
        if not pois:
            print("POI 无结果，尝试地址编码...")
            result = geo_search(keyword)
            if result:
                lng, lat = result
                if json_fmt:
                    print(f'"{keyword}": {{ "lng": {lng:.6f}, "lat": {lat:.6f} }}')
                else:
                    print(f"坐标: {lng:.6f}, {lat:.6f}")
                    print(f"高德: https://uri.amap.com/marker?position={lng},{lat}")
            else:
                print("❌ 未找到")
                sys.exit(1)
        else:
            for i, poi in enumerate(pois):
                loc = poi["location"].split(",")
                lng, lat = float(loc[0]), float(loc[1])
                print(f"{i+1}. {poi['name']}")
                print(f"   地址: {poi.get('address', '?')}")
                print(f"   坐标: {lng:.6f}, {lat:.6f}")
                print(f"   地图: https://uri.amap.com/marker?position={lng},{lat}")
                if json_fmt:
                    print(f'   JSON: "{poi["name"]}": {{ "lng": {lng:.6f}, "lat": {lat:.6f} }}')
                print()
