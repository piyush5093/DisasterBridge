import requests
import xml.etree.ElementTree as ET

# Test GDACS - South Asia filter
r = requests.get('https://gdacs.org/xml/rss.xml', timeout=10)
root = ET.fromstring(r.content)
ns = {'gdacs': 'http://www.gdacs.org'}
south_asia = 0
total = 0
for item in root.findall('.//item'):
    geo = item.find('{http://www.georss.org/georss}point')
    if geo is not None and geo.text:
        lat, lon = map(float, geo.text.split())
        total += 1
        if 5 <= lat <= 37 and 60 <= lon <= 100:
            south_asia += 1
            t = item.find('title')
            title = t.text if t is not None else 'unknown'
            print(f"  GDACS SA: {title} lat={lat} lon={lon}")
print(f"GDACS total={total} south_asia={south_asia}")

# Test USGS South Asia bbox
url = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    "?format=geojson"
    "&minlatitude=5&maxlatitude=37"
    "&minlongitude=60&maxlongitude=100"
    "&minmagnitude=3.5&limit=100&orderby=time"
)
r2 = requests.get(url, timeout=15)
d = r2.json()
feats = d.get('features', [])
print(f"USGS South Asia M>=3.5 past 30 days: {len(feats)}")
if feats:
    p = feats[0]['properties']
    g = feats[0]['geometry']['coordinates']
    print(f"  Sample: {p['title']} lon={g[0]} lat={g[1]}")

# Test ReliefWeb
rw_url = (
    "https://api.reliefweb.int/v1/disasters"
    "?appname=disasterbridge"
    "&filter[operator]=OR"
    "&filter[conditions][0][field]=country.name&filter[conditions][0][value]=India"
    "&filter[conditions][1][field]=country.name&filter[conditions][1][value]=Nepal"
    "&filter[conditions][2][field]=country.name&filter[conditions][2][value]=Bangladesh"
    "&filter[conditions][3][field]=country.name&filter[conditions][3][value]=Sri Lanka"
    "&filter[conditions][4][field]=country.name&filter[conditions][4][value]=Myanmar"
    "&filter[conditions][5][field]=country.name&filter[conditions][5][value]=Pakistan"
    "&fields[include][]=name&fields[include][]=type&fields[include][]=date&fields[include][]=country"
    "&limit=20&sort=date.created:desc"
)
r3 = requests.get(rw_url, timeout=15)
rw = r3.json()
items = rw.get('data', [])
print(f"ReliefWeb South Asia disasters: {len(items)}")
for item in items[:5]:
    f = item.get('fields', {})
    dtype = f.get('type', [{}])
    tname = dtype[0].get('name', 'unknown') if dtype else 'unknown'
    country = f.get('country', [{}])
    cname = country[0].get('name', 'unknown') if country else 'unknown'
    print(f"  {f.get('name','')} | {tname} | {cname}")
