import os

for p in [
    r"C:\Users\priya\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin",
    r"C:\Program Files\ffmpeg\bin",
    r"C:\ffmpeg\bin",
]:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
        break

import whisper
import requests
from pydub import AudioSegment

# Sarvam's sync STT-translate API rejects audio longer than 30s.
# We slice each chunk into 25s pieces (with a 5s safety margin) before sending.
SARVAM_PIECE_SECONDS = 25


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")


SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_TRANSLATE_URL = "https://api.sarvam.ai/speech-to-text-translate"
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")

_model = None
_loaded_model_name = None


def load_model():
    global _model, _loaded_model_name
    model_name = os.getenv("WHISPER_MODEL", "tiny")

    if _model is None or _loaded_model_name != model_name: 
        print(f"Loading Whisper model: {model_name} ...")
        _model = whisper.load_model(model_name)
        _loaded_model_name = model_name
        print("Whisper model loaded.")
    return _model 


def transcribe_chunk_whisper(chunk_path: str) -> str:
    model = load_model()  
    print(f"Transcribing with Whisper ({_loaded_model_name}, fast greedy decoding)...")
    result = model.transcribe(
        chunk_path,
        task="transcribe",
        fp16=False,
        beam_size=1,
        best_of=1,
        temperature=0.0,
    )  
    return result["text"]  


def _send_to_sarvam(piece_path: str) -> str:
    """Send one ≤30s WAV file to Sarvam and return the English transcript."""
    api_key = os.getenv("SARVAM_API_KEY") or SARVAM_API_KEY
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not set. Please provide your Sarvam API key.")
    headers = {"api-subscription-key": api_key}

    with open(piece_path, "rb") as f:
        files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
        data = {"model": os.getenv("SARVAM_STT_MODEL", SARVAM_MODEL), "with_diarization": "false"}
        response = requests.post(
            SARVAM_STT_TRANSLATE_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if not response.ok:
        print(f"\n❌ Sarvam returned {response.status_code}")
        print(f"Response body: {response.text}\n")
        response.raise_for_status()

    return response.json().get("transcript", "")


def transcribe_chunk_sarvam(chunk_path: str) -> str:
    """
    Sarvam sync API only accepts ≤30s audio. We split this chunk into
    25-second pieces, send each concurrently in parallel, and join the transcripts.
    """
    from concurrent.futures import ThreadPoolExecutor

    api_key = os.getenv("SARVAM_API_KEY") or SARVAM_API_KEY
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = SARVAM_PIECE_SECONDS * 1000

    pieces = []
    total_pieces = (len(audio) + piece_ms - 1) // piece_ms

    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece = audio[start: start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")
        pieces.append((i, piece_path))

    transcripts = {}

    def _upload_piece(item):
        idx, path = item
        try:
            print(f"  → Sarvam piece {idx + 1}/{total_pieces} transcribing...")
            return idx, _send_to_sarvam(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(_upload_piece, pieces)
        for idx, text in results:
            transcripts[idx] = text

    full_text = " ".join(transcripts[i] for i in range(total_pieces))
    return full_text.strip()

   



def transcribe_chunk(chunk_path: str, language: str = "english") -> str:
    """
    Route one chunk to Whisper or Sarvam depending on language choice.
    - english  → Whisper (local model)
    - hinglish → Sarvam (translates to English while transcribing)
    """
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(chunk_path)
    return transcribe_chunk_whisper(chunk_path)


def transcribe_all(chunks: list, language: str = "english") -> str:

    full_transcript = "" 

    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    print(f"Using {engine} for transcription.")

    for i, chunk in enumerate(chunks):  

        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        text = transcribe_chunk(chunk, language=language)  

        full_transcript += text + " "  

    print("Transcription complete.")

    return full_transcript.strip()  
