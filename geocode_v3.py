"""
V3: Incremental geocoding for routes 15-34 stops.
Appends new stops to stops_geo_v2.json.
Usage: set AMAP_WEB_API_KEY=<key> && python geocode_v3.py
"""
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print("Error: requests library not found. pip install requests")
    sys.exit(1)

KEY = os.environ.get("AMAP_WEB_API_KEY")
if not KEY:
    print("Error: AMAP_WEB_API_KEY environment variable not set.")
    sys.exit(1)

# All NEW unique stops from routes 15-34 (name -> POI search keyword)
NEW_STOPS = [
    # 15号
    ("革新街", "哈尔滨南岗区革新街"),
    ("烟草大厦", "哈尔滨南岗区革新街中山路"),
    ("医大一院", "哈尔滨南岗区医大一院东大直街"),
    ("博物馆", "哈尔滨南岗区博物馆少年宫"),
    ("工大", "哈尔滨南岗区哈尔滨工业大学"),
    ("康宁桥", "哈尔滨南岗区康宁桥"),
    ("西雅图水岸", "哈尔滨南岗区西雅图水岸小区"),
    # 16号
    ("经纬三道街", "哈尔滨道里区经纬三道街"),
    ("安升街", "哈尔滨道里区安升街新阳路"),
    ("安发桥", "哈尔滨道里区安发桥"),
    # 17号
    ("理工大学", "哈尔滨南岗区哈尔滨理工大学"),
    ("西典家园", "哈尔滨南岗区西典家园"),
    ("保利清华颐园", "哈尔滨南岗区保利清华颐园"),
    ("职工街", "哈尔滨道里区职工街"),
    ("迎宾小区", "哈尔滨道里区迎宾小区"),
    # 18号
    ("骨伤医院", "哈尔滨南岗区骨伤科医院西大桥"),
    ("清明四道街", "哈尔滨南岗区清明四道街"),
    ("商业大学", "哈尔滨道里区商业大学通达街"),
    # 19号
    ("港务局加油站", "哈尔滨道外区港务局加油站"),
    ("道台府", "哈尔滨道外区道台府八中"),
    ("道外三道街", "哈尔滨道外区北三道街"),
    ("九站", "哈尔滨道里区九站公园"),
    ("盛和世纪", "哈尔滨道里区群力盛和世纪"),
    ("群力新城", "哈尔滨道里区群力新城小区"),
    ("贝肯山", "哈尔滨道里区群力贝肯山"),
    ("保利城3期", "哈尔滨道里区群力保利城三期"),
    ("星光耀", "哈尔滨道里区群力星光耀"),
    # 20号
    ("107站台", "哈尔滨南岗区征仪路科研路"),
    ("大众新城", "哈尔滨南岗区大众新城征仪路"),
    ("大众新城2", "哈尔滨南岗区大众新城保健路"),
    ("医大二院", "哈尔滨南岗区医大二院学府路"),
    # 21号 (小平房 & 恒大御景湾 already in V2)
    # 22号
    ("松浦大桥", "哈尔滨松北区松浦大桥"),
    ("九零四所", "哈尔滨松北区中源大道九零四"),
    ("富力城", "哈尔滨松北区富力城小区"),
    ("商业大学北区", "哈尔滨松北区商业大学北校区中源大道"),
    ("奥林小镇", "哈尔滨松北区奥林小镇"),
    ("莲花渔村", "哈尔滨松北区莲花渔村"),
    ("民生尚都和园", "哈尔滨道里区民生尚都和园"),
    # 23号
    ("南京路", "哈尔滨呼兰区南京路转盘道"),
    ("利民大道", "哈尔滨呼兰区利民大道顺迈医院"),
    ("柒季城", "哈尔滨呼兰区柒季城小区"),
    ("龙翔路", "哈尔滨松北区龙翔路祥安北大街"),
    ("龙祥路", "哈尔滨松北区龙祥路"),
    ("恒源街", "哈尔滨松北区恒源街万达秀园"),
    ("万达城", "哈尔滨松北区万达城"),
    ("滨江新城", "哈尔滨松北区滨江新城"),
    ("宜居家园", "哈尔滨道里区宜居家园四方台大道"),
    # 24号
    ("酒鬼居", "哈尔滨香坊区香滨路"),
    ("汽车公司", "哈尔滨香坊区香滨路"),
    ("埃德蒙顿路", "哈尔滨道里区埃德蒙顿路"),
    ("穆斯林小区", "哈尔滨道里区穆斯林小区机场路"),
    # 25号
    ("翡翠城", "哈尔滨道里区翡翠城工农大街"),
    ("海富秀园", "哈尔滨道里区群力海富秀园第七大道"),
    ("海福景园", "哈尔滨道里区群力海富景园四方台大道"),
    ("四方台大道", "哈尔滨道里区四方台大道恒大帝景"),
    # 26号
    ("安乐街", "哈尔滨香坊区安乐街和平路和兴路交口"),
    # 27号
    ("八区", "哈尔滨道外区八区南极街长青公园"),
    ("党校（上班单向）", "哈尔滨南岗区延兴路省委党校"),
    # 28号
    ("太平桥", "哈尔滨道外区太平桥地铁口"),
    ("宣化街", "哈尔滨南岗区宣化街聋哑学校"),
    ("中海天誉", "哈尔滨道里区中海天誉洪湖路三环路"),
    # 29号
    ("大学城", "哈尔滨平房区大学城民族学院"),
    ("东方小区", "哈尔滨平房区东方小区"),
    ("二十四中", "哈尔滨平房区二十四中集智街"),
    ("东安名苑", "哈尔滨平房区东安名苑友协大街"),
    ("建安头道街", "哈尔滨平房区建安头道街"),
    ("太平洋商厦", "哈尔滨平房区太平洋商厦友协大街"),
    # 30号
    ("中海时代名邸", "哈尔滨道里区群力中海时代名邸第六大道"),
    ("民生尚都福园", "哈尔滨道里区民生尚都福园"),
    ("熙郡印象", "哈尔滨道里区熙郡印象第六大道"),
    # 31号
    ("万家", "哈尔滨道里区万家电缆厂"),
    ("大中安屯", "哈尔滨道里区大中安屯"),
    ("宫家", "哈尔滨道里区新农镇宫家"),
    ("辛家窝堡", "哈尔滨道里区辛家窝堡"),
    ("建国村", "哈尔滨道里区建国村"),
    ("四环桥", "哈尔滨道里区四环桥"),
    # 32号
    ("薛家", "哈尔滨道里区薛家新发邮局"),
    ("康家", "哈尔滨道里区康家道口"),
    ("小三姓", "哈尔滨道里区小三姓"),
    # 33号
    ("哈西骏赫城", "哈尔滨南岗区哈西骏赫城"),
    ("海宁皮革城", "哈尔滨道里区海宁皮革城机场路"),
    ("小西屯", "哈尔滨道里区小西屯机场路"),
    ("王家店", "哈尔滨道里区王家店机场路"),
    # 34号
    ("汇龙澜湾九里", "哈尔滨道里区群力汇龙澜湾九里"),
    ("金地名悦", "哈尔滨道里区群力金地名悦"),
    ("华润昆仑御", "哈尔滨道里区群力华润昆仑御"),
]


