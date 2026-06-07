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
# TIMEZONE
# ─────────────────────────────────────────────────────────────────────────────

VN_TZ       = timezone(timedelta(hours=7))
LIVE_BEFORE = timedelta(minutes=15)


def now_vn() -> datetime:
    return datetime.now(tz=VN_TZ)


def parse_kickoff(time_str: str, date_str: str = ""):
    if not time_str or not time_str.strip():
        return None

    t = time_str.strip()
    d = date_str.strip() if date_str else ""
    today = now_vn()
    year  = today.year

    try:
        hh, mm = int(t.split(":")[0]), int(t.split(":")[1])
    except Exception:
        return None

    if d:
        m3 = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
        if m3:
            try:
                return datetime(int(m3.group(3)), int(m3.group(2)), int(m3.group(1)), hh, mm, tzinfo=VN_TZ)
            except ValueError:
                pass
        m2 = re.match(r"(\d{1,2})/(\d{1,2})$", d)
        if m2:
            try:
                return datetime(year, int(m2.group(2)), int(m2.group(1)), hh, mm, tzinfo=VN_TZ)
            except ValueError:
                pass

    try:
        return datetime(today.year, today.month, today.day, hh, mm, tzinfo=VN_TZ)
    except ValueError:
        return None


def calc_is_live(status_code: str, time_str: str, date_str: str) -> bool:
    live_codes = {"1H", "2H", "HT", "PEN", "LIVE", "ET"}
    if status_code in live_codes:
        return True
    kickoff = parse_kickoff(time_str, date_str)
    if kickoff is None:
        return False
    now = now_vn()
    return now >= (kickoff - LIVE_BEFORE)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":    "https://giovang.fun/",
}

BASE_URL      = "https://giovang.fun"
API_LIVE      = "https://live-api.keovip88.net/storage/livestream/live.json"
API_ALL       = "https://live-api.keovip88.net/storage/livestream/all.json"
API_DETAIL    = "https://live-api.keovip88.net/api/fixtures/"

THUMBS_DIR    = "thumbs"
REPO_RAW      = os.environ.get("REPO_RAW", "")
THUMB_VERSION = "v4"

CATE_MAP = {
    "football":   "⚽ Bóng Đá",
    "basketball": "🏀 Bóng Rổ",
    "tennis":     "🎾 Tennis",
    "bongchuyen": "🏐 Bóng Chuyền",
    "esport":     "🎮 Esport",
    "caulong":    "🏸 Cầu Lông",
    "vothuat":    "🥊 Võ Thuật",
    "bongchay":   "⚾ Bóng Chày",
    "duaxe":      "🏎️ Đua Xe",
}

CATE_ORDER = ["football", "basketball", "tennis", "bongchuyen",
              "esport", "caulong", "vothuat", "bongchay", "duaxe"]

MOTORSPORT_KW = ["formula", "f1", "grand prix", "motogp", "nascar", "indycar", "đua xe"]

EXCLUDE_LEAGUES_AMERICA = [
    "mls", "major league soccer",
    "liga mx", "liga de expansion",
    "brasileirao", "brasileirão", "serie a brasil", "campeonato brasileiro", "brazilian",
    "copa do brasil",
    "argentine", "argentina", "liga profesional", "copa de la liga",
    "colombian", "colombia", "liga betplay",
    "chile", "ecuador", "peru", "venezuela", "paraguay", "uruguay", "bolivia",
    "inter miami", "new england", "la galaxy", "nycfc",
    "concacaf", "conmebol",
    "copa america", "copa sudamericana", "copa libertadores",
]


def is_america_league(league_name: str) -> bool:
    lower = league_name.lower()
    return any(kw in lower for kw in EXCLUDE_LEAGUES_AMERICA)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def make_id(text, prefix):
    h = hashlib.md5(text.encode()).hexdigest()[:10]
    return f"{prefix}-{h}"


