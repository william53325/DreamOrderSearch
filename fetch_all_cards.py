import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

# ========== 版本資訊 ==========
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}"

CACHE_DIR = Path(__file__).parent / 'local_cache'
CACHE_FILE = CACHE_DIR / 'card_data.json'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

EXPANSION_CODES = [
    'BP01', 'BP02',
    'CBP01', 'CBP02', 'CBP03', 'CBP04',
    'CSD01', 'CSD02', 'CSD03', 'CSD04', 'CSD05', 'CSD06',
    'PB01',
    'PBP01', 'PBP02', 'PBP03', 'PBP04',
    'PR',
    'PSD01', 'PSD02', 'PSD03', 'PSD04', 'PSD05', 'PSD06',
    'TBP01B', 'TBP01C', 'TBP01D', 'TBP01DB', 'TBP01E', 'TBP01F',
    'TBP01G', 'TBP01H', 'TBP01L', 'TBP01M', 'TBP01S', 'TBP01T'
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

ICON_TAG_MAP = {
    '【攻撃】': '【攻擊】',
    '【守備】': '【守備】',
    '【サポート】': '【支援】',
    '【メイン】': '【主要】',
    '【メイン・起動】': '【主要・起動】',
    '【勝負中①】': '【勝負中1】',
    '【勝負中②】': '【勝負中2】',
    '【コンボ】': '【Combo】',
    '【覚醒】': '【覺醒】',
    '【手札①】': '【手札1】',
    '【ダイス】': '【骰子】',
    '【ZONE】': '【ZONE】',
    '【本領発揮】': '【本領發揮】',
    '【タイム①】': '【時間1】',
    '【タイム1】': '【時間1】'
}

POSITION_MAP = {
    '投手': '投手 (Pitcher)',
    '捕手': '捕手 (Catcher)',
    '一塁手': '一壘手 (1B)',
    '二塁手': '二壘手 (2B)',
    '三塁手': '三壘手 (3B)',
    '遊撃手': '遊撃手 (SS)',
    '外野手': '外野手 (OF)',
    'ZONE': 'ZONE'
}

TYPE_MAP = {
    '選手': '選手卡',
    '戦術': '戰術卡',
    'ZONE選手': 'ZONE選手卡',
    'タイム': '時間卡',
    'チーム': '隊伍卡'
}

TEAM_MAP = {
    '読売ジャイアンツ': '讀賣巨人',
    '阪神タイガース': '阪神虎',
    '中日ドラゴンズ': '中日龍',
    '横浜DeNAベイスターズ': '橫濱DeNA',
    '広島東洋カープ': '廣島東洋鯉',
    '東京ヤクルトスワローズ': '東京養樂多',
    '福岡ソフトバンクホークス': '福岡軟銀',
    '北海道日本ハムファイターズ': '北海道日本火腿',
    'オリックス・バファローズ': '歐力士猛牛',
    '東北楽天ゴールデンイーグルス': '東北樂天金鷲',
    '埼玉西武ライオンズ': '埼玉西武獅',
    '千葉ロッテマリーンズ': '千葉羅德海洋',
    '侍ジャパン': '武士日本'
}


def extract_ability_lines(info_div):
    if not info_div:
        return []
    segments = []
    current = ''
    for node in info_div.descendants:
        if getattr(node, 'name', None) == 'img':
            alt = node.get('alt', '').strip()
            if alt:
                if current and not current.endswith(' '):
                    current += ' '
                current += alt
        elif getattr(node, 'name', None) == 'br':
            if current.strip():
                segments.append(re.sub(r'\s+', ' ', current).strip())
                current = ''
        elif getattr(node, 'name', None) in ['p', 'div']:
            if current.strip():
                segments.append(re.sub(r'\s+', ' ', current).strip())
                current = ''
        elif isinstance(node, str):
            text = node.strip()
            if text:
                if current and not current.endswith(' '):
                    current += ' '
                current += text
    if current.strip():
        segments.append(re.sub(r'\s+', ' ', current).strip())
    return [seg for seg in segments if seg and seg != '詳細を見る']


def translate_line_tags(line):
    for tag, zh in ICON_TAG_MAP.items():
        line = line.replace(tag, zh)
    return line


def build_card_record(expansion, card_id, card_name, team_name, position, card_type, rarity, ability_lines, img_url):
    special_ability = ' '.join(ability_lines) if ability_lines else '無特殊能力'
    if not special_ability.strip() or special_ability.strip() == '-':
        special_ability = '無特殊能力 (白板卡)'

    ap_bonus = re.findall(r'AP\s*[＋+]\s*(\d+)', special_ability)
    dp_bonus = re.findall(r'DP\s*[＋+]\s*(\d+)', special_ability)

    return {
        'id': card_id,
        'expansion': expansion,
        'name': card_name,
        'team': team_name,
        'team_zh': TEAM_MAP.get(team_name, ''),
        'position': position,
        'type': card_type,
        'rarity': rarity,
        'special_ability_ja': special_ability,
        'ability_lines': ability_lines,
        'ability_tag_notes': [],
        'image_url': img_url,
        'detected_ap': f'+{ap_bonus[0]}' if ap_bonus else '依效果判定',
        'detected_dp': f'+{dp_bonus[0]}' if dp_bonus else '依效果判定',
    }


def make_expansion_page_url(expansion, page):
    params = {
        'expansion': expansion,
        'view': 'text',
        'page': page
    }
    return f'https://dreamorder.com/cardlist/searchresults_ex?{urlencode(params)}'


def fetch_all_cards():
    cards = []
    start = time.time()
    session = requests.Session()
    session.headers.update(HEADERS)
    for expansion in EXPANSION_CODES:
        page = 1
        print(f'Fetching expansion {expansion}')
        while True:
            url = make_expansion_page_url(expansion, page)
            try:
                resp = session.get(url, timeout=25)
            except Exception as exc:
                print(f'  request error {expansion} page {page}:', exc)
                break
            if resp.status_code == 404:
                print(f'  page {page} returned 404, stop expansion')
                break
            if resp.status_code != 200:
                print(f'  page {page} status {resp.status_code}, skip page')
                page += 1
                continue
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('li.list-Item')
            if not items:
                print(f'  no items on page {page}, stop expansion')
                break
            print(f'  page {page} items {len(items)}')
            for item in items:
                card_id_tag = item.select_one('p.info-Number')
                card_name_tag = item.select_one('p.info-Name')
                if not card_id_tag or not card_name_tag:
                    continue
                cid = card_id_tag.get_text(strip=True)
                type_spans = [span.get_text(strip=True) for span in item.select('p.info-Types span')]
                team_name = type_spans[0] if len(type_spans) > 0 else '其他/戰術卡'
                position = POSITION_MAP.get(type_spans[1], type_spans[1]) if len(type_spans) > 1 else '無'
                card_type = TYPE_MAP.get(type_spans[2], type_spans[2]) if len(type_spans) > 2 else '其他'
                rarity = type_spans[3] if len(type_spans) > 3 else 'C'
                info = item.select_one('div.info-Text')
                ability_lines = extract_ability_lines(info)
                img_tag = item.select_one('div.item-Image img')
                img_url = urljoin('https://dreamorder.com/', img_tag.get('src')) if img_tag and img_tag.get('src') else ''
                cards.append(build_card_record(
                    expansion,
                    cid,
                    card_name_tag.get_text(strip=True),
                    team_name,
                    position,
                    card_type,
                    rarity,
                    ability_lines,
                    img_url,
                ))
            page += 1
        save_cards(cards)
        print(f'  saved progress count {len(cards)}')
    elapsed = time.time() - start
    print(f'Fetched total {len(cards)} cards in {elapsed:.1f}s')
    return cards


def save_cards(cards):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    print(f"Dream Order Card Fetcher v{VERSION}")
    print(f"Starting full card database fetch from official website...")
    print("-" * 60)
    
    start_time = time.time()
    cards = fetch_all_cards()
    elapsed_time = time.time() - start_time
    
    save_cards(cards)
    print("-" * 60)
    print(f"✅ Successfully saved {len(cards)} cards to {CACHE_FILE}")
    print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
    print(f"📊 File size: {CACHE_FILE.stat().st_size / 1024 / 1024:.2f} MB")