def poi_search(keyword, city="哈尔滨"):
    """Amap POI search"""
    try:
        resp = requests.get(
            "https://restapi.amap.com/v3/place/text",
            params={"key": KEY, "keywords": keyword, "city": city, "offset": 1},
            timeout=5
        )
        data = resp.json()
        if data.get("status") == "1" and data.get("pois"):
            poi = data["pois"][0]
            loc = poi["location"].split(",")
            return float(loc[0]), float(loc[1]), poi.get("name", "")
    except:
        pass
    return None


def geo_search(address, city="哈尔滨"):
    """Amap geocode"""
    try:
        resp = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"key": KEY, "address": address, "city": city},
            timeout=5
        )
        data = resp.json()
        if data.get("status") == "1" and data.get("geocodes"):
            loc = data["geocodes"][0]["location"].split(",")
            return float(loc[0]), float(loc[1])
    except:
        pass
    return None


# Load existing V2 data
with open("stops_geo_v2.json", "r", encoding="utf-8") as f:
    existing = json.load(f)

print("Existing V2 stops: %d" % len(existing))
print("New stops to geocode: %d\n" % len(NEW_STOPS))

new_count = 0
fail_count = 0

for i, (name, keyword) in enumerate(NEW_STOPS):
    if name in existing:
        continue

    coord = None
    poi_result = poi_search(keyword)
    if poi_result:
        lng, lat, poi_name = poi_result
        coord = (lng, lat)

    if not coord:
        geo_result = geo_search(keyword)
        if geo_result:
            coord = geo_result

    if coord:
        existing[name] = {"lng": coord[0], "lat": coord[1]}
        new_count += 1
    else:
        existing[name] = None
        fail_count += 1
        print("  FAIL: %s" % name)

    if (i + 1) % 20 == 0:
        print("  [%d/%d] progress..." % (i + 1, len(NEW_STOPS)))

    time.sleep(0.04)

# Save merged data
with open("stops_geo_v2.json", "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

print("\nDone! %d new stops added, %d failed." % (new_count, fail_count))
print("Total V2 stops: %d" % len(existing))

# Check for None entries
none_entries = [k for k, v in existing.items() if v is None]
if none_entries:
    print("\nUnresolved stops:")
    for n in sorted(none_entries):
        print("  - %s" % n)
