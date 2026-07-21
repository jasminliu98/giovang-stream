import requests
import json
import hashlib
import re
import time
import os
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ─────────────────────────────────────────────────────────────────────────────
# TIMEZONE & HELPERS
# ─────────────────────────────────────────────────────────────────────────────

VN_TZ       = timezone(timedelta(hours=7))

def now_vn() -> datetime:
    return datetime.now(tz=VN_TZ)

def parse_kickoff(time_str: str, date_str: str = ""):
    if not time_str or not time_str.strip():
        return None
    t = time_str.strip()
    d = date_str.strip() if date_str else ""
    today = now_vn()
    year = today.year

    try:
        hh, mm = int(t.split(":")[0]), int(t.split(":")[1])
    except Exception:
        return None

    if d:
        m3 = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
        if m3:
            try: return datetime(int(m3.group(3)), int(m3.group(2)), int(m3.group(1)), hh, mm, tzinfo=VN_TZ)
            except ValueError: pass
        m2 = re.match(r"(\d{1,2})/(\d{1,2})$", d)
        if m2:
            try: return datetime(year, int(m2.group(2)), int(m2.group(1)), hh, mm, tzinfo=VN_TZ)
            except ValueError: pass

    try:
        return datetime(today.year, today.month, today.day, hh, mm, tzinfo=VN_TZ)
    except ValueError:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":    "https://giovang.store/",
}

API_LIVE      = "https://live-api.keovip88.net/storage/livestream/live.json"
API_ALL       = "https://live-api.keovip88.net/storage/livestream/all.json"
API_FIXTURES  = "https://live-api.keovip88.net/api/fixtures/"

THUMBS_DIR    = "thumbs"
REPO_RAW      = os.environ.get("REPO_RAW", "")
THUMB_VERSION = "v1"

CATE_MAP = {
    "football": "⚽ Bóng Đá", "basketball": "🏀 Bóng Rổ", "tennis": "🎾 Tennis",
    "bongchuyen": "🏐 Bóng Chuyền", "esport": "🎮 Esport", "caulong": "🏸 Cầu Lông",
    "vothuat": "🥊 Võ Thuật", "bongchay": "⚾ Bóng Chày", "duaxe": "🏎️ Đua Xe",
}
CATE_ORDER = ["football", "basketball", "tennis", "bongchuyen", "esport", "caulong", "vothuat", "bongchay", "duaxe"]

MOTORSPORT_KW = ["formula", "f1", "grand prix", "motogp", "nascar", "indycar", "đua xe"]
EXCLUDE_LEAGUES_AMERICA = [
    "mls", "major league soccer", "liga mx", "brasileirao", "brasileirão", "serie a brasil",
    "campeonato brasileiro", "copa do brasil", "argentine", "argentina", "liga profesional",
    "colombian", "colombia", "liga betplay", "chile", "ecuador", "peru", "venezuela",
    "paraguay", "uruguay", "bolivia", "inter miami", "la galaxy", "concacaf", "conmebol",
    "copa america", "copa sudamericana", "copa libertadores",
]

def is_america_league(league_name: str) -> bool:
    return any(kw in league_name.lower() for kw in EXCLUDE_LEAGUES_AMERICA)

def make_id(text, prefix):
    return f"{prefix}-{hashlib.md5(text.encode()).hexdigest()[:10]}"

def fetch_image(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        res.raise_for_status()
        return Image.open(BytesIO(res.content)).convert("RGBA")
    except Exception:
        return None

def parse_time_sort(time_str: str, date_str: str) -> int:
    kickoff = parse_kickoff(time_str, date_str)
    if kickoff:
        return kickoff.month * 10_000_000 + kickoff.day * 10_000 + kickoff.hour * 100 + kickoff.minute
    return 999_999_999

def format_time_hhmm(time_str: str) -> str:
    if not time_str: return ""
    parts = time_str.strip().split(":")
    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}" if len(parts) >= 2 else time_str.strip()

def format_date_ddmm(date_str: str) -> str:
    if not date_str: return ""
    d = date_str.strip()
    m = re.match(r"(\d{1,2})[-/](\d{1,2})(?:[-/]\d{4})?", d)
    return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}" if m else d

def get_stream_type(url: str) -> str:
    if not url: return "hls"
    clean_url = url.lower().split("?")[0]
    if clean_url.endswith(".flv"): return "httpflv"
    if clean_url.endswith(".mpd"): return "dash"
    if clean_url.endswith(".mp4"): return "mp4"
    return "hls"

