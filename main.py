import streamlit as st
import requests
from bs4 import BeautifulSoup
from googletrans import Translator
import time
import re
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse

# ========== 版本資訊 ==========
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}"

# 1. 網頁基礎配置
st.set_page_config(page_title="日職 Dream Order TCG 全能力查詢", page_icon="⚾", layout="wide")

@st.cache_resource
def get_translator():
    return Translator()

# 日文位置對照表
POSITION_MAP = {
    "投手": "投手 (Pitcher)", "捕手": "捕手 (Catcher)", "一塁手": "一壘手 (1B)",
    "二塁手": "二壘手 (2B)", "三塁手": "三壘手 (3B)", "遊撃手": "遊擊手 (SS)",
    "外野手": "外野手 (OF)", "ZONE": "ZONE"
}

# 中文標記還原回日文的反向映射
ZH_TO_JA_TAG_MAP = {
    "【攻擊】": "【攻撃】",
    "【守備】": "【守備】",
    "【支援】": "【サポート】",
    "【主要】": "【メイン】",
    "【主要・起動】": "【メイン・起動】",
    "【勝負中1】": "【勝負中①】",
    "【勝負中2】": "【勝負中②】",
    "【Combo】": "【コンボ】",
    "【覺醒】": "【覚醒】",
    "【手札1】": "【手札①】",
    "【骰子】": "【ダイス】",
    "【ZONE】": "【ZONE】",
    "【本領發揮】": "【本領発揮】",
    "【時間1】": "【タイム①】"
}

# 卡片類型中文對照
TYPE_MAP = {
    "選手": "選手卡",
    "戦術": "戰術卡",
    "ZONE選手": "ZONE選手卡",
    "タイム": "時間卡",
    "チーム": "隊伍卡"
}

