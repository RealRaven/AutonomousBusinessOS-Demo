# config/settings.py
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

BASE_DIR = Path(__file__).parent.resolve()
DB_DIR = BASE_DIR / "dbs"
CHROMA_DIR = DB_DIR / "chroma"

def env(key: str, default: str = None):
    return os.getenv(key, default)

@dataclass(frozen=True)
class AppConfig:
    base_dir: Path = BASE_DIR
    db_dir: Path = DB_DIR
    chroma_dir: Path = CHROMA_DIR

    ollama_host: str = env("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = env("OLLAMA_MODEL", "qwen3.5:4b")
    temperature: float = float(env("OLLAMA_TEMPERATURE", "0.7"))
    max_tokens: int = int(env("OLLAMA_MAX_TOKENS", "4096"))

    embedding_model: str = env("OLLAMA_EMBEDDING_MODEL", "mxbai-embed-large")
    chunk_size: int = int(env("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(env("CHUNK_OVERLAP", "200"))

    app_title: str = env("APP_TITLE", "Autonomous Business OS Demo")
    app_description: str = env("APP_DESCRIPTION", "AI-Powered Business Management with RAG")
    theme: str = env("APP_THEME", "soft")

    categories: List[str] = field(default_factory=lambda: ["customers"])

settings = AppConfig()