# ─────────────────────────────────────────────────────────────────────────────
# BLV MAPPING
# ─────────────────────────────────────────────────────────────────────────────

BLV_NAME_MAP = {
    "blv-perry": "BLV Perry", "blv-1": "BLV Ngỗng", "blv-ngong": "BLV Ngỗng",
    "blv-3": "BLV Dần", "blv-5": "BLV Thìn", "blv-6": "BLV Tỵ", "blv-12": "BLV Hợi",
    "blv-tom": "BLV Tôm", "blv-ben": "BLV Ben", "blv-cay": "BLV Cầy", "blv-bang": "BLV Băng",
    "blv-mason": "BLV Mason", "blv-cam": "BLV Câm", "blv-dory": "BLV Dory", "blv-chanh": "BLV Chanh",
    "blv-nen": "BLV Nến", "blv-diec": "BLV Điếc", "blv-thuviec": "BLV Thử Việc",
    "blv-bon": "BLV Bón", "blv-ngu": "BLV Ngủ", "blv-tri": "BLV Trĩ", "blv-sun": "BLV Sún",
    "blv-can": "BLV Cần", "blv-mat": "BLV Mát", "blv Mù": "BLV Mù",
    "fan-liver": "Fan Liver: Thìn + Tỵ", "fan-mu-perry-cam": "Fan MU: Perry vs Câm",
    "fan-psg": "Fan PSG: Câm + Bin", "fan-bayern": "Fan Chè: Điếc",
    "nha-dai": "Nhà Đài", "mason-mat": "Mason vs Mát", "leo-mason": "Leo + Mason",
    "bon-tri": "Bón + Trĩ", "can-ngu": "Cần + Ngủ", "ben-dory": "Ben + Dory",
    "tri-ngong": "Trĩ + Ngỗng", "leo-dory": "Leo + Dory", "hoi-ngong": "Hỏi + Ngỗng",
    "mat-mason": "Mát + Mason", "dory-leo": "Dory + Leo", "leo": "Leo",
}

def get_blv_display_name(blv_key: str) -> str:
    if not blv_key: return "BLV Không Tên"
    return BLV_NAME_MAP.get(blv_key, blv_key.replace("blv-", "BLV ").title())

# ─────────────────────────────────────────────────────────────────────────────
# THUMBNAIL (ĐÃ SỬA LỖI PASTE ẢNH)
# ─────────────────────────────────────────────────────────────────────────────

