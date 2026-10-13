"""
src/core/generators/ollama.py — Gerador de roteiro via LLM local (Ollama).

Implementa `ScriptGenerator` chamando o endpoint `/api/generate` de um
servidor Ollama local por HTTP (httpx), pedindo saída em JSON e convertendo
para o tipo de domínio `Script`. Vide ADR-006.

Sem GPU/torch necessário — apenas um servidor Ollama acessível.
"""

import json
import time

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from src.core.errors import GenerationError, GenerationTimeoutError
from src.core.interfaces import Scene, Script

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "Você é um roteirista de vídeos curtos. Dado o pedido do usuário, produza "
    "um roteiro em JSON no formato:\n"
    '{"scenes": [{"narration": "<texto falado>", '
    '"visual_prompt": "<prompt visual para IA de vídeo>"}]}\n'
    "Gere de 1 a 5 cenas. Responda APENAS com JSON válido, sem texto extra."
)


class _SceneModel(BaseModel):
    """Esquema intermediário de uma cena na resposta do Ollama."""

    narration: str
    visual_prompt: str


class _ScriptModel(BaseModel):
    """Esquema intermediário do roteiro na resposta do Ollama."""

    scenes: list[_SceneModel]


class OllamaScriptGenerator:
    """
    `ScriptGenerator` real baseado em um servidor Ollama local.

    Args:
        base_url: URL base do servidor Ollama (default das settings).
        model: Nome do modelo Ollama (default das settings).
        timeout: Timeout HTTP em segundos (default das settings).
        max_retries: Tentativas extras em erro de rede/5xx (default settings).
        retry_backoff: Espera base (s) entre tentativas — 0 em testes.
        client: `httpx.Client` injetável (usado em testes via MockTransport).
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        retry_backoff: float = 0.5,
        client: httpx.Client | None = None,
    ) -> None:
        from src.config import get_settings

        settings = get_settings()
        self._base_url = (base_url or settings.ollama_host).rstrip("/")
        self._model = model or settings.ollama_model
        self._timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
        self._max_retries = (
            max_retries if max_retries is not None else settings.ollama_max_retries
        )
        self._retry_backoff = retry_backoff
        self._client = (
            client
            if client is not None
            else httpx.Client(base_url=self._base_url, timeout=self._timeout)
        )

    def is_available(self) -> bool:
        """True se o servidor Ollama responde em `/api/tags`."""
        try:
            response = self._client.get("/api/tags")
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    def generate_script(self, prompt: str) -> Script:
        """
        Gera um `Script` a partir do prompt via Ollama.

        Raises:
            GenerationTimeoutError: Requisição excedeu o tempo limite.
            GenerationError: Falha de rede esgotada ou roteiro inválido.
        """
        payload: dict[str, object] = {
            "model": self._model,
            "prompt": prompt,
            "system": _SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
        }
        response = self._post_with_retry("/api/generate", payload)

        data = response.json()
        raw = data.get("response", "")
        if not isinstance(raw, str):
            raw = json.dumps(raw)
        return self._parse_script(raw, source_prompt=prompt)

    def _post_with_retry(self, path: str, payload: dict[str, object]) -> httpx.Response:
        """POST com retry em erro de rede e 5xx; timeout não é retentado."""
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            is_last = attempt == self._max_retries
            try:
                response = self._client.post(path, json=payload)
                response.raise_for_status()
                return response
            except httpx.TimeoutException as exc:
                raise GenerationTimeoutError(
                    f"Ollama não respondeu em {self._timeout}s."
                ) from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and not is_last:
                    last_exc = exc
                    time.sleep(self._retry_backoff * (attempt + 1))
                    continue
                raise GenerationError(f"Ollama retornou erro: {exc}") from exc
            except httpx.TransportError as exc:
                if not is_last:
                    last_exc = exc
                    time.sleep(self._retry_backoff * (attempt + 1))
                    continue
                raise GenerationError(f"Falha de rede ao chamar Ollama: {exc}") from exc
        # Inalcançável na prática: o loop sempre retorna ou levanta antes.
        raise GenerationError(f"Falha ao chamar Ollama: {last_exc}")  # pragma: no cover

    def _parse_script(self, raw: str, source_prompt: str) -> Script:
        """Converte a string JSON do Ollama em um `Script` validado."""
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GenerationError(f"Ollama retornou JSON inválido: {exc}") from exc

        try:
            model = _ScriptModel.model_validate(payload)
        except ValidationError as exc:
            raise GenerationError(f"Roteiro fora do esquema esperado: {exc}") from exc

        scenes = tuple(
            Scene(narration=s.narration, visual_prompt=s.visual_prompt)
            for s in model.scenes
        )
        if not scenes:
            raise GenerationError("Ollama retornou um roteiro sem cenas.")

        logger.info("script_generated", model=self._model, scenes=len(scenes))
        return Script(scenes=scenes, source_prompt=source_prompt)
