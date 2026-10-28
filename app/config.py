"""All settings come from environment variables / .env. No secrets in code."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    def __init__(self):
        self.data_dir = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
        self.db_path = self.data_dir / "companybrain.db"
        self.chroma_dir = self.data_dir / "chroma"
        self.upload_dir = self.data_dir / "uploads"
        # If SECRET_KEY is missing we make a random one (logins reset on restart).
        self.secret_key = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
        self.token_minutes = int(os.getenv("TOKEN_MINUTES", "60"))
        self.max_upload_bytes = int(float(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024)
        self.embedding_backend = os.getenv("EMBEDDING_BACKEND", "sentence-transformers")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.top_k = int(os.getenv("TOP_K", "4"))
        self.max_distance = float(os.getenv("MAX_DISTANCE", "0.65"))
        self.llm_provider = os.getenv("LLM_PROVIDER", "extractive")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.allow_external_llm = os.getenv("ALLOW_EXTERNAL_LLM", "false").lower() in ("1", "true", "yes")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.upload_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