def make_thumbnail(match, match_id_safe):
    os.makedirs(THUMBS_DIR, exist_ok=True)
    cache_key = match.get("logo_a", "") + match.get("logo_b", "") + THUMB_VERSION
    logo_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]
    date_str = now_vn().strftime("%Y%m%d")
    
    out_path = f"{THUMBS_DIR}/{match_id_safe}_{logo_hash}_{date_str}.png"
    if os.path.exists(out_path):
        return out_path

    W, H = 1600, 1200
    HEADER_H, FOOTER_H = 180, 160
    bg = Image.new("RGB", (W, H), (245, 245, 248))
    draw = ImageDraw.Draw(bg)

    for y in range(HEADER_H, H - FOOTER_H):
        ratio = (y - HEADER_H) / (H - FOOTER_H - HEADER_H)
        draw.line([(0, y), (W, y)], fill=(int(248 - ratio * 18),) * 3)

    draw.rectangle([(0, 0), (W, HEADER_H)], fill=(13, 20, 40))
    draw.rectangle([(0, H - FOOTER_H), (W, H)], fill=(13, 20, 40))
    draw.rectangle([(0, HEADER_H), (W, HEADER_H + 5)], fill=(220, 30, 40))
    draw.rectangle([(0, H - FOOTER_H - 5), (W, H - FOOTER_H)], fill=(220, 30, 40))

    FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font_vs = ImageFont.truetype(FONT_BOLD, 160)
        font_time = ImageFont.truetype(FONT_BOLD, 100)
        font_team = ImageFont.truetype(FONT_BOLD, 58)
    except Exception:
        font_vs = font_time = font_team = ImageFont.load_default()

    logo_size = 360
    logo_y = HEADER_H + 40
    name_center = logo_y + logo_size + 80
    time_y = name_center + 80

    for side, team_key, logo_key in [(W // 4, "team_a", "logo_a"), (W * 3 // 4, "team_b", "logo_b")]:
        if match.get(logo_key):
            img = fetch_image(match[logo_key])
            if img:
                try:
                    # SỬA LỖI: Gán ảnh đã resize vào biến, dùng chính nó làm mask để tránh lỗi "images do not match"
                    resized_img = img.resize((logo_size, logo_size), Image.LANCZOS)
                    bg.paste(resized_img, (side - logo_size // 2, logo_y), resized_img)
                except Exception:
                    pass # Bỏ qua nếu ảnh lỗi, không làm crash toàn bộ script

        if match.get(team_key):
            draw.text((side, name_center), match[team_key], fill=(20, 20, 20), font=font_team, anchor="mm")

    draw.text((W // 2, logo_y + logo_size // 2), "VS", fill=(220, 30, 40), font=font_vs, anchor="mm")

    time_fmt = format_time_hhmm(match.get("time", ""))
    date_fmt = format_date_ddmm(match.get("date", ""))
    time_display = f"{time_fmt} {date_fmt}" if time_fmt and date_fmt else (time_fmt or "")
    if time_display:
        draw.text((W // 2, time_y), time_display, fill=(15, 15, 15), font=font_time, anchor="mm")

    if match.get("league"):
        draw.text((W // 2, HEADER_H // 2), match["league"].upper(), fill=(255, 255, 255), font=font_team, anchor="mm")

    draw.rectangle([(0, 0), (W - 1, H - 1)], outline=(180, 180, 180), width=3)
    bg.save(out_path, "PNG", optimize=True)
    return out_path

def cleanup_old_thumbs(days: int = 3):
    if not os.path.exists(THUMBS_DIR): return
    cutoff = now_vn() - timedelta(days=days)
    for fname in os.listdir(THUMBS_DIR):
        if not fname.endswith(".png"): continue
        m = re.search(r'_(\d{8})\.png$', fname)
        if m:
            try:
                if datetime.strptime(m.group(1), "%Y%m%d").replace(tzinfo=VN_TZ) < cutoff:
                    os.remove(os.path.join(THUMBS_DIR, fname))
            except Exception: pass

# ─────────────────────────────────────────────────────────────────────────────
# FETCH & GROUP LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def fetch_json(url: str) -> list:
    try:
        res = requests.get(f"{url}?t={int(time.time() * 1000)}", headers=HEADERS, timeout=15)
        data = res.json()
        return data.get("response", []) if isinstance(data, dict) else []
    except Exception as e:
        print(f"  Loi fetch {url}: {e}")
        return []

def get_grouped_matches() -> dict:
    live_items = fetch_json(API_LIVE)
    all_items = fetch_json(API_ALL)

    seen = {}
    for item in live_items:
        if item.get("id"):
            seen[item.get("id")] = item
    for item in all_items:
        if item.get("id") and item.get("id") not in seen:
            seen[item.get("id")] = item

    grouped = {}
    now = now_vn()

    for item in seen.values():
        match_id = str(item.get("id", ""))
        status_code = item.get("status_code", "NS")
        is_live_api = item.get("is_live", False) or status_code in {"1H", "2H", "HT", "PEN", "LIVE", "ET"}

        if not match_id or status_code == "FT":
            continue

        league_obj = item.get("league") or {}
        league_name = league_obj.get("title", "")
        teams = item.get("teams") or {}
        team_a = teams.get("home", {}).get("name", "").strip()
        team_b = teams.get("away", {}).get("name", "").strip()
        
        if not team_a or not team_b:
            continue

        raw_type = item.get("type", "football")
        if any(kw in (league_name + " " + team_a + " " + team_b).lower() for kw in MOTORSPORT_KW):
            cate_type = "duaxe"
        else:
            cate_type = raw_type

        if cate_type == "football" and is_america_league(league_name):
            continue

        time_str = item.get("time", "")
        date_str = item.get("day_month", "")
        
        # Chỉ lọc thời gian nếu KHÔNG phải trận đang LIVE
        if not is_live_api:
            kickoff = parse_kickoff(time_str, date_str)
            if kickoff:
                if now > kickoff + timedelta(hours=6):
                    continue
                if kickoff > now + timedelta(hours=48):
                    continue

        blv_keys = [b for b in (item.get("blv") or []) if b != "nha-dai" and isinstance(b, str)]

        if match_id not in grouped:
            grouped[match_id] = {
                "match_id": match_id,
                "cate_type": cate_type,
                "name": f"{team_a} vs {team_b}",
                "time": time_str,
                "date": date_str,
                "time_sort": parse_time_sort(time_str, date_str),
                "team_a": team_a,
                "team_b": team_b,
                "logo_a": teams.get("home", {}).get("logo", ""),
                "logo_b": teams.get("away", {}).get("logo", ""),
                "league": league_name,
                "is_live": is_live_api,
                "blvs_dict": {},
                "_blv_keys": blv_keys
            }
        else:
            if is_live_api:
                grouped[match_id]["is_live"] = True
            grouped[match_id]["_blv_keys"] = list(set(grouped[match_id]["_blv_keys"] + blv_keys))

    for match_id, match_data in grouped.items():
        try:
            url = f"{API_FIXTURES}/{match_id}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            data = res.json()
            fixture_data = data.get("response", {}) if isinstance(data, dict) else {}
            
            if isinstance(fixture_data, dict):
                api_blv_list = fixture_data.get("blv", [])
                stream_keys = ["link_stream_hd", "pc_stream_url", "mobile_stream_url", "link_stream_sd"]
                
                for blv in api_blv_list:
                    if isinstance(blv, dict):
                        blv_key = blv.get("blv_key") or blv.get("key") or blv.get("id") or "unknown"
                        blv_name = blv.get("blv_name") or get_blv_display_name(blv_key)
                        
                        valid_keys = match_data.get("_blv_keys", [])
                        if blv_key != "unknown" and valid_keys and blv_key not in valid_keys:
                            continue
                            
                        stream_url = next((blv.get(k) for k in stream_keys if blv.get(k) and isinstance(blv.get(k), str)), None)
                        
                        if stream_url:
                            if blv_name not in match_data["blvs_dict"]:
                                match_data["blvs_dict"][blv_name] = []
                            if stream_url not in match_data["blvs_dict"][blv_name]:
                                match_data["blvs_dict"][blv_name].append(stream_url)
        except Exception:
            pass
            
        match_data.pop("_blv_keys", None)

    return grouped

# ─────────────────────────────────────────────────────────────────────────────
# BUILD CHANNEL JSON
# ─────────────────────────────────────────────────────────────────────────────

def build_channel(match: dict, match_id_safe: str, thumb_url: str = "") -> dict:
    uid = make_id(match_id_safe, "gv")
    src_id = make_id(match_id_safe, "src")
    ct_id = make_id(match_id_safe, "ct")
    st_id = make_id(match_id_safe, "st")

    stream_links = []
    for blv_name, urls in match["blvs_dict"].items():
        for idx, s_url in enumerate(urls):
            name = f"{blv_name} {idx + 1}" if len(urls) > 1 else blv_name
            
            stream_links.append({
                "id": make_id(s_url + str(idx), "lnk"),
                "name": name,
                "type": get_stream_type(s_url),
                "default": len(stream_links) == 0,
                "url": s_url,
                "request_headers": [
                    {"key": "Referer", "value": "https://giovang.store/"},
                    {"key": "User-Agent", "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                ],
            })

    label_text = "● LIVE" if match["is_live"] else "🕐 Sắp"
    label_color = "#ff4444" if match["is_live"] else "#aaaaaa"

    time_fmt = format_time_hhmm(match["time"])
    date_fmt = format_date_ddmm(match["date"])
    display_name = f"{match['name']} | {time_fmt} {date_fmt}" if time_fmt and date_fmt else (f"{match['name']} | {time_fmt}" if time_fmt else match["name"])

    channel = {
        "id": uid,
        "name": display_name,
        "type": "single",
        "display": "thumbnail-only",
        "enable_detail": False,
        "labels": [{"text": label_text, "position": "top-left", "color": "#00000080", "text_color": label_color}],
        "sources": [{
            "id": src_id,
            "name": "GiovangTV",
            "contents": [{
                "id": ct_id,
                "name": match["name"],
                "streams": [{"id": st_id, "name": "GV", "stream_links": stream_links}],
            }],
        }],
        "org_metadata": {
            "league": match.get("league", ""),
            "team_a": match.get("team_a", ""),
            "team_b": match.get("team_b", ""),
            "logo_a": match.get("logo_a", ""),
            "logo_b": match.get("logo_b", ""),
            "time": match.get("time", ""),
            "date": match.get("date", ""),
            "blv": ", ".join(match["blvs_dict"].keys()),
            "is_live": match["is_live"],
            "cate_type": match.get("cate_type", ""),
        },
    }

    if thumb_url:
        channel["image"] = {
            "padding": 1, "background_color": "#ffffff", "display": "contain",
            "url": thumb_url, "width": 1600, "height": 1200,
        }

    return channel

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(THUMBS_DIR, exist_ok=True)
    cleanup_old_thumbs(days=3)
    print(f"Gio VN hien tai : {now_vn().strftime('%H:%M %d/%m/%Y')}")
    print("Lay & gom nhom tran dau tu GiovangTV API...")

    grouped_matches = get_grouped_matches()
    matches_list = list(grouped_matches.values())
    
    matches_list.sort(key=lambda m: (0 if m["is_live"] else 1, m["time_sort"]))

    live_count = sum(1 for m in matches_list if m["is_live"])
    print(f"Tong: {len(matches_list)} | LIVE: {live_count} | Sap: {len(matches_list) - live_count}\n")

    cate_channels = {cate: [] for cate in CATE_ORDER}

    for i, match in enumerate(matches_list):
        match_id_safe = match["match_id"].replace(":", "-").replace("/", "-")
        status = "LIVE" if match["is_live"] else "SAP"
        log_time = format_time_hhmm(match['time'])
        log_date = format_date_ddmm(match['date'])
        blv_str = ", ".join(match["blvs_dict"].keys()) if match["blvs_dict"] else "Khong co link"
        
        print(f"[{status} {i+1}/{len(matches_list)}] {match['name']} ({log_time} {log_date}) | BLV: {blv_str}")

        thumb_path = make_thumbnail(match, match_id_safe)
        cache_key = match.get("logo_a", "") + match.get("logo_b", "") + THUMB_VERSION
        logo_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]
        thumb_url = f"{REPO_RAW}/{thumb_path}?v={logo_hash}" if REPO_RAW else ""

        channel = build_channel(match, match_id_safe, thumb_url)

        cate_type = match["cate_type"]
        if cate_type not in cate_channels:
            cate_channels[cate_type] = []
        cate_channels[cate_type].append(channel)

        time.sleep(0.15)

    groups = []
    for cate_type in CATE_ORDER:
        channels = cate_channels.get(cate_type, [])
        if not channels: continue
        cate_label = CATE_MAP.get(cate_type, "🏅 Thể Thao")
        live_cnt = sum(1 for ch in channels if ch.get("org_metadata", {}).get("is_live", False))
        cate_name = f"{cate_label} ({live_cnt} LIVE)" if live_cnt > 0 else cate_label

        groups.append({
            "id": f"cate_{cate_type}", "name": cate_name, "display": "vertical",
            "grid_number": 2, "enable_detail": False, "channels": channels,
        })

    for cate_type, channels in cate_channels.items():
        if cate_type not in CATE_ORDER and channels:
            live_cnt = sum(1 for ch in channels if ch.get("org_metadata", {}).get("is_live", False))
            groups.append({
                "id": f"cate_{cate_type}", "name": f"🏅 Thể Thao ({live_cnt} LIVE)" if live_cnt > 0 else "🏅 Thể Thao",
                "display": "vertical", "grid_number": 2, "enable_detail": False, "channels": channels,
            })

    output = {
        "id": "giovang", "url": "https://giovang.store", "name": "GiovangTV",
        "color": "#0155a5", "grid_number": 3,
        "image": {"type": "cover", "url": "https://giovang.fun/wp-content/uploads/2024/10/GiovangTV_logo-01-1.png"},
        "groups": groups,
    }

    staging = "output_staging.json"
    with open(staging, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = sum(len(g["channels"]) for g in groups)

    def normalize(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.dumps(json.load(f), sort_keys=True, ensure_ascii=False)
        except Exception:
            return ""

    if normalize("output.json") != normalize(staging):
        os.replace(staging, "output.json")
        print(f"\n✅ Xong! {total} kenh, {len(groups)} mon the thao -> output.json (DA CAP NHAT)")
    else:
        os.remove(staging)
        print(f"\n✅ Xong! {total} kenh, {len(groups)} mon the thao -> Khong co thay doi, giu nguyen output.json")

if __name__ == "__main__":
    main()
