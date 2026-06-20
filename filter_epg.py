import urllib.request
import re
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

m3u_urls = [
    'https://iptv-org.github.io/iptv/categories/sports.m3u',
    'https://iptv-org.github.io/iptv/categories/movies.m3u'
]

print("1. Fetching M3U playlists and extracting names...")
name_to_tvgid = {}

for url in m3u_urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8', errors='ignore')
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('#EXTINF:'):
                tvg_id_match = re.search(r'tvg-id="([^"]+)"', line)
                if tvg_id_match:
                    tvgid = tvg_id_match.group(1)
                    
                    # Extract the actual channel name (after the last comma)
                    name_parts = line.split(',')
                    if len(name_parts) > 1:
                        name = name_parts[-1].strip().lower()
                        name_to_tvgid[name] = tvgid
                        
                    # Also try to extract tvg-name if present
                    tvg_name_match = re.search(r'tvg-name="([^"]+)"', line)
                    if tvg_name_match:
                        name_to_tvgid[tvg_name_match.group(1).lower()] = tvgid

print(f"   Mapped {len(name_to_tvgid)} unique channel names from M3Us.")

print("2. Parsing massive raw XMLTV file (Loading into memory)...")
tree = ET.parse(gzip.open('guide_raw.xml.gz', 'rb'))
root = tree.getroot()

now = datetime.now(timezone.utc)
end_window = now + timedelta(hours=48)

print("3. Matching channels by name and rewriting IDs...")
kept_channels = []
epg_id_to_tvgid = {}

for c in root.findall('channel'):
    display_names = c.findall('display-name')
    matched_tvgid = None
    
    for d in display_names:
        if d.text:
            name_lower = d.text.strip().lower()
            if name_lower in name_to_tvgid:
                matched_tvgid = name_to_tvgid[name_lower]
                break
    
    if matched_tvgid:
        epg_id = c.get('id')
        epg_id_to_tvgid[epg_id] = matched_tvgid
        c.set('id', matched_tvgid) # Rewrite ID for Flutter app!
        kept_channels.append(c)

print(f"   Matched and kept {len(kept_channels)} channels.")

print("4. Filtering programmes and rewriting IDs...")
kept_programmes = []
for prog in root.findall('programme'):
    epg_id = prog.get('channel')
    if epg_id in epg_id_to_tvgid:
        try:
            stop_time = datetime.strptime(prog.get('stop')[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
            start_time = datetime.strptime(prog.get('start')[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
            
            if stop_time >= now and start_time <= end_window:
                # Rewrite ID for Flutter app!
                prog.set('channel', epg_id_to_tvgid[epg_id])
                kept_programmes.append(prog)
        except Exception:
            pass

print(f"   Kept {len(kept_programmes)} programmes.")

print("5. Saving ultra-lean compressed EPG...")
root.clear()
root.extend(kept_channels)
root.extend(kept_programmes)

with gzip.open('guide.xml.gz', 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print("Done! The file is now perfectly matched and optimized.")