def fetch_image(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        return Image.open(BytesIO(res.content)).convert("RGBA")
    except Exception:
        return None


def parse_time_sort(time_str: str, date_str: str) -> int:
    kickoff = parse_kickoff(time_str, date_str)
    if kickoff:
        return kickoff.month * 10_000_000 + kickoff.day * 10_000 + kickoff.hour * 100 + kickoff.minute
    return 999_999_999


def is_within_24h(time_str: str, date_str: str, cate_type: str = "football") -> bool:
    if cate_type != "football":
        return True
    kickoff = parse_kickoff(time_str, date_str)
    if kickoff is None:
        return True
    now   = now_vn()
    lower = now - timedelta(hours=6)
    upper = now + timedelta(hours=24)
    return lower <= kickoff <= upper


def format_time_hhmm(time_str: str) -> str:
    """Cắt thời gian về HH:MM (bỏ giây)."""
    if not time_str:
        return ""
    parts = time_str.strip().split(":")
    if len(parts) >= 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    return time_str.strip()


def format_date_ddmm(date_str: str) -> str:
    """Cắt ngày về DD/MM (bỏ năm)."""
    if not date_str:
        return ""
    d = date_str.strip()
    # DD/MM/YYYY -> DD/MM
    m3 = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
    if m3:
        return f"{m3.group(1).zfill(2)}/{m3.group(2).zfill(2)}"
    # DD/MM -> DD/MM
    m2 = re.match(r"(\d{1,2})/(\d{1,2})$", d)
    if m2:
        return f"{m2.group(1).zfill(2)}/{m2.group(2).zfill(2)}"
    return d


# ─────────────────────────────────────────────────────────────────────────────
# THUMBNAIL
# ─────────────────────────────────────────────────────────────────────────────

def make_thumbnail(match, channel_id):
    os.makedirs(THUMBS_DIR, exist_ok=True)
    cache_key = match.get("logo_a", "") + match.get("logo_b", "") + THUMB_VERSION
    logo_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]
    date_str  = now_vn().strftime("%Y%m%d")
    out_path  = f"{THUMBS_DIR}/{channel_id}_{logo_hash}_{date_str}.png"

    if os.path.exists(out_path):
        return out_path

    W, H = 1600, 1200
    HEADER_H = 180
    FOOTER_H = 160

    bg   = Image.new("RGB", (W, H), (245, 245, 248))
    draw = ImageDraw.Draw(bg)

    for y in range(HEADER_H, H - FOOTER_H):
        ratio = (y - HEADER_H) / (H - FOOTER_H - HEADER_H)
        gray  = int(248 - ratio * 18)
        draw.line([(0, y), (W, y)], fill=(gray, gray, gray + 4))

    draw.rectangle([(0, 0),            (W, HEADER_H)],  fill=(13, 20, 40))
    draw.rectangle([(0, H - FOOTER_H), (W, H)],         fill=(13, 20, 40))

    ACCENT = (220, 30, 40)
    draw.rectangle([(0, HEADER_H),         (W, HEADER_H + 5)],    fill=ACCENT)
    draw.rectangle([(0, H - FOOTER_H - 5), (W, H - FOOTER_H)],    fill=ACCENT)

    FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font_vs   = ImageFont.truetype(FONT_BOLD, 160)
        font_time = ImageFont.truetype(FONT_BOLD, 100)
        font_team = ImageFont.truetype(FONT_BOLD, 58)
        font_blv  = ImageFont.truetype(FONT_BOLD, 58)
    except Exception:
        font_vs = font_time = font_team = font_blv = ImageFont.load_default()

    content_top = HEADER_H + 5
    content_bot = H - FOOTER_H - 5
    content_h   = content_bot - content_top

    logo_size     = 360
    name_h        = 120
    time_h        = 110
    gap_logo_name = 40
    gap_name_time = 60

    total_block_h = logo_size + gap_logo_name + name_h + gap_name_time + time_h
    block_top     = content_top + (content_h - total_block_h) // 2

    logo_y       = block_top
    name_block_y = logo_y + logo_size + gap_logo_name
    name_center  = name_block_y + name_h // 2
    time_y       = name_block_y + name_h + gap_name_time + time_h // 2

    if match.get("logo_a"):
        img = fetch_image(match["logo_a"])
        if img:
            img = img.resize((logo_size, logo_size), Image.LANCZOS)
            x   = W // 4 - logo_size // 2
            bg.paste(img, (x, logo_y), img)

    if match.get("logo_b"):
        img = fetch_image(match["logo_b"])
        if img:
            img = img.resize((logo_size, logo_size), Image.LANCZOS)
            x   = W * 3 // 4 - logo_size // 2
            bg.paste(img, (x, logo_y), img)

    draw.text((W // 2, logo_y + logo_size // 2), "VS",
              fill=ACCENT, font=font_vs, anchor="mm")

    def draw_team_name(text, cx):
        max_width = W // 2 - 60
        font_size = 58
        f = font_team
        while font_size >= 28:
            try:
                f = ImageFont.truetype(FONT_BOLD, font_size)
            except Exception:
                f = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=f)
            if (bbox[2] - bbox[0]) <= max_width:
                break
            font_size -= 3
        draw.text((cx, name_center), text, fill=(20, 20, 20), font=f, anchor="mm")

    if match.get("team_a"):
        draw_team_name(match["team_a"], W // 4)
    if match.get("team_b"):
        draw_team_name(match["team_b"], W * 3 // 4)

    # Định dạng thời gian trên thumbnail: HH:MM DD/MM
    time_fmt = format_time_hhmm(match.get("time", ""))
    date_fmt = format_date_ddmm(match.get("date", ""))

    time_display = ""
    if time_fmt and date_fmt:
        time_display = f"{time_fmt} {date_fmt}"
    elif time_fmt:
        time_display = time_fmt

    if time_display:
        font_size = 100
        f_time = font_time
        while font_size >= 40:
            try:
                f_time = ImageFont.truetype(FONT_BOLD, font_size)
            except Exception:
                f_time = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), time_display, font=f_time)
            if (bbox[2] - bbox[0]) <= W - 100:
                break
            font_size -= 4

        draw.text((W // 2 + 4, time_y + 4), time_display,
                  fill=ACCENT, font=f_time, anchor="mm")
        draw.text((W // 2, time_y), time_display,
                  fill=(15, 15, 15), font=f_time, anchor="mm")

    if match.get("league"):
        league_text = match["league"].upper()
        font_size   = 62
        f           = None
        while font_size >= 28:
            try:
                f = ImageFont.truetype(FONT_BOLD, font_size)
            except Exception:
                f = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), league_text, font=f)
            if (bbox[2] - bbox[0]) <= W - 60:
                break
            font_size -= 3
        draw.text((W // 2, HEADER_H // 2), league_text,
                  fill=(255, 255, 255), font=f, anchor="mm")

    draw.rectangle([(0, 0), (W - 1, H - 1)], outline=(180, 180, 180), width=3)
    bg.save(out_path, "PNG", optimize=True)
    return out_path


def cleanup_old_thumbs(days: int = 3):
    if not os.path.exists(THUMBS_DIR):
        return
    cutoff  = now_vn() - timedelta(days=days)
    removed = 0
    for fname in os.listdir(THUMBS_DIR):
        if not fname.endswith(".png"):
            continue
        m = re.search(r'_(\d{8})\.png$', fname)
        if not m:
            fpath = os.path.join(THUMBS_DIR, fname)
            try:
                os.remove(fpath)
                removed += 1
            except Exception:
                pass
            continue
        try:
            file_date = datetime.strptime(m.group(1), "%Y%m%d").replace(tzinfo=VN_TZ)
        except ValueError:
            continue
        if file_date < cutoff:
            fpath = os.path.join(THUMBS_DIR, fname)
            try:
                os.remove(fpath)
                removed += 1
            except Exception:
                pass
    if removed:
        print(f"Da xoa {removed} thumbnail cu (>{days} ngay)")


# ─────────────────────────────────────────────────────────────────────────────
# FETCH API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_json(url: str) -> list:
    try:
        t   = int(time.time() * 1000)
        res = requests.get(f"{url}?t={t}", headers=HEADERS, timeout=15)
        data = res.json()
        return data.get("response", []) if isinstance(data, dict) else []
    except Exception as e:
        print(f"  Loi fetch {url}: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# PARSE MATCHES
# ─────────────────────────────────────────────────────────────────────────────

def get_blv_names(blv_list: list) -> str:
    BLV_NAME_MAP = {
        "blv-perry":         "BLV Perry",
        "blv-1":             "BLV Ngỗng",
        "blv-3":             "BLV Dần",
        "blv-5":             "BLV Thìn",
        "blv-6":             "BLV Tỵ",
        "blv-12":            "BLV Hợi",
        "blv-tom":           "BLV Tôm",
        "blv-ben":           "BLV Ben",
        "blv-cay":           "BLV Cầy",
        "blv-bang":          "BLV Băng",
        "blv-mason":         "BLV Mason",
        "blv-cam":           "BLV Câm",
        "blv-dory":          "BLV Dory",
        "blv-chanh":         "BLV Chanh",
        "blv-nen":           "BLV Nến",
        "blv-diec":          "BLV Điếc",
        "blv-thuviec":       "BLV Thử Việc",
        "fan-liver":         "Fan Liver: Thìn + Tỵ",
        "fan-mu-perry-cam":  "Fan MU: Perry vs Câm",
        "fan-psg":           "Fan PSG: Câm + Bin",
        "fan-bayern":        "Fan Chè: Điếc",
        "nha-dai":           "Nhà Đài",
    }
    names = []
    for key in blv_list:
        if key == "nha-dai":
            continue
        names.append(BLV_NAME_MAP.get(key, key))
    return ", ".join(names)


def resolve_cate_type(raw_type: str, league_name: str, team_a: str, team_b: str) -> str:
    """Override cate_type dựa trên keyword đua xe, dù API trả về type gì."""
    league_lower = league_name.lower()
    name_lower   = (team_a + " " + team_b).lower()
    if any(kw in league_lower or kw in name_lower for kw in MOTORSPORT_KW):
        return "duaxe"
    return raw_type


def get_matches() -> list:
    live_items = fetch_json(API_LIVE)
    all_items  = fetch_json(API_ALL)

    seen = {}
    for item in live_items:
        seen[item.get("id")] = item
    for item in all_items:
        if item.get("id") not in seen:
            seen[item.get("id")] = item

    matches = []
    for item in seen.values():
        match_id    = item.get("id", "")
        raw_type    = item.get("type", "football")
        status_code = item.get("status_code", "NS")
        blv_list    = item.get("blv") or []
        time_str    = item.get("time", "")
        date_str    = item.get("day_month", "")
        league_obj  = item.get("league") or {}
        league_name = league_obj.get("title", "")
        league_icon = league_obj.get("icon", "")
        teams       = item.get("teams") or {}
        home        = teams.get("home") or {}
        away        = teams.get("away") or {}
        team_a      = home.get("name", "")
        team_b      = away.get("name", "")
        logo_a      = home.get("logo", "")
        logo_b      = away.get("logo", "")

        if not match_id:
            continue

        if status_code == "FT":
            continue

        if "nha-dai" in blv_list:
            continue

        real_blv = [b for b in blv_list if b != "nha-dai"]
        if not real_blv:
            continue

        # Override cate_type nếu là đua xe
        cate_type = resolve_cate_type(raw_type, league_name, team_a, team_b)

        if cate_type == "football" and is_america_league(league_name):
            continue

        if not is_within_24h(time_str, date_str, cate_type):
            continue

        is_live = calc_is_live(status_code, time_str, date_str)
        blv_names = get_blv_names(blv_list)

        name = f"{team_a} vs {team_b}" if team_a and team_b else match_id[:50]

        matches.append({
            "match_id":   match_id,
            "cate_type":  cate_type,
            "name":       name,
            "time":       time_str,
            "date":       date_str,
            "time_sort":  parse_time_sort(time_str, date_str),
            "team_a":     team_a,
            "team_b":     team_b,
            "logo_a":     logo_a,
            "logo_b":     logo_b,
            "league":     league_name,
            "league_icon": league_icon,
            "blv":        blv_names,
            "blv_list":   blv_list,
            "is_live":    is_live,
            "status_code": status_code,
            "is_hot":     item.get("is_hot", 0),
            "is_hot_top": item.get("is_hot_top", 0),
        })

    matches.sort(key=lambda m: (0 if m["is_live"] else 1, m["time_sort"]))
    return matches


# ─────────────────────────────────────────────────────────────────────────────
# GET LIVE URL (API CHI TIẾT)
# ─────────────────────────────────────────────────────────────────────────────

def get_live_url(match_id: str) -> str | None:
    """Gọi API chi tiết để lấy link_stream_hd thực tế."""
    if not match_id:
        return None
    try:
        url = f"{API_DETAIL}{match_id}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()

        fixture_data = data
        if isinstance(data, dict) and "response" in data:
            fixture_data = data["response"]
            if isinstance(fixture_data, list) and len(fixture_data) > 0:
                fixture_data = fixture_data[0]

        blv_list = fixture_data.get("blv", []) if isinstance(fixture_data, dict) else []

        if isinstance(blv_list, list):
            for blv in blv_list:
                if isinstance(blv, dict):
                    hd_link = blv.get("link_stream_hd")
                    if hd_link:
                        return hd_link
        return None
    except Exception as e:
        print(f"    Loi lay link chi tiet: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# BUILD CHANNEL JSON
# ─────────────────────────────────────────────────────────────────────────────

def build_channel(match: dict, stream_url: str, thumb_url: str = "") -> dict:
    uid    = make_id(match["match_id"], "gv")
    src_id = make_id(match["match_id"], "src")
    ct_id  = make_id(match["match_id"], "ct")
    st_id  = make_id(match["match_id"], "st")

    stream_links = []
    if stream_url:
        lnk_id = make_id(stream_url, "lnk")
        stream_links.append({
            "id":      lnk_id,
            "name":    "Link HD 720p",
            "type":    "hls",
            "default": True,
            "url":     stream_url,
            "request_headers": [
                {"key": "Referer",    "value": "https://giovang.fun/"},
                {"key": "User-Agent", "value": "Mozilla/5.0"},
            ],
        })

    label_text  = "● LIVE" if match["is_live"] else "🕐 Sắp"
    label_color = "#ff4444" if match["is_live"] else "#aaaaaa"

    time_fmt = format_time_hhmm(match["time"])
    date_fmt = format_date_ddmm(match["date"])

    display_name = match["name"]
    if time_fmt and date_fmt:
        display_name = f"{match['name']} | {time_fmt} {date_fmt}"
    elif time_fmt:
        display_name = f"{match['name']} | {time_fmt}"

    channel = {
        "id":            uid,
        "name":          display_name,
        "type":          "single",
        "display":       "thumbnail-only",
        "enable_detail": False,
        "labels": [{"text": label_text, "position": "top-left",
                    "color": "#00000080", "text_color": label_color}],
        "sources": [{
            "id":   src_id,
            "name": "GiovangTV",
            "contents": [{
                "id":   ct_id,
                "name": match["name"],
                "streams": [{"id": st_id, "name": "GV", "stream_links": stream_links}],
            }],
        }],
        "org_metadata": {
            "league":    match.get("league",      ""),
            "team_a":    match.get("team_a",      ""),
            "team_b":    match.get("team_b",      ""),
            "logo_a":    match.get("logo_a",      ""),
            "logo_b":    match.get("logo_b",      ""),
            "time":      match.get("time",        ""),
            "date":      match.get("date",        ""),
            "blv":       match.get("blv",         ""),
            "is_live":   match["is_live"],
            "cate_type": match.get("cate_type",   ""),
        },
    }

    if thumb_url:
        channel["image"] = {
            "padding":          1,
            "background_color": "#ffffff",
            "display":          "contain",
            "url":              thumb_url,
            "width":            1600,
            "height":           1200,
        }

    return channel


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(THUMBS_DIR, exist_ok=True)
    cleanup_old_thumbs(days=3)
    print(f"Gio VN hien tai : {now_vn().strftime('%H:%M %d/%m/%Y')}")
    print("Lay danh sach tran tu GiovangTV API...")

    matches = get_matches()

    live_count = sum(1 for m in matches if m["is_live"])
    print(f"Tong: {len(matches)} | LIVE: {live_count} | Sap: {len(matches) - live_count}\n")

    cate_channels = {cate: [] for cate in CATE_ORDER}

    for i, match in enumerate(matches):
        cate_type = match["cate_type"]
        status    = "LIVE" if match["is_live"] else "SAP"
        log_time  = format_time_hhmm(match['time'])
        log_date  = format_date_ddmm(match['date'])
        print(f"[{status} {i+1}/{len(matches)}] {match['name']} ({log_time} {log_date}) | BLV: {match['blv']}")

        stream_url = None

        raw_url = get_live_url(match["match_id"])

        if raw_url:
            stream_url = raw_url
            if match["is_live"]:
                print(f"    stream: DA LUU (LIVE)")
            else:
                print(f"    stream: DA LUU (SAP)")
        else:
            if match["is_live"]:
                print(f"    stream: LOI API CHI TIET (de trong)")
            else:
                print(f"    stream: Chua co link (de trong)")

        uid       = make_id(match["match_id"], "gv")
        cache_key = match.get("logo_a", "") + match.get("logo_b", "") + THUMB_VERSION
        logo_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]

        thumb_path = make_thumbnail(match, uid)
        thumb_url  = f"{REPO_RAW}/{thumb_path}?v={logo_hash}" if REPO_RAW else ""

        channel = build_channel(match, stream_url, thumb_url)

        if cate_type not in cate_channels:
            cate_channels[cate_type] = []
        cate_channels[cate_type].append(channel)

        time.sleep(0.2)

    groups = []
    for cate_type in CATE_ORDER:
        channels = cate_channels.get(cate_type, [])
        if not channels:
            continue

        cate_label = CATE_MAP.get(cate_type, "🏅 Thể Thao")
        live_cnt   = sum(1 for ch in channels
                         if ch.get("org_metadata", {}).get("is_live", False))
        cate_name  = f"{cate_label} ({live_cnt} LIVE)" if live_cnt > 0 else cate_label

        groups.append({
            "id":            f"cate_{cate_type}",
            "name":          cate_name,
            "display":       "vertical",
            "grid_number":   2,
            "enable_detail": False,
            "channels":      channels,
        })

    for cate_type, channels in cate_channels.items():
        if cate_type not in CATE_ORDER and channels:
            live_cnt  = sum(1 for ch in channels
                            if ch.get("org_metadata", {}).get("is_live", False))
            cate_name = f"🏅 Thể Thao ({live_cnt} LIVE)" if live_cnt > 0 else "🏅 Thể Thao"
            groups.append({
                "id":            f"cate_{cate_type}",
                "name":          cate_name,
                "display":       "vertical",
                "grid_number":   2,
                "enable_detail": False,
                "channels":      channels,
            })

    output = {
        "id":          "giovang",
        "url":         "https://giovang.fun",
        "name":        "GiovangTV",
        "color":       "#0155a5",
        "grid_number": 3,
        "image":       {"type": "cover", "url": "https://giovang.fun/wp-content/uploads/2024/10/GiovangTV_logo-01-1.png"},
        "groups":      groups,
    }

    staging = "output_staging.json"
    with open(staging, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = sum(len(g["channels"]) for g in groups)

    def normalize(path):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            return json.dumps(d, sort_keys=True, ensure_ascii=False)
        except Exception:
            return ""

    old_norm = normalize("output.json")
    new_norm = normalize(staging)

    if old_norm != new_norm:
        os.replace(staging, "output.json")
        print(f"\nXong! {total} kenh, {len(groups)} mon the thao -> output.json (DA CAP NHAT)")
    else:
        os.remove(staging)
        print(f"\nXong! {total} kenh, {len(groups)} mon the thao -> Khong co thay doi, giu nguyen output.json")


if __name__ == "__main__":
    main()
