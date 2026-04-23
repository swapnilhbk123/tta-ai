# ai_enhancer.py  —  Free AI elaboration engine for TTA Itinerary Builder
# Supports: Groq (Llama 3.3) [PRIMARY]  |  Google Gemini Flash [FALLBACK]

import os
import re
import json
import urllib.request
import urllib.error

# ── Shared prompt builder ─────────────────────────────────────────────────────
def _build_prompt(location: str, activity: str, bullet_points: list[str]) -> str:
    bullets_joined = "\n".join(f"- {b}" for b in bullet_points)
    return f"""You are a professional travel writer for a premium travel DMC company.

Your task is to take the following raw bullet points for a travel itinerary day and ELABORATE each one into a rich, vivid, and accurate travel description.

STRICT RULES:
1. Keep EVERY original bullet point — do NOT remove, skip, or merge any of them.
2. Only EXPAND each bullet with 1-2 sentences of vivid, accurate, travel-writing style detail.
3. Do NOT invent new activities, sights, or stops that were not in the original input.
4. Do NOT add any headings, titles, or preamble — just return the elaborated bullet list.
5. Return ONLY a JSON array of strings, one string per bullet. No other text.
6. Maintain factual accuracy. Only describe what is genuinely known about each place.

Location: {location}
Day Theme: {activity}

Original bullets:
{bullets_joined}

Return format (strict JSON array, nothing else):
["elaborated bullet 1", "elaborated bullet 2", ...]"""

# ── Response parser ───────────────────────────────────────────────────────────
def _parse_response(raw_text: str, original_bullets: list[str]) -> list[str]:
    """Safely parse the JSON array from the AI response."""
    raw_text = raw_text.strip()

    # Try to extract JSON array from the response
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list) and len(parsed) > 0:
                # Safety: ensure we have at least as many bullets as original
                if len(parsed) >= len(original_bullets):
                    return [str(item).strip() for item in parsed]
                else:
                    # Pad missing with originals
                    result = [str(item).strip() for item in parsed]
                    result += original_bullets[len(parsed):]
                    return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: try line-by-line parsing
    lines = [
        line.lstrip("-•*123456789. ").strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("]")
    ]
    if len(lines) >= len(original_bullets):
        return lines[:len(original_bullets)]

    return original_bullets  # Safe fallback — return originals unchanged

# ── PROVIDER 1: Groq (Llama 3.3-70B — Free Tier) ─────────────────────────────
def enhance_with_groq(api_key: str, location: str, activity: str, bullet_points: list[str]) -> tuple[list[str], str]:
    """Elaborate bullet points using Groq's free-tier Llama 3.3 model."""
    if not api_key or not api_key.strip():
        return bullet_points, "No Groq API key provided."

    prompt = _build_prompt(location, activity, bullet_points)

    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional travel content writer. "
                    "You respond ONLY with valid JSON arrays of strings. "
                    "Never add commentary, headers, or markdown outside the JSON array."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1024,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            raw_text = result["choices"][0]["message"]["content"]
            return _parse_response(raw_text, bullet_points), ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err_json = json.loads(body)
            msg = err_json.get("error", {}).get("message", body)
        except Exception:
            msg = body
        return bullet_points, f"Groq API error {e.code}: {msg}"
    except urllib.error.URLError as e:
        return bullet_points, f"Network error: {e.reason}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return bullet_points, f"Response parse error: {e}"

# ── PROVIDER 2: Google Gemini Flash (Free Tier) ───────────────────────────────
def enhance_with_gemini(api_key: str, location: str, activity: str, bullet_points: list[str]) -> tuple[list[str], str]:
    """Elaborate bullet points using Google Gemini Flash (free tier)."""
    if not api_key or not api_key.strip():
        return bullet_points, "No Gemini API key provided."

    prompt = _build_prompt(location, activity, bullet_points)

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json",
        },
    }).encode("utf-8")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key.strip()}"
    )
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_response(raw_text, bullet_points), ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err_json = json.loads(body)
            msg = err_json.get("error", {}).get("message", body)
        except Exception:
            msg = body
        return bullet_points, f"Gemini API error {e.code}: {msg}"
    except urllib.error.URLError as e:
        return bullet_points, f"Network error: {e.reason}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return bullet_points, f"Response parse error: {e}"

# ── PROVIDER 3: Ollama (Local — 100% Free, No Key Needed) ────────────────────
def enhance_with_ollama(location: str, activity: str, bullet_points: list[str], model: str = "llama3.2", base_url: str = "http://localhost:11434") -> tuple[list[str], str]:
    """Elaborate bullet points using a locally running Ollama model."""
    prompt = _build_prompt(location, activity, bullet_points)

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.4},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result   = json.loads(resp.read().decode("utf-8"))
            raw_text = result.get("response", "")
            return _parse_response(raw_text, bullet_points), ""
    except urllib.error.URLError as e:
        return bullet_points, (
            f"Cannot reach Ollama at {base_url}. "
            "Make sure Ollama is running locally. Error: {e.reason}"
        )
    except (KeyError, json.JSONDecodeError) as e:
        return bullet_points, f"Ollama response parse error: {e}"

# ── Unified entry point ───────────────────────────────────────────────────────
def enhance_day_details(location: str, activity: str, bullet_points: list[str], provider: str = "groq", groq_api_key: str = "", gemini_api_key: str = "", ollama_model: str = "llama3.2", ollama_base_url: str = "http://localhost:11434") -> tuple[list[str], str]:
    """Main entry point. Calls the selected AI provider."""
    if not bullet_points:
        return bullet_points, "No bullet points to elaborate."

    if provider == "groq":
        return enhance_with_groq(groq_api_key, location, activity, bullet_points)
    elif provider == "gemini":
        return enhance_with_gemini(gemini_api_key, location, activity, bullet_points)
    elif provider == "ollama":
        return enhance_with_ollama(location, activity, bullet_points, model=ollama_model, base_url=ollama_base_url)
    else:
        return bullet_points, f"Unknown provider: {provider}"
