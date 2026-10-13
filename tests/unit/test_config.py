"""
Testes unitários para src/config.py.

Verificam que as configurações carregam corretamente de variáveis de ambiente,
que valores padrão existem, e que validações funcionam.
"""



class TestAppSettings:
    """Testa carregamento das configurações da aplicação."""

    def test_default_app_env(self, monkeypatch):
        """APP_ENV tem default 'development' quando não definido."""
        monkeypatch.delenv("APP_ENV", raising=False)
        # Reimporta para pegar o estado limpo
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.app_env == "development"

    def test_default_host(self, monkeypatch):
        """APP_HOST tem default '0.0.0.0'."""
        monkeypatch.delenv("APP_HOST", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.app_host == "0.0.0.0"  # noqa: S104

    def test_default_port(self, monkeypatch):
        """APP_PORT tem default 8000."""
        monkeypatch.delenv("APP_PORT", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.app_port == 8000

    def test_default_version(self, monkeypatch):
        """APP_VERSION tem default '0.1.0'."""
        monkeypatch.delenv("APP_VERSION", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.app_version == "0.1.0"

    def test_custom_env_from_environment(self, monkeypatch):
        """Valores de ambiente sobrescrevem os defaults."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_PORT", "9000")
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.app_env == "production"
        assert settings.app_port == 9000

    def test_is_development_property(self, monkeypatch):
        """Propriedade is_development retorna True apenas para APP_ENV=development."""
        monkeypatch.setenv("APP_ENV", "development")
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.is_development is True

    def test_is_not_development_in_production(self, monkeypatch):
        """is_development retorna False para APP_ENV=production."""
        monkeypatch.setenv("APP_ENV", "production")
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.is_development is False

    def test_is_testing_property(self, monkeypatch):
        """Propriedade is_testing retorna True apenas para APP_ENV=test."""
        monkeypatch.setenv("APP_ENV", "test")
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.is_testing is True

    def test_log_level_default(self, monkeypatch):
        """LOG_LEVEL tem default 'INFO'."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.log_level == "INFO"

    def test_log_level_uppercased(self, monkeypatch):
        """LOG_LEVEL é sempre uppercase."""
        monkeypatch.setenv("LOG_LEVEL", "debug")
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.log_level == "DEBUG"


class TestDatabaseSettings:
    """Testa configurações do banco de dados."""

    def test_default_database_url(self, monkeypatch):
        """DATABASE_URL tem default para SQLite local."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert "sqlite" in settings.database_url

    def test_test_database_url_differs_from_main(self, monkeypatch):
        """DATABASE_URL_TEST é diferente de DATABASE_URL para não poluir banco de dev."""
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.database_url != settings.database_url_test


class TestVideoSettings:
    """Testa configurações de geração de vídeo."""

    def test_default_model(self, monkeypatch):
        """DEFAULT_MODEL tem default 'animatediff'."""
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.default_model == "animatediff"

    def test_default_job_timeout(self, monkeypatch):
        """JOB_TIMEOUT_SECONDS tem default 600 (10 minutos)."""
        monkeypatch.delenv("JOB_TIMEOUT_SECONDS", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.job_timeout_seconds == 600

    def test_default_max_concurrent_jobs(self, monkeypatch):
        """MAX_CONCURRENT_JOBS tem default 1."""
        monkeypatch.delenv("MAX_CONCURRENT_JOBS", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.max_concurrent_jobs == 1


class TestGetSettings:
    """Testa a função get_settings()."""

    def test_returns_settings_instance(self):
        """get_settings() retorna uma instância de Settings."""
        import src.config as cfg
        settings = cfg.get_settings()
        assert isinstance(settings, cfg.Settings)

    def test_get_settings_is_callable_multiple_times(self):
        """get_settings() pode ser chamada múltiplas vezes sem erro."""
        import src.config as cfg
        s1 = cfg.get_settings()
        s2 = cfg.get_settings()
        assert s1.app_version == s2.app_version


class TestLocalAISettings:
    """Testa configurações de IA local: roteiro (Ollama) e áudio (Piper)."""

    def test_default_ollama_host(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.ollama_host == "http://localhost:11434"

    def test_default_ollama_model(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.ollama_model == "llama3.2"

    def test_default_piper_voice_path(self, monkeypatch):
        monkeypatch.delenv("PIPER_VOICE_PATH", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert "pt_BR" in settings.piper_voice_path

    def test_ollama_timeout_validation(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "0")
        import importlib

        import pytest
        from pydantic import ValidationError

        import src.config as cfg
        importlib.reload(cfg)
        with pytest.raises(ValidationError):
            cfg.get_settings()

    def test_piper_timeout_validation(self, monkeypatch):
        monkeypatch.setenv("PIPER_TIMEOUT_SECONDS", "9999")
        import importlib

        import pytest
        from pydantic import ValidationError

        import src.config as cfg
        importlib.reload(cfg)
        with pytest.raises(ValidationError):
            cfg.get_settings()

    def test_ollama_max_retries_default(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MAX_RETRIES", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.ollama_max_retries == 2

    def test_default_ffmpeg_binary(self, monkeypatch):
        monkeypatch.delenv("FFMPEG_BINARY", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.ffmpeg_binary == "ffmpeg"

    def test_default_ffmpeg_timeout(self, monkeypatch):
        monkeypatch.delenv("FFMPEG_TIMEOUT_SECONDS", raising=False)
        import importlib

        import src.config as cfg
        importlib.reload(cfg)
        settings = cfg.get_settings()
        assert settings.ffmpeg_timeout_seconds == 300

    def test_ffmpeg_timeout_validation(self, monkeypatch):
        monkeypatch.setenv("FFMPEG_TIMEOUT_SECONDS", "0")
        import importlib

        import pytest
        from pydantic import ValidationError

        import src.config as cfg
        importlib.reload(cfg)
        with pytest.raises(ValidationError):
            cfg.get_settings()
