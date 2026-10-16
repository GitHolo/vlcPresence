import os
import re
import time
import urllib.parse
import requests
from pypresence import Presence
from pypresence.types import ActivityType

# --- CONFIG ---
CLIENT_ID = "1554906001743024210"
VLC_PASSWORD = "YOUR_PASSWORD_HERE"  # Set this in VLC's web interface (Tools > Preferences > Show Settings: All > Interface > Main interfaces > Lua > Lua HTTP > Password)
VLC_URL = "http://127.0.0.1:8080/requests/status.json"
DEFAULT_VLC_ICON = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/VLC_media_player.svg/512px-VLC_media_player.svg.png"

AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus", ".wma"}
media_cache = {}

def format_time(seconds):
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def clean_movie_filename(raw_text):

    base, ext = os.path.splitext(raw_text)
    if ext.lower() in {".mkv", ".mp4", ".avi", ".mov", ".webm", ".flv", ".wmv"} | AUDIO_EXTENSIONS:
        raw_text = base
    text = re.sub(r"[\[\(\{].*?[\]\)\}]", " ", raw_text)
    text = re.sub(r"[._\-]+", " ", text)

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    year = year_match.group(1) if year_match else None

    split_pattern = (
        r"\b(19\d{2}|20\d{2}|S\d{1,2}E\d{1,2}|1080p|720p|2160p|4k|uhd|bluray|brrip|bdrip|"
        r"web-dl|webrip|web|hdrip|dvdrip|x264|x265|h264|h265|hevc|aac|ac3|proper|repack|"
        r"extended|remastered|unrated|directors cut)\b"
    )
    clean_title = re.split(split_pattern, text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return (clean_title or text.strip()), year

def get_media_metadata(raw_title, filename, artist=None):
    cache_key = f"{filename}_{raw_title}_{artist}"
    if cache_key in media_cache:
        return media_cache[cache_key]

    _, ext = os.path.splitext(filename)
    is_audio = ext.lower() in AUDIO_EXTENSIONS
    clean_title, year = clean_movie_filename(raw_title if not is_audio else filename)

    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. Try IMDb
    if not is_audio:
        search_query = f"{clean_title} {year}" if year else clean_title
        encoded_query = urllib.parse.quote(search_query.lower())
        imdb_url = f"https://v3.sg.media-imdb.com/suggestion/x/{encoded_query}.json"

        try:
            res = requests.get(imdb_url, headers=headers, timeout=3)
            if res.status_code == 200:
                results = res.json().get("d", [])
                for item in results:
                    if "i" in item and "imageUrl" in item["i"]:
                        official_title = item.get("l", clean_title)
                        rel_year = item.get("y") or year
                        formatted_title = f"{official_title} ({rel_year})" if rel_year else official_title
                        
                        # Resize IMDb poster to 500px wide so Discord loads it quickly
                        poster = re.sub(r"\._V1_.*\.jpg$", "._V1_SX500.jpg", item["i"]["imageUrl"])
                        cast_info = item.get("s", "")

                        result_data = {
                            "title": formatted_title,
                            "subtitle": cast_info,
                            "image": poster,
                            "is_audio": False,
                        }
                        media_cache[cache_key] = result_data
                        print(f"[IMDb Match] {formatted_title}")
                        return result_data
        except Exception as e:
            print(f"[IMDb Warning] {e}")

    # 2. Fallback to iTunes
    itunes_term = f"{artist} {raw_title}" if (is_audio and artist) else clean_title
    media_type = "music" if is_audio else "movie"
    try:
        res = requests.get(
            "https://itunes.apple.com/search",
            params={"term": itunes_term, "media": media_type, "limit": 1},
            timeout=3,
        )
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results and "artworkUrl100" in results[0]:
                art_url = results[0]["artworkUrl100"].replace("100x100bb", "512x512bb")
                result_data = {
                    "title": raw_title if is_audio else (f"{clean_title} ({year})" if year else clean_title),
                    "subtitle": f"by {artist}" if artist else "",
                    "image": art_url,
                    "is_audio": is_audio,
                }
                media_cache[cache_key] = result_data
                print(f"[iTunes Match] {result_data['title']}")
                return result_data
    except Exception as e:
        print(f"[iTunes Warning] {e}")

    # 3. Default Fallback if offline or unmatched
    fallback_data = {
        "title": f"{clean_title} ({year})" if (year and not is_audio) else clean_title,
        "subtitle": f"by {artist}" if artist else "",
        "image": DEFAULT_VLC_ICON,
        "is_audio": is_audio,
    }
    media_cache[cache_key] = fallback_data
    return fallback_data

# --- MAIN LOOP ---
rpc = Presence(CLIENT_ID)
rpc.connect()
print("Connected to Discord RPC. Checking VLC on 127.0.0.1:8080...")

while True:
    try:
        res = requests.get(VLC_URL, auth=("", VLC_PASSWORD), timeout=2)

        if res.status_code == 200:
            data = res.json()
            state = data.get("state")

            if state in ("playing", "paused"):
                meta = data.get("information", {}).get("category", {}).get("meta", {})

                raw_filename = meta.get("filename", "Unknown Media")
                raw_title = meta.get("title") or raw_filename
                artist = meta.get("artist")

                info = get_media_metadata(raw_title, raw_filename, artist)
                details = info["title"][:128]

                elapsed = int(data.get("time", 0))
                duration = int(data.get("length", 0))
                time_str = f"{format_time(elapsed)} / {format_time(duration)}" if duration > 0 else format_time(elapsed)

                if state == "playing":
                    start_time = int(time.time()) - elapsed
                    end_time = (start_time + duration) if duration > 0 else None
                    state_text = f"{info['subtitle']} • {time_str}" if info["subtitle"] else time_str
                else:
                    start_time = None
                    end_time = None
                    state_text = f"Paused • {time_str}"

                activity_mode = ActivityType.LISTENING if info["is_audio"] else ActivityType.WATCHING
                has_custom_art = info["image"] != DEFAULT_VLC_ICON

                rpc.update(
                    activity_type=activity_mode,
                    details=details,
                    state=state_text[:128],
                    start=start_time,
                    end=end_time,
                    large_image=info["image"],
                    large_text=details,
                    small_image=DEFAULT_VLC_ICON if has_custom_art else None,
                    small_text="VLC Media Player" if has_custom_art else None,
                )
                print(f"[SUCCESS] {details} | {state_text} ({state})")
            else:
                print("[VLC Connected] Idle/Stopped.")
                rpc.clear()
        elif res.status_code == 401:
            print("[ERROR 401] Wrong password! Check VLC_PASSWORD.")
            rpc.clear()
        else:
            print(f"[ERROR] VLC returned HTTP {res.status_code}")
            rpc.clear()

    except requests.exceptions.ConnectionError:
        print("[WAITING] Cannot reach VLC on 127.0.0.1:8080.")
        rpc.clear()
    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(5)