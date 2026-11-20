import os
import shutil

# Ensure FFmpeg is available even if the terminal has a stale PATH
for p in [
    r"C:\Users\priya\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin",
    r"C:\Program Files\ffmpeg\bin",
    r"C:\ffmpeg\bin",
]:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
        break

import yt_dlp
from pydub import AudioSegment

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR,exist_ok = True)

def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    
    ffmpeg_dir = r"C:\Users\priya\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "mweb", "tv", "android", "web"]
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
    }
    
    if os.path.exists(ffmpeg_dir):
        ydl_opts["ffmpeg_location"] = ffmpeg_dir
    if shutil.which("node"):
        ydl_opts["js_runtimes"] = {"node": {}}
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_name = os.path.splitext(ydl.prepare_filename(info))[0]
            filename = base_name + ".wav"
            if not os.path.exists(filename):
                alt_filename = ydl.prepare_filename(info)
                if os.path.exists(alt_filename):
                    filename = alt_filename
        return filename
    except Exception as e:
        err_str = str(e)
        if "403" in err_str or "Forbidden" in err_str or "Sign in to confirm" in err_str:
            raise RuntimeError(
                "YouTube has restricted direct streaming from this cloud server's IP address (HTTP 403: Forbidden). "
                "Cloud platforms (AWS / Streamlit Cloud) are frequently blocked by YouTube's bot protection.\n\n"
                "👉 Solution: Please select 'Upload File' in the sidebar and upload your video/audio file directly to process it!"
            ) from e
        raise e



def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000) #16khz
    audio.export(output_path, format="wav")
    return output_path



def chunk_audio(wav_path : str , chunk_minutes : int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000 

    chunks = []

    for i, start in enumerate(range(0,len(audio),chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path , format = "wav")

        chunks.append(chunk_path)
    
    return chunks

def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks


def extract_youtube_id(url: str):
    import re
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:shorts\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_youtube_transcript(url: str):
    """
    Attempts to fetch existing captions/subtitles directly from YouTube.
    Bypasses raw video/audio media download and avoids 403 Forbidden on cloud datacenters.
    Returns full transcript string if found, otherwise None.
    """
    video_id = extract_youtube_id(url)
    if not video_id:
        return None

    def _get_text(item):
        if hasattr(item, "text"):
            return item.text
        if isinstance(item, dict):
            return item.get("text", "")
        return str(item)

    # Strategy 1: youtube-transcript-api (supports both modern object and legacy dict formats)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        # Check for legacy get_transcript method
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            try:
                for lang_code in [["en"], ["en-US"], ["en-GB"], ["hi"]]:
                    entries = YouTubeTranscriptApi.get_transcript(video_id, languages=lang_code)
                    if entries:
                        return " ".join(_get_text(item) for item in entries)
            except Exception:
                pass

        # Modern instance-based list() method
        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list(video_id)

        # Priority 1: English (manual or auto)
        for t in transcript_list:
            if t.language_code.startswith("en"):
                lines = t.fetch()
                return " ".join(_get_text(item) for item in lines)

        # Priority 2: Any available language (Hindi, etc.)
        for t in transcript_list:
            lines = t.fetch()
            return " ".join(_get_text(item) for item in lines)
    except Exception as e:
        print(f"youtube-transcript-api lookup failed for {video_id}: {e}")

    # Strategy 2: yt-dlp subtitle metadata extraction (no video/audio download needed)
    try:
        ydl_opts_sub = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en.*", "hi.*"],
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "mweb", "tv", "android", "web"]
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts_sub) as ydl:
            info = ydl.extract_info(url, download=False)
            subs = info.get("subtitles") or info.get("automatic_captions") or {}

            chosen_track = None
            for lang, tracks in subs.items():
                if lang.startswith("en"):
                    chosen_track = tracks
                    break
            if not chosen_track and subs:
                chosen_track = next(iter(subs.values()))

            if chosen_track:
                sub_url = None
                for track in chosen_track:
                    ext = track.get("ext", "")
                    if ext == "json3":
                        sub_url = track.get("url")
                        break
                    elif ext == "vtt" and not sub_url:
                        sub_url = track.get("url")

                if sub_url:
                    import requests
                    resp = requests.get(sub_url, timeout=15)
                    if resp.ok:
                        if "json" in resp.headers.get("Content-Type", "") or sub_url.endswith("json3"):
                            data = resp.json()
                            events = data.get("events", [])
                            lines = []
                            for ev in events:
                                segs = ev.get("segs", [])
                                line = "".join(s.get("utf8", "") for s in segs).strip()
                                if line and line != "\n":
                                    lines.append(line)
                            if lines:
                                return " ".join(lines)
                        else:
                            import re
                            clean_text = re.sub(r"<[^>]+>", "", resp.text)
                            clean_text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}", "", clean_text)
                            clean_text = re.sub(r"WEBVTT|NOTE.*", "", clean_text)
                            words = " ".join(clean_text.split())
                            if words:
                                return words
    except Exception as e:
        print(f"yt-dlp subtitle extraction failed for {url}: {e}")

    return None


