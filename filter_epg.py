import urllib.request
import re
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# 1. We read the same playlists your Flutter app uses
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

print("2. Parsing massive raw XMLTV file (this takes a moment)...")
tree = ET.parse(gzip.open('guide_raw.xml.gz', 'rb'))
root = tree.getroot()

now = datetime.now(timezone.utc)
end_window = now + timedelta(hours=48)

print("3. Filtering channels...")
channels_kept = 0
for channel in root.findall('channel'):
    if channel.get('id') not in valid_ids:
        root.remove(channel)
    else:
        channels_kept += 1

print(f"   Kept {channels_kept} channels.")

print("4. Filtering programmes (Right Now + Next 48 hours only)...")
programmes_kept = 0
for prog in root.findall('programme'):
    c_id = prog.get('channel')
    if c_id not in valid_ids:
        root.remove(prog)
        continue
    
    start_str = prog.get('start')
    stop_str = prog.get('stop')
    try:
        stop_time = datetime.strptime(stop_str[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        start_time = datetime.strptime(start_str[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        
        # Keep if: it hasn't finished yet (stop > now) AND starts within our 48h window
        if stop_time >= now and start_time <= end_window:
            programmes_kept += 1
        else:
            root.remove(prog)
    except Exception:
        root.remove(prog)

print(f"   Kept {programmes_kept} programmes.")

print("5. Saving ultra-lean compressed EPG...")
with gzip.open('guide.xml.gz', 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print("Done! The file is now optimized for mobile.")
