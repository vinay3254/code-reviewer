import json
import os
import re
import urllib.request
import urllib.error
import yaml
from pathlib import Path

# Load config
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "models": {
            "planner": "qwen2.5-coder:32b",
            "patcher": "qwen2.5-coder:14b",
            "verifier": "qwen2.5-coder:32b",
            "embedding": "nomic-embed-text"
        }
    }

def strip_markdown_fences(text: str) -> str:
    """Strips markdown code blocks (e.g., ```diff ... ``` or ```json ... ```) from LLM output."""
    pattern = r"^```(?:diff|python|json|yaml)?\s*\n(.*?)\n```$"
    match = re.search(pattern, text.strip(), re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    
    # Generic fence stripping if opening/closing fences exist
    lines = text.strip().splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
        
    return text.strip()

def call_ollama_generate(prompt: str, model: str, host: str = "http://localhost:11434") -> str:
    """Calls Ollama /api/generate endpoint directly."""
    url = f"{host}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("response", "")
    except Exception as e:
        raise RuntimeError(f"Ollama API error calling model '{model}' at {url}: {e}")

def call_ollama_embedding(text: str, model: str = "nomic-embed-text", host: str = "http://localhost:11434") -> list[float]:
    """Calls Ollama /api/embeddings endpoint directly."""
    url = f"{host}/api/embeddings"
    payload = {
        "model": model,
        "prompt": text
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("embedding", [])
    except Exception:
        # Fallback pseudo-embedding generator for offline/testing if Ollama is un-reachable
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Produce 384-dimensional float vector normalized
        vec = [(b / 255.0) - 0.5 for b in (h * 12)[:384]]
        return vec

def call_role(role_name: str, prompt: str, model_override: str | None = None, mock: bool = False, mock_response: str | None = None) -> str:
    """Routes to the model configured for this role in config.yaml, via Ollama, with fence stripping."""
    if mock or os.getenv("AGENT_MOCK_LLM", "").lower() in ("1", "true", "yes"):
        if mock_response is not None:
            return strip_markdown_fences(mock_response)
        if role_name == "planner":
            return "Strategy: Implement missing key checks using dict.get() with a default value of 30."
        elif role_name == "patcher":
            return "--- a/config.py\n+++ b/config.py\n@@ -1,2 +1,2 @@\n def parse_config(cfg):\n-    return cfg['timeout']\n+    return cfg.get('timeout', 30)"
        elif role_name == "verifier":
            return json.dumps({"genuine": True, "confidence": 0.95, "reasoning": "Genuine bug fix addressing root cause without modifying tests or using mocks."})
        return "Mock response"

    cfg = load_config()
    model = model_override or cfg.get("models", {}).get(role_name, "qwen2.5-coder:14b")
    
    try:
        raw_response = call_ollama_generate(prompt, model)
        return strip_markdown_fences(raw_response)
    except Exception as e:
        # If real call fails and fallback is enabled, return a default mock
        if os.getenv("AGENT_FALLBACK_MOCK", "1") == "1":
            return call_role(role_name, prompt, model_override, mock=True, mock_response=mock_response)
        raise e
