from llm.ollama_client import call_ollama_embedding

def embed_text(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Embeds task description + error trace to produce a vector embedding."""
    return call_ollama_embedding(text, model=model)
