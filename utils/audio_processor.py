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
                "player_client": ["android", "web"]
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
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list(video_id)

        # Priority 1: English (manual or auto)
        for t in transcript_list:
            if t.language_code.startswith("en"):
                lines = t.fetch()
                return " ".join(item.text for item in lines)

        # Priority 2: Any available language (Hindi, etc.)
        for t in transcript_list:
            lines = t.fetch()
            return " ".join(item.text for item in lines)
    except Exception as e:
        print(f"Direct transcript lookup not available for {video_id}: {e}")
        return None