KNOWN_EXPANSION_CODES = [
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

EXPANSION_CODE_PATTERN = re.compile(r'^[A-Z][A-Z0-9]{1,7}$')

# 2. 核心資料爬取與「全能力精準拆分」邏輯
ICON_TAG_MAP = {
    "【攻撃】": "【攻擊】",
    "【守備】": "【守備】",
    "【サポート】": "【支援】",
    "【メイン】": "【主要】",
    "【メイン・起動】": "【主要・起動】",
    "【主要】": "【主要】",
    "【勝負中①】": "【勝負中1】",
    "【勝負中②】": "【勝負中2】",
    "【勝負中1】": "【勝負中1】",
    "【勝負中2】": "【勝負中2】",
    "【コンボ】": "【Combo】",
    "【Combo】": "【Combo】",
    "【覚醒】": "【覺醒】",
    "【手札①】": "【手札1】",
    "【手札1】": "【手札1】",
    "【ダイス】": "【骰子】",
    "【ZONE】": "【ZONE】",
    "【本領発揮】": "【本領發揮】",
    "【タイム①】": "【時間1】",
    "【タイム1】": "【時間1】"
}

TAG_EXPLANATION_MAP = {
    "【攻撃】": "攻擊：在攻擊判定或攻擊階段相關效果",
    "【守備】": "守備：在防守判定或守備階段相關效果",
    "【メイン】": "主要：屬於主要判定/效果",
    "【メイン・起動】": "主要・起動：主要判定的起動型效果",
    "【主要】": "主要：屬於主要判定/效果",
    "【勝負中①】": "勝負中1：勝負階段第一步驟生效",
    "【勝負中②】": "勝負中2：勝負階段第二步驟生效",
    "【勝負中1】": "勝負中1：勝負階段第一步驟生效",
    "【勝負中2】": "勝負中2：勝負階段第二步驟生效",
    "【コンボ】": "Combo：連擊條件下可觸發的效果",
    "【Combo】": "Combo：連擊條件下可觸發的效果",
    "【覚醒】": "覺醒：覺醒狀態時生效的能力",
    "【手札①】": "手札1：消耗一張手牌相關效果",
    "【手札1】": "手札1：消耗一張手牌相關效果",
    "【ダイス】": "骰子：與骰子判定或骰子數有關",
    "【ZONE】": "ZONE：ZONE狀態相關效果",
    "【本領発揮】": "本領發揮：發揮本職能力的強化效果",
    "【タイム①】": "時間1：時間階段或時間效果相關",
    "【タイム1】": "時間1：時間階段或時間效果相關"
}

TEAM_MAP = {
    "読売ジャイアンツ": "讀賣巨人",
    "阪神タイガース": "阪神虎",
    "中日ドラゴンズ": "中日龍",
    "横浜DeNAベイスターズ": "橫濱DeNA",
    "広島東洋カープ": "廣島東洋鯉",
    "東京ヤクルトスワローズ": "東京養樂多",
    "福岡ソフトバンクホークス": "福岡軟銀",
    "北海道日本ハムファイターズ": "北海道日本火腿",
    "オリックス・バファローズ": "歐力士猛牛",
    "東北楽天ゴールデンイーグルス": "東北樂天金鷲",
    "埼玉西武ライオンズ": "埼玉西武獅",
    "千葉ロッテマリーンズ": "千葉羅德海洋",
    "侍ジャパン": "武士日本"
}

CACHE_DIR = Path(__file__).parent / 'local_cache'
CACHE_FILE = CACHE_DIR / 'card_data.json'


def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_local_card_cache():
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [normalize_card_record(card) for card in data]
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_local_card_cache(data):
    try:
        ensure_cache_dir()
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def normalize_expansion_url(url):
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params['view'] = 'text'
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def is_expansion_code(value):
    return bool(EXPANSION_CODE_PATTERN.match(value))


def parse_expansion_codes_from_soup(soup):
    codes = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/cardlist/searchresults/?expansion=' in href:
            parsed = urlparse(href)
            params = dict(parse_qsl(parsed.query, keep_blank_values=True))
            expansion = params.get('expansion', '').strip()
            if is_expansion_code(expansion):
                codes.add(expansion)
    for opt in soup.find_all('option'):
        value = opt.get('value', '').strip()
        if is_expansion_code(value):
            codes.add(value)
    return sorted(codes)


def clean_name(name_text):
    return re.sub(r'^\s*【.*?】\s*', '', name_text).strip()


def normalize_card_record(card):
    normalized = dict(card)
    normalized['name'] = clean_name(normalized.get('name', ''))

    ability_lines = normalized.get('ability_lines', []) or []
    # 保留原始版本（可能已經部分替換標記，但盡量還原）
    ability_lines_raw = [restore_ja_tags(line) for line in ability_lines]
    special_ability = normalized.get('special_ability_ja') or ' '.join(ability_lines_raw)
    if not special_ability.strip() or special_ability.strip() == '-':
        special_ability = '無特殊能力 (白板卡)'

    ap_bonus = re.findall(r'AP\s*[＋+]\s*(\d+)', special_ability)
    dp_bonus = re.findall(r'DP\s*[＋+]\s*(\d+)', special_ability)

    tag_notes = normalized.get('ability_tag_notes') or []
    if not tag_notes:
        # 用翻譯後的標記版本來生成說明
        for line in ability_lines:
            tag_notes.extend(explain_tags(translate_line_tags(line)))
        tag_notes = list(dict.fromkeys(tag_notes))

    normalized['ability_lines_raw'] = ability_lines_raw
    normalized['special_ability_ja'] = special_ability
    normalized['ability_tag_notes'] = tag_notes
    normalized['detected_ap'] = normalized.get('detected_ap') or (f'+{ap_bonus[0]}' if ap_bonus else '依效果判定')
    normalized['detected_dp'] = normalized.get('detected_dp') or (f'+{dp_bonus[0]}' if dp_bonus else '依效果判定')
    normalized['team_zh'] = normalized.get('team_zh', TEAM_MAP.get(normalized.get('team', ''), ''))
    return normalized


def normalize_text(text):
    if not text:
        return ''
    return text.replace('\u3000', ' ').replace('　', ' ').strip().lower()


def extract_ability_lines(info_div):
    if not info_div:
        return []

    segments = []
    current = ""

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
                current = ""
        elif getattr(node, 'name', None) in ['p', 'div']:
            if current.strip():
                # Keep paragraph boundaries if there is actual content.
                segments.append(re.sub(r'\s+', ' ', current).strip())
                current = ""
        elif isinstance(node, str):
            text = node.strip()
            if text:
                if current and not current.endswith(' '):
                    current += ' '
                current += text

    if current.strip():
        segments.append(re.sub(r'\s+', ' ', current).strip())
    return [seg for seg in segments if seg and seg != '詳細を見る']


def explain_tags(text):
    notes = []
    for tag, note in TAG_EXPLANATION_MAP.items():
        if tag in text:
            notes.append(note)
    return notes


def translate_line_tags(line):
    for tag, zh in ICON_TAG_MAP.items():
        line = line.replace(tag, zh)
    return line


def restore_ja_tags(line):
    for zh, ja in ZH_TO_JA_TAG_MAP.items():
        line = line.replace(zh, ja)
    return line


def translate_lines(translator, lines):
    if not lines:
        return []

    import time
    # 逐句翻譯（googletrans 批量翻譯有 bug）
    translated_lines = []
    for line in lines:
        for attempt in range(3):
            try:
                # 每次翻譯前稍微延遲，避免 rate limit
                time.sleep(0.5)
                # 逐句用 Google Translate 翻譯
                result = translator.translate(line, src='ja', dest='zh-tw')
                translated_text = result.text if hasattr(result, 'text') else str(result)
                # 翻譯後再把標記換成中文版本（以防 Google 翻得不準）
                translated_lines.append(translate_line_tags(translated_text))
                break  # 成功就跳出重試循環
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.0)  # 失敗後等待更久再重試
                    continue
                # 最後一次失敗，使用只替換標記的版本
                st.warning(f"⚠️ 翻譯失敗：{str(e)[:50]}...，此句顯示標記中文化的原文。")
                translated_lines.append(translate_line_tags(line))
                break
    
    return translated_lines if translated_lines else None


