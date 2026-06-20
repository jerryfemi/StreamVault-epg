import urllib.request
import re
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

m3u_urls = [
    'https://iptv-org.github.io/iptv/categories/sports.m3u',
    'https://iptv-org.github.io/iptv/categories/movies.m3u'
]

print("1. Fetching M3U playlists...")
valid_ids = set()
for url in m3u_urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8', errors='ignore')
        ids = re.findall(r'tvg-id="([^"]+)"', content)
        valid_ids.update(ids)

if "" in valid_ids:
    valid_ids.remove("")
print(f"   Found {len(valid_ids)} unique channel IDs in playlists.")

print("2. Parsing massive raw XMLTV file (Loading into memory)...")
tree = ET.parse(gzip.open('guide_raw.xml.gz', 'rb'))
root = tree.getroot()

now = datetime.now(timezone.utc)
end_window = now + timedelta(hours=48)

print("3. Filtering channels instantly...")
# FAST METHOD: Create a new list of what we want to keep
kept_channels = [c for c in root.findall('channel') if c.get('id') in valid_ids]

print("4. Filtering programmes instantly (Right Now + Next 48 hours only)...")
kept_programmes = []
for prog in root.findall('programme'):
    if prog.get('channel') not in valid_ids:
        continue
    
    try:
        stop_time = datetime.strptime(prog.get('stop')[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        start_time = datetime.strptime(prog.get('start')[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        
        if stop_time >= now and start_time <= end_window:
            kept_programmes.append(prog)
    except Exception:
        pass

print(f"   Kept {len(kept_channels)} channels and {len(kept_programmes)} programmes.")

print("5. Saving ultra-lean compressed EPG...")
# Wipe the massive list instantly, then only add back the ones we kept
root.clear()
root.extend(kept_channels)
root.extend(kept_programmes)

with gzip.open('guide.xml.gz', 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print("Done! The file is now optimized for mobile.")
