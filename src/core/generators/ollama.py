"""
src/core/generators/ollama.py — Gerador de roteiro via LLM local (Ollama).

Implementa `ScriptGenerator` chamando o endpoint `/api/generate` de um
servidor Ollama local por HTTP (httpx), pedindo saída em JSON e convertendo
para o tipo de domínio `Script`. Vide ADR-006.

Sem GPU/torch necessário — apenas um servidor Ollama acessível.

Inclui **LLM-as-a-Judge** (E11): após cada geração, um auditor valida se o
roteiro atende estritamente ao prompt do usuário; reprovações injetam o
`reason` na próxima tentativa (máx. 3) e, no limite, levantam
`ScriptValidationError` — fail-closed em JSON inválido do auditor.
"""

import json
import time

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from src.core.errors import (
    GenerationError,
    GenerationTimeoutError,
    ScriptValidationError,
)
from src.core.interfaces import Scene, Script

logger = structlog.get_logger(__name__)

_JUDGE_SYSTEM_PROMPT = (
    "Você é um auditor. Verifique se o ROTEIRO atende estritamente ao "
    "PROMPT do usuário. Responda APENAS com um JSON contendo "
    "approved: true/false e reason: 'sua justificativa'."
)

# Motivo injetado quando o JSON do auditor não é parseável (fail-closed, E11).
_JUDGE_DEFAULT_REASON = (
    "Erro de validação interna do auditor. Revise o roteiro e "
    "garanta total fidelidade ao prompt."
)

_MAX_JUDGE_ATTEMPTS = 3

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


class _JudgeModel(BaseModel):
    """Esquema do veredito do auditor LLM (E11)."""

    approved: bool
    reason: str = ""


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
        Gera e **audita** um `Script` (LLM-as-a-Judge, E11).

        Até `_MAX_JUDGE_ATTEMPTS` tentativas: gera o roteiro, envia ao
        auditor e, se reprovado, regenera injetando o `reason` no prompt.
        JSON inválido do auditor é reprovação com motivo padrão (fail-closed).

        Raises:
            ScriptValidationError: Reprovado nas `_MAX_JUDGE_ATTEMPTS`.
            GenerationTimeoutError: Requisição excedeu o tempo limite.
            GenerationError: Falha de rede esgotada ou roteiro inválido.
        """
        feedback: str | None = None
        for attempt in range(1, _MAX_JUDGE_ATTEMPTS + 1):
            attempt_prompt = (
                prompt
                if feedback is None
                else self._correction_prompt(prompt, feedback)
            )
            script = self._generate_once(attempt_prompt, source_prompt=prompt)
            verdict = self._judge(prompt, script, attempt)
            logger.info(
                "script_judge_verdict",
                attempt=attempt,
                approved=verdict.approved,
                reason=verdict.reason,
                model=self._model,
            )
            if verdict.approved:
                return script
            logger.warning(
                "script_judge_rejected", attempt=attempt, reason=verdict.reason
            )
            feedback = verdict.reason or _JUDGE_DEFAULT_REASON

        logger.error(
            "script_validation_failed",
            attempts=_MAX_JUDGE_ATTEMPTS,
            reason=feedback,
        )
        raise ScriptValidationError(
            f"Roteiro reprovado pelo auditor após {_MAX_JUDGE_ATTEMPTS} "
            f"tentativas: {feedback}"
        )

    @staticmethod
    def _correction_prompt(prompt: str, reason: str) -> str:
        """Injeta o motivo da reprovação na nova tentativa (E11)."""
        return (
            f"{prompt}\n\n[CONTROLE DE QUALIDADE]\n"
            "Sua versão anterior foi reprovada pelo auditor. "
            f"Motivo: {reason}. Gere um novo roteiro corrigindo esse "
            "problema, sem fugir do pedido original."
        )

    def _generate_once(self, attempt_prompt: str, source_prompt: str) -> Script:
        """Uma tentativa de geração de roteiro (chamada /api/generate)."""
        payload: dict[str, object] = {
            "model": self._model,
            "prompt": attempt_prompt,
            "system": _SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
        }
        response = self._post_with_retry("/api/generate", payload)

        data = response.json()
        raw = data.get("response", "")
        if not isinstance(raw, str):
            raw = json.dumps(raw)
        return self._parse_script(raw, source_prompt=source_prompt)

    def _judge(self, user_prompt: str, script: Script, attempt: int) -> _JudgeModel:
        """
        Audita o roteiro contra o prompt original.

        Fail-closed: JSON inválido/inparseável = reprovação com
        `_JUDGE_DEFAULT_REASON` + warning `script_judge_unparseable` (E11).
        """
        scenes = [
            {"narration": s.narration, "visual_prompt": s.visual_prompt}
            for s in script.scenes
        ]
        judge_user = (
            f"PROMPT DO USUÁRIO:\n{user_prompt}\n\n"
            f"ROTEIRO GERADO:\n"
            f"{json.dumps({'scenes': scenes}, ensure_ascii=False)}"
        )
        payload: dict[str, object] = {
            "model": self._model,
            "prompt": judge_user,
            "system": _JUDGE_SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
        }
        start = time.perf_counter()
        response = self._post_with_retry("/api/generate", payload)
        try:
            data = response.json()
            raw = data.get("response", "")
            if not isinstance(raw, str):
                raw = json.dumps(raw)
            verdict = _JudgeModel.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "script_judge_unparseable", attempt=attempt, error=str(exc)
            )
            return _JudgeModel(approved=False, reason=_JUDGE_DEFAULT_REASON)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "script_judge_call", attempt=attempt, duration_ms=duration_ms
        )
        return verdict

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
