"""
src/config.py — Configurações centralizadas da aplicação.

Carrega variáveis de ambiente via pydantic-settings.
Único ponto de verdade para toda configuração da aplicação.

Uso:
    from src.config import get_settings
    settings = get_settings()
    print(settings.app_port)

    # Em testes, limpe o cache entre testes com:
    get_settings.cache_clear()
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "production", "test"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
VideoModel = Literal["wan2.1", "cogvideox", "hunyuan", "animatediff", "fake"]


class Settings(BaseSettings):
    """Configurações da aplicação carregadas do ambiente / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignora variáveis não declaradas sem erro
    )

    # ── API ──────────────────────────────────────────────────────────────────
    app_env: AppEnv = "development"
    app_host: str = "0.0.0.0"  # noqa: S104
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_version: str = "0.1.0"
    log_level: LogLevel = "INFO"

    # ── Banco de dados ────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/geracao_video.db"
    database_url_test: str = "sqlite:///./data/test.db"

    # ── Geração de vídeo ──────────────────────────────────────────────────────
    default_model: VideoModel = "animatediff"
    output_dir: str = "./outputs/videos"
    job_timeout_seconds: int = Field(default=600, ge=1, le=86400)  # 1s a 24h
    max_concurrent_jobs: int = Field(default=1, ge=1, le=10)

    # ── HuggingFace ───────────────────────────────────────────────────────────
    hf_token: SecretStr = SecretStr("")
    hf_home: str = "~/.cache/huggingface"

    # ── IA local: roteiro (Ollama) + áudio (Piper) — ADR-006 ──────────────────
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: int = Field(default=30, ge=1, le=600)
    ollama_max_retries: int = Field(default=2, ge=0, le=5)

    piper_binary: str = "piper"
    piper_voice_path: str = "~/.local/share/piper/voices/pt_BR-faber-medium.onnx"
    piper_timeout_seconds: int = Field(default=60, ge=1, le=600)

    # ── Hardware ──────────────────────────────────────────────────────────────
    force_cpu: bool = False

    # ── Dupla IA ──────────────────────────────────────────────────────────────
    gemini_api_key: SecretStr = SecretStr("")

    # ── Propriedades derivadas ────────────────────────────────────────────────

    @property
    def is_development(self) -> bool:
        """True se rodando em modo desenvolvimento."""
        return self.app_env == "development"

    @property
    def is_testing(self) -> bool:
        """True se rodando em modo de testes."""
        return self.app_env == "test"

    @property
    def is_production(self) -> bool:
        """True se rodando em produção."""
        return self.app_env == "production"

    # ── Validadores ──────────────────────────────────────────────────────────

    @field_validator("log_level", mode="before")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        """Garante que LOG_LEVEL seja sempre uppercase."""
        return str(v).upper()

    @field_validator("app_env", mode="before")
    @classmethod
    def lowercase_app_env(cls, v: str) -> str:
        """Garante que APP_ENV seja sempre lowercase."""
        return str(v).lower()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retorna a instância singleton de Settings.

    Usa lru_cache para criar a instância apenas uma vez por processo.
    Em testes, limpe o cache entre testes com:

        from src.config import get_settings
        get_settings.cache_clear()

    Ou use monkeypatch + importlib.reload(src.config) para isolamento completo.
    """
    return Settings()
