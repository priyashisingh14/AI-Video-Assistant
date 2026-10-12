import os
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI

load_dotenv()

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None


def get_llm(temperature: float = 0.3):
    """
    Returns an LLM instance:
    1. If MISTRAL_API_KEY is present, uses Mistral.
    2. If SARVAM_API_KEY is present, uses Sarvam's sarvam-105b LLM.
    3. Otherwise raises a clear error.
    """
    mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()
    sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()

    if mistral_key:
        return ChatMistralAI(
            model="mistral-small-latest",
            mistral_api_key=mistral_key,
            temperature=temperature,
        )
    elif sarvam_key and ChatOpenAI is not None:
        sarvam_model = os.getenv("SARVAM_LLM_MODEL", "sarvam-105b-conversations")
        return ChatOpenAI(
            base_url="https://api.sarvam.ai/v1",
            api_key=sarvam_key,
            model=sarvam_model,
            temperature=temperature,
        )
    else:
        raise ValueError(
            "No API key found! Please provide a SARVAM_API_KEY or MISTRAL_API_KEY in .env or the UI sidebar."
        )
