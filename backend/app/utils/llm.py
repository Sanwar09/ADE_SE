import os
import time
import hashlib
import threading
import json
from typing import Optional, Generator
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────
# Multi-Key Rotation
# ──────────────────────────────────────────────────────────────────────

def _load_api_keys():
    """Load all available Gemini API keys from environment variables."""
    keys = []
    primary = os.getenv("GEMINI_API_KEY", "")
    if primary and primary != "your_gemini_api_key_here":
        keys.append(primary)
    # Support up to 5 additional rotated keys
    for i in range(2, 7):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "")
        if k and k != "your_gemini_api_key_here":
            keys.append(k)
    return keys

API_KEYS = _load_api_keys()
_key_index = 0
_key_lock = threading.Lock()


def _get_next_key() -> str:
    """Round-robin key rotation across available API keys."""
    global _key_index
    if not API_KEYS:
        raise ValueError(
            "No GEMINI_API_KEY configured. "
            "Set GEMINI_API_KEY in backend/.env"
        )
    with _key_lock:
        key = API_KEYS[_key_index % len(API_KEYS)]
        _key_index += 1
    return key


def _build_client(api_key: str):
    """Build a google-genai Client for a specific API key."""
    return genai.Client(api_key=api_key)


# ──────────────────────────────────────────────────────────────────────
# Request Pacing  (prevents 429 on free-tier: ≤15 RPM)
# ──────────────────────────────────────────────────────────────────────

_last_call_time = 0.0
_pace_lock = threading.Lock()
MIN_CALL_INTERVAL = float(os.getenv("LLM_MIN_INTERVAL_SEC", "4"))


def _pace():
    """Enforce minimum delay between consecutive API calls."""
    global _last_call_time
    with _pace_lock:
        now = time.time()
        elapsed = now - _last_call_time
        if elapsed < MIN_CALL_INTERVAL:
            wait = MIN_CALL_INTERVAL - elapsed
            time.sleep(wait)
        _last_call_time = time.time()


# ──────────────────────────────────────────────────────────────────────
# Prompt-Level Cache (hash-based deduplication)
# ──────────────────────────────────────────────────────────────────────

_cache: dict = {}
_cache_lock = threading.Lock()
CACHE_ENABLED = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
MAX_CACHE_SIZE = 100


def _cache_key(prompt: str, system_instruction: str, temperature: float) -> str:
    raw = f"{prompt}||{system_instruction}||{temperature}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _get_cached(key: str) -> Optional[str]:
    if not CACHE_ENABLED:
        return None
    with _cache_lock:
        entry = _cache.get(key)
        if entry:
            return entry["response"]
    return None


def _set_cached(key: str, response: str):
    if not CACHE_ENABLED:
        return
    with _cache_lock:
        if len(_cache) >= MAX_CACHE_SIZE:
            oldest = next(iter(_cache))
            del _cache[oldest]
        _cache[key] = {"response": response, "ts": time.time()}


# ──────────────────────────────────────────────────────────────────────
# Core LLM Call
# ──────────────────────────────────────────────────────────────────────

def get_model_name() -> str:
    """Return the configured model name."""
    return os.getenv("MODEL_NAME", "gemini-2.0-flash")


def call_llm(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.2,
    max_tokens: int = 8192,
    retries: int = 3,
    use_cache: bool = True,
) -> str:
    """
    Call Gemini API with a prompt and return the text response.
    Single entry point for ALL LLM calls.

    Features:
    - Multi-key rotation across all GEMINI_API_KEY_* env vars
    - Token-bucket pacing (min 4s between calls on free tier)
    - Prompt-level hash caching (skip API if same prompt seen before)
    - Exponential backoff with jitter for rate limit errors
    """
    # 1. Check cache
    ck = _cache_key(prompt, system_instruction, temperature)
    if use_cache:
        cached = _get_cached(ck)
        if cached:
            return cached

    model_name = get_model_name()

    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    if system_instruction:
        config.system_instruction = system_instruction

    last_error = None
    for attempt in range(retries):
        # 2. Pace requests
        _pace()

        # 3. Rotate key
        api_key = _get_next_key()
        client = _build_client(api_key)

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            # 4. Cache result
            if text:
                _set_cached(ck, text)
            return text

        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            if "429" in error_str or "resource_exhausted" in error_str:
                import random
                base_wait = (attempt + 1) * 12
                jitter = random.uniform(0, 5)
                wait_time = base_wait + jitter
                print(
                    f"[LLM] Rate limited (key #{_key_index % max(len(API_KEYS),1)}). "
                    f"Waiting {wait_time:.1f}s before retry {attempt + 1}/{retries}..."
                )
                time.sleep(wait_time)
            elif "404" in error_str or "not found" in error_str:
                # Model not found — try a fallback
                if model_name != "gemini-2.0-flash":
                    print(f"[LLM] Model '{model_name}' not found. Trying gemini-2.0-flash...")
                    os.environ["MODEL_NAME"] = "gemini-2.0-flash"
                    model_name = "gemini-2.0-flash"
                else:
                    raise
            else:
                raise

    raise last_error


def call_llm_safe(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.2,
    max_tokens: int = 8192,
) -> str:
    """
    Safe wrapper — never crashes. Falls back to a placeholder if API fails.
    Use this for all agent calls.
    """
    try:
        return call_llm(prompt, system_instruction, temperature, max_tokens)
    except ValueError:
        return "[DEMO MODE — No API Key] Configure GEMINI_API_KEY in backend/.env"
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return (
                "[RATE LIMITED] Gemini API quota exceeded after retries. "
                "Please wait a minute and try again, or add more API keys "
                "(GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.) in .env"
            )
        return f"[LLM ERROR] {error_msg[:300]}"


# ──────────────────────────────────────────────────────────────────────
# Event Callback (for SSE streaming to frontend)
# ──────────────────────────────────────────────────────────────────────

def create_event_callback():
    """
    Create a thread-safe event queue for SSE streaming.
    Returns (push_event, get_events) pair.
    """
    import queue
    q = queue.Queue()

    def push(event_type: str, data: dict):
        q.put({"event": event_type, "data": data, "ts": time.time()})

    def get_all():
        events = []
        while not q.empty():
            try:
                events.append(q.get_nowait())
            except queue.Empty:
                break
        return events

    return push, q
