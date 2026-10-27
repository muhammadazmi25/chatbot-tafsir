import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def test_api():
    # 1. Test Surahs
    url = 'http://localhost:8001/api/v1/tafsir/surahs'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        surahs = json.loads(resp.read().decode('utf-8'))
        print(f"[OK] GET /api/v1/tafsir/surahs -> {len(surahs)} surah")
        
    # 2. Test Ayat for Hud (11) and Yusuf (12)
    for s_no in [11, 12, 15, 24]:
        url = f'http://localhost:8001/api/v1/tafsir/surahs/{s_no}/ayat'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            ayats = json.loads(resp.read().decode('utf-8'))
            print(f"[OK] GET /api/v1/tafsir/surahs/{s_no}/ayat -> {len(ayats)} ayat")
            # Test first ayat units (fallback to raw if units table is reset)
            if ayats:
                vt_id = ayats[0]['id_verse_tafsir']
                u_url = f'http://localhost:8001/api/v1/tafsir/verse/{vt_id}/units'
                u_req = urllib.request.Request(u_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(u_req) as u_resp:
                    units = json.loads(u_resp.read().decode('utf-8'))
                    print(f"     -> Units/Raw fallback for Ayat 1 (vt_id={vt_id}): {len(units)} units")

if __name__ == '__main__':
    test_api()
