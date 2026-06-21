"""
llm.py — Communicates with the local Ollama API.

Sends prompts to llama3.2:3b running on localhost:11434
and returns the model's text response.
"""

import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"


def ask_llama(prompt: str, system: str = "") -> str:
    """
    Send a prompt to Llama via Ollama and return the full response text.

    Args:
        prompt:  The user message / conversation history.
        system:  Optional system-level instruction (overrides default if set).

    Returns:
        The model's reply as a plain string.
    """
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,   # Wait for the complete response
        "options": {
            "temperature": 0.1,   # Low temperature = more deterministic
            "num_predict": 300,   # Max tokens per reply
        }
    }

    if system:
        payload["system"] = system

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120   # Llama may take a moment on t3.small
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Is it running? Try: sudo systemctl start ollama"
    except requests.exceptions.Timeout:
        return "ERROR: Ollama timed out. The model may be loading — try again in 30 seconds."
    except requests.exceptions.HTTPError as e:
        return f"ERROR: Ollama HTTP error — {str(e)}"
    except Exception as e:
        return f"ERROR: Unexpected error — {str(e)}"


def check_ollama_running() -> bool:
    """Quick health check — returns True if Ollama is reachable."""
    try:
        r = requests.get("http://localhost:11434", timeout=5)
        return r.status_code == 200
    except Exception:
        return False
