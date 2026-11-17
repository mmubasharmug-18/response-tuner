import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LLM_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def get_api_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key or key == "your_key_here":
        raise RuntimeError("GROQ_API_KEY is not set in the .env file")
    return key


def has_api_key():
    try:
        get_api_key()
        return True
    except RuntimeError:
        return False