def get_all_expansion_codes():
    base = 'https://dreamorder.com/cardlist/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(base, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception:
        return sorted(KNOWN_EXPANSION_CODES)

    soup = BeautifulSoup(response.text, 'html.parser')
    codes = parse_expansion_codes_from_soup(soup)
    if len(codes) < len(KNOWN_EXPANSION_CODES):
        codes = sorted(set(codes) | set(KNOWN_EXPANSION_CODES))

    return sorted(codes)


def get_all_expansion_urls():
    return [make_expansion_page_url(code, 1) for code in get_all_expansion_codes()]


def get_max_page_from_html(html_text):
    match = re.search(r'max_page\s*=\s*(\d+)', html_text)
    if match:
        return int(match.group(1))
    return 1


def make_expansion_page_url(expansion, page_number):
    query = urlencode({
        'expansion': expansion,
        'view': 'text',
        'page': page_number
    })
    return f'https://dreamorder.com/cardlist/searchresults_ex?{query}'


@st.cache_data(ttl=3600)
def fetch_and_parse_cards():
    expansion_urls = get_all_expansion_urls()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    card_database = []

    for expansion_url in expansion_urls:
        parsed = urlparse(expansion_url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        expansion_value = params.get('expansion', '')
        if expansion_value == '':
            continue

        page_number = 1
        while page_number <= 250:
            page_url = make_expansion_page_url(expansion_value, page_number)
            response = None
            for attempt in range(3):
                try:
                    response = requests.get(page_url, headers=headers, timeout=20)
                    if response.status_code == 404:
                        break
                    response.raise_for_status()
                    break
                except requests.RequestException:
                    if attempt < 2:
                        time.sleep(1)
                        continue
                    response = None

            if not response or response.status_code == 404:
                break

            page_soup = BeautifulSoup(response.text, 'html.parser')
            page_items = page_soup.select('li.list-Item')
            if not page_items:
                break

            for item in page_items:
                card_id_tag = item.select_one('p.info-Number')
                card_name_tag = item.select_one('p.info-Name')
                type_spans = [span.get_text(strip=True) for span in item.select('p.info-Types span')]
                info_text = item.select_one('div.info-Text')
                img_tag = item.select_one('div.item-Image img')

                if not card_id_tag or not card_name_tag:
                    continue

                card_id = card_id_tag.get_text(strip=True)

                player_name = clean_name(card_name_tag.get_text(strip=True))
                team_name = type_spans[0] if len(type_spans) > 0 else '其他/戰術卡'
                position = POSITION_MAP.get(type_spans[1], type_spans[1]) if len(type_spans) > 1 else '無'
                card_type = TYPE_MAP.get(type_spans[2], type_spans[2]) if len(type_spans) > 2 else '其他'
                rarity = type_spans[3] if len(type_spans) > 3 else 'C'

                ability_lines = extract_ability_lines(info_text)
                special_ability = ' '.join(ability_lines) if ability_lines else '無特殊能力'
                if special_ability.strip() == '' or special_ability.strip() == '-':
                    special_ability = '無特殊能力 (白板卡)'

                ap_bonus = re.findall(r'AP\s*[＋+]\s*(\d+)', special_ability)
                dp_bonus = re.findall(r'DP\s*[＋+]\s*(\d+)', special_ability)

                img_url = urljoin('https://dreamorder.com/', img_tag.get('src')) if img_tag and img_tag.get('src') else ''
                tag_notes = []
                for line in ability_lines:
                    tag_notes.extend(explain_tags(line))
                tag_notes = list(dict.fromkeys(tag_notes))

                card_database.append(normalize_card_record({
                    'id': card_id,
                    'expansion': expansion_value,
                    'name': player_name,
                    'team': team_name,
                    'team_zh': TEAM_MAP.get(team_name, ''),
                    'position': position,
                    'type': card_type,
                    'rarity': rarity,
                    'special_ability_ja': special_ability,
                    'ability_lines': ability_lines,
                    'ability_tag_notes': tag_notes,
                    'image_url': img_url,
                    'detected_ap': f'+{ap_bonus[0]}' if ap_bonus else '依效果判定',
                    'detected_dp': f'+{dp_bonus[0]}' if dp_bonus else '依效果判定'
                }))

            page_number += 1

    return card_database

# 3. 前端網頁佈局
st.title("⚾ 日職 Dream Order TCG 全屬性智能翻譯系統")
st.caption(f"Version {VERSION} | Dream Order 卡片查詢與即時翻譯工具")
st.markdown("本系統已將官網數據全面**結構化解析**，拆解出 **AP/DP/球隊/守備位置/卡片類型/稀有度** 並完成中文化。")

cache_loaded = False
cache_source = 'local'
cache_load_start = time.perf_counter()
db = load_local_card_cache()
cache_load_ms = (time.perf_counter() - cache_load_start) * 1000

if db:
    cache_loaded = True
    st.success(f"✅ 已載入本地快取資料，共 {len(db)} 張卡片。若要更新資料，請按右側按鈕。")
    st.caption(f"快取載入 {cache_load_ms:.2f} ms")
    if len(db) < 5153:
        st.warning("本地快取數量少於預期，將自動從官網重新抓取完整資料。請稍候...")
        cache_source = 'remote'
        with st.spinner("正在從官網抓取完整卡片資料並更新本地快取..."):
            fetch_and_parse_cards.clear()
            db = fetch_and_parse_cards()
            if db:
                save_local_card_cache(db)
                cache_loaded = True
                st.success(f"✅ 已重新抓取並更新本地快取，共 {len(db)} 張卡片。")
else:
    cache_source = 'remote'
    with st.spinner("本地快取不存在，正在從官網抓取並建立快取..."):
        fetch_and_parse_cards.clear()
        db = fetch_and_parse_cards()
        if db:
            save_local_card_cache(db)

refresh = st.button("🔄 重新抓取並更新本地快取", use_container_width=True)
if refresh:
    with st.spinner("正在從官網重新抓取最新資料並更新本地快取..."):
        fetch_and_parse_cards.clear()
        db = fetch_and_parse_cards()
        if db:
            save_local_card_cache(db)
            cache_loaded = True
            cache_source = 'remote'
            st.success(f"✅ 已重新抓取並更新本地快取，共 {len(db)} 張卡片。")

if not db:
    st.error("連線失敗或本地快取無效，請檢查網路或重新整理。")
else:
    if cache_source == 'local' and cache_loaded:
        st.info("目前顯示的是本地快取資料。若需要最新卡片請按『重新抓取並更新本地快取』。")
    st.success(f"📊 成功解析並結構化 {len(db)} 張官方卡片全能力欄位！")

    # 搜尋組件
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("💡 請輸入欲查詢的【卡片編號】或【球員日文/中文名字】", placeholder="例如: BP02-T04 或 森下 翔太").strip()
    with col2:
        st.write("")
        st.write("")
        search_button = st.button("🔍 智能檢索", use_container_width=True)

    if search_button or query:
        if not query:
            st.warning("請先輸入搜尋關鍵字。")
        else:
            query_lower = query.lower()
            # 模糊搜尋包含卡號、名字或球隊
            results = [c for c in db if query_lower in c['id'].lower()
                       or query in c['name']
                       or query in c['team']
                       or query in c.get('team_zh', '')
                       or query in c.get('special_ability_ja', '')]
            
            # 去重複：相同卡片編號只保留第一個（能力相同的平行卡）
            seen_ids = set()
            unique_results = []
            for card in results:
                card_base_id = card['id'].split('-')[0] + '-' + card['id'].split('-')[1] if '-' in card['id'] else card['id']
                if card_base_id not in seen_ids:
                    seen_ids.add(card_base_id)
                    unique_results.append(card)
            results = unique_results
            
            if not results:
                st.info("找不到符合條件的卡牌。")
            else:
                st.subheader(f"🎯 為您尋找到 {len(results)} 筆精確卡牌報告：")
                translator = get_translator()
                
                for card_idx, res in enumerate(results):
                    # 展開卡片標題顯示： [卡號] 球員名 (稀有度)
                    expansion_label = res.get('expansion', '未知卡池')
                    # 只展開第一張卡片，其他卡片收起，避免同時渲染造成狀態混亂
                    is_first_card = (card_idx == 0)
                    with st.expander(f"【{res['id']}】 {res['name']} （{res['rarity']} / {expansion_label}）", expanded=is_first_card):
                        
                        # 使用唯一容器確保每張卡片完全獨立
                        card_container = st.container()
                        
                        with card_container:
                            # 重要：每張卡片都獨立處理，避免變數殘留
                            card_original_lines = res.get('ability_lines_raw', res.get('ability_lines', []))
                            card_trans_team = res.get('team_zh', res['team'])
                            
                            # 只在第一張卡片時才即時翻譯，其他卡片延遲翻譯以加速載入
                            if is_first_card:
                                with st.spinner("正在即時翻譯特殊能力說明..."):
                                    try:
                                        import time
                                        time.sleep(0.3)  # 稍微延遲避免 rate limit
                                        card_trans_team = translator.translate(res['team'], src='ja', dest='zh-tw').text
                                        if not card_trans_team:
                                            card_trans_team = res.get('team_zh', res['team'])
                                    except Exception:
                                        card_trans_team = res.get('team_zh', res['team'])
                                    
                                    # 用原始日文版本翻譯
                                    card_translated_lines = translate_lines(translator, card_original_lines)
                                    
                                    # 如果翻譯失敗，使用僅替換標記的版本
                                    if card_translated_lines is None or len(card_translated_lines) == 0:
                                        card_translated_lines = [translate_line_tags(line) for line in card_original_lines]
                                        st.error("❌ 無法連接到 Google 翻譯服務，僅顯示標記中文化的日文原文。")
                            else:
                                # 非第一張卡片：按需翻譯（用戶展開時才翻譯）
                                card_translated_lines = None
                            
                            # 分配網頁排版 (左：官方卡面 | 右：完整拆分資料卡)
                            idx_img, idx_info = st.columns([1, 2])
                        
                        with idx_img:
                            if res['image_url']:
                                st.image(res['image_url'], caption=f"官方卡面：{res['id']}", width=260)
                            else:
                                st.caption("（官方此卡無提供純文字模式圖片）")
                                
                        with idx_info:
                            # 透過 Streamlit Badge 與 Markdown 漂亮呈現所有屬性
                            st.markdown(f"### 📋 卡片基礎資訊")
                            
                            # 第一排：基本背景
                            c1, c2, c3 = st.columns(3)
                            c1.metric(label="所屬球隊", value=card_trans_team)
                            c2.metric(label="卡片類型", value="選手卡" if res['type']=="選手" else res['type'])
                            c3.metric(label="守備位置", value=res['position'])
                            
                            # 第二排：基本能力數值（從卡片效果加成中自動提取）
                            c4, c5, c6 = st.columns(3)
                            c4.metric(label="卡片稀有度", value=res['rarity'])
                            c5.metric(label="AP 基本加成", value=res.get('detected_ap', '依效果判定'))
                            c6.metric(label="DP 基本加成", value=res.get('detected_dp', '依效果判定'))
                            
                            st.write("---")
                            # 第三排：特殊能力與效果說明
                            st.markdown(f"### ⚡ 特殊能力與效果說明")
                            
                            # 為每張卡片的 tabs 創建獨立內容（避免狀態混亂）
                            tab_zh, tab_ja = st.tabs(["🇹🇼 繁體中文翻譯效果", "🇯🇵 日文官方原文"])
                            
                            with tab_zh:
                                # 使用 empty 確保內容完全重新渲染
                                zh_content = st.empty()
                                with zh_content.container():
                                    # 如果尚未翻譯，現在翻譯
                                    if card_translated_lines is None:
                                        with st.spinner("正在翻譯..."):
                                            try:
                                                import time
                                                time.sleep(0.3)
                                                card_trans_team = translator.translate(res['team'], src='ja', dest='zh-tw').text
                                            except Exception:
                                                pass
                                            card_translated_lines = translate_lines(translator, card_original_lines)
                                            if card_translated_lines is None or len(card_translated_lines) == 0:
                                                card_translated_lines = [translate_line_tags(line) for line in card_original_lines]
                                    
                                    for idx, line in enumerate(card_translated_lines, 1):
                                        st.markdown(f"**{idx}.** {line}")
                                    if res.get('ability_tag_notes'):
                                        st.markdown("#### 能力標記說明")
                                        for note in res['ability_tag_notes']:
                                            st.write(f"- {note}")
                            
                            with tab_ja:
                                # 使用 empty 確保內容完全重新渲染
                                ja_content = st.empty()
                                with ja_content.container():
                                    # 顯示完全原始的日文（不含任何中文標記）
                                    for idx, line in enumerate(card_original_lines, 1):
                                        st.markdown(f"**{idx}.** {line}")
                                    if res.get('ability_tag_notes'):
                                        st.markdown("#### 能力標記說明")
                                        for note in res['ability_tag_notes']:
                                            st.write(f"- {note}")
                                
                        time.sleep(0.05)