"""
Testes para OllamaScriptGenerator (src/core/generators/ollama.py).

Isola a rede com httpx.MockTransport — nenhuma chamada real ao Ollama.
"""

import json

import httpx
import pytest

from src.core.errors import GenerationError, GenerationTimeoutError, ScriptValidationError
from src.core.generators.ollama import OllamaScriptGenerator


def _client(handler: object) -> httpx.Client:
    """Cria um httpx.Client com MockTransport (sem I/O real)."""
    return httpx.Client(
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        base_url="http://testserver",
    )


def _judge_response(approved: bool, reason: str = "") -> dict[str, object]:
    """Resposta do juiz no formato {approved, reason}."""
    return {"response": json.dumps({"approved": approved, "reason": reason}), "done": True}


def _is_judge_call(request: httpx.Request) -> bool:
    """True se a requisição é uma chamada do auditor (system prompt do juiz)."""
    if request.method != "POST":
        return False
    payload = json.loads(request.content)
    return "auditor" in str(payload.get("system", ""))


def _auto_judge(handler: object) -> object:
    """Intercepta o juiz e aprova automaticamente (para testes não-juiz)."""

    def wrapped(request: httpx.Request) -> httpx.Response:
        if _is_judge_call(request):
            return httpx.Response(200, json=_judge_response(True))
        return handler(request)  # type: ignore[operator]

    return wrapped


def _make_generator(
    handler: object, *, auto_approve_judge: bool = True, **kwargs: object
) -> OllamaScriptGenerator:
    if auto_approve_judge:
        handler = _auto_judge(handler)
    defaults = {"retry_backoff": 0.0, "client": _client(handler)}
    defaults.update(kwargs)
    return OllamaScriptGenerator(**defaults)  # type: ignore[arg-type]


VALID_SCRIPT = {"scenes": [{"narration": "Era uma vez", "visual_prompt": "a forest"}]}


def _ollama_response(scenes: object) -> dict[str, object]:
    return {"response": json.dumps({"scenes": scenes}), "done": True}


class TestIsAvailable:
    def test_available_on_200(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"models": []})

        assert _make_generator(handler).is_available() is True

    def test_unavailable_on_connection_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        assert _make_generator(handler).is_available() is False

    def test_unavailable_on_500(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        assert _make_generator(handler).is_available() is False


class TestGenerateScript:
    def test_success_single_scene(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        script = _make_generator(handler).generate_script("conte uma historia")
        assert len(script.scenes) == 1
        assert script.scenes[0].narration == "Era uma vez"
        assert script.scenes[0].visual_prompt == "a forest"
        assert script.source_prompt == "conte uma historia"

    def test_success_multiple_scenes(self) -> None:
        scenes = [
            {"narration": "cena 1", "visual_prompt": "praia"},
            {"narration": "cena 2", "visual_prompt": "montanha"},
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_ollama_response(scenes))

        script = _make_generator(handler).generate_script("duas cenas")
        assert len(script.scenes) == 2
        assert script.scenes[1].visual_prompt == "montanha"

    def test_sends_json_format_and_stream_false(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        _make_generator(handler).generate_script("x")
        assert captured["format"] == "json"
        assert captured["stream"] is False
        assert "model" in captured

    def test_invalid_json_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"response": "nao eh json {", "done": True})

        with pytest.raises(GenerationError, match="JSON inv"):
            _make_generator(handler).generate_script("x")

    def test_schema_violation_raises(self) -> None:
        bad = [{"visual_prompt": "sem narracao"}]  # narration ausente

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_ollama_response(bad))

        with pytest.raises(GenerationError, match="esquema"):
            _make_generator(handler).generate_script("x")

    def test_empty_scenes_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_ollama_response([]))

        with pytest.raises(GenerationError, match="sem cenas"):
            _make_generator(handler).generate_script("x")

    def test_connection_error_retries_then_raises(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            raise httpx.ConnectError("down", request=request)

        with pytest.raises(GenerationError, match="rede"):
            _make_generator(handler, max_retries=2).generate_script("x")
        assert calls["n"] == 3  # 1 tentativa + 2 retries

    def test_5xx_retries_then_succeeds(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] < 3:
                return httpx.Response(503, json={"error": "indisponivel"})
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        script = _make_generator(handler, max_retries=3).generate_script("x")
        assert len(script.scenes) == 1
        assert calls["n"] == 3

    def test_4xx_does_not_retry(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(400, json={"error": "bad request"})

        with pytest.raises(GenerationError, match="erro"):
            _make_generator(handler, max_retries=3).generate_script("x")
        assert calls["n"] == 1  # erro de cliente não é retentado

    def test_timeout_raises_timeout_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

        with pytest.raises(GenerationTimeoutError):
            _make_generator(handler, max_retries=2).generate_script("x")

    def test_response_as_dict_is_accepted(self) -> None:
        # Algumas versões do Ollama já devolvem `response` como objeto (não string)
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"response": VALID_SCRIPT, "done": True})

        script = _make_generator(handler).generate_script("x")
        assert len(script.scenes) == 1
        assert script.scenes[0].narration == "Era uma vez"


class TestJudge:
    """Cenários do LLM-as-a-Judge (E11) — aprovação, correção e falha máxima."""

    def test_approves_on_first_attempt(self) -> None:
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                calls.append("judge")
                return httpx.Response(200, json=_judge_response(True))
            calls.append("generate")
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        script = _make_generator(handler, auto_approve_judge=False).generate_script(
            "conte uma historia"
        )
        assert len(script.scenes) == 1
        assert calls == ["generate", "judge"]

    def test_rejection_injects_reason_into_next_prompt(self) -> None:
        state: dict[str, object] = {"judge_n": 0, "gen_prompts": []}
        reason = "foge do tema: deveria ser sobre gatos"

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                state["judge_n"] = int(state["judge_n"]) + 1  # type: ignore[arg-type]
                if state["judge_n"] == 1:
                    return httpx.Response(200, json=_judge_response(False, reason))
                return httpx.Response(200, json=_judge_response(True))
            payload = json.loads(request.content)
            prompts: list[str] = state["gen_prompts"]  # type: ignore[assignment]
            prompts.append(str(payload["prompt"]))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        script = _make_generator(handler, auto_approve_judge=False).generate_script(
            "video sobre pombos"
        )
        assert len(script.scenes) == 1
        assert state["judge_n"] == 2
        prompts = state["gen_prompts"]
        assert len(prompts) == 2
        assert prompts[0] == "video sobre pombos"  # 1ª tentativa: prompt original
        assert "video sobre pombos" in prompts[1]  # tema preservado
        assert reason in prompts[1]  # reason do juiz injetado

    def test_max_attempts_raises_script_validation_error(self) -> None:
        counts = {"gen": 0, "judge": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                counts["judge"] += 1
                return httpx.Response(200, json=_judge_response(False, "fora do tema"))
            counts["gen"] += 1
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        with pytest.raises(ScriptValidationError, match="tentativas"):
            _make_generator(handler, auto_approve_judge=False).generate_script("x")
        assert counts == {"gen": 3, "judge": 3}


    def test_judge_payload_carries_prompt_and_script(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                captured.update(json.loads(request.content))
                return httpx.Response(200, json=_judge_response(True))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        _make_generator(handler, auto_approve_judge=False).generate_script("um dragão")
        assert "um dragão" in str(captured["prompt"])
        assert "Era uma vez" in str(captured["prompt"])  # cenas serializadas
        assert "auditor" in str(captured["system"])

    def test_invalid_judge_json_rejects_with_default_reason(self) -> None:
        """Fail-closed: JSON inválido do juiz = reprovação com reason padrão."""
        state: dict[str, object] = {"judge_n": 0, "gen_prompts": []}

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                state["judge_n"] = int(state["judge_n"]) + 1  # type: ignore[arg-type]
                if state["judge_n"] == 1:
                    return httpx.Response(
                        200, json={"response": "isto nao eh json {", "done": True}
                    )
                return httpx.Response(200, json=_judge_response(True))
            payload = json.loads(request.content)
            prompts: list[str] = state["gen_prompts"]  # type: ignore[assignment]
            prompts.append(str(payload["prompt"]))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        script = _make_generator(handler, auto_approve_judge=False).generate_script(
            "flores"
        )
        assert len(script.scenes) == 1
        assert state["judge_n"] == 2
        prompts = state["gen_prompts"]
        assert "Erro de validação interna do auditor" in prompts[1]  # reason padrão

    def test_always_invalid_judge_json_raises_after_max_attempts(self) -> None:
        judge_calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                judge_calls["n"] += 1
                return httpx.Response(
                    200, json={"response": "<html>erro</html>", "done": True}
                )
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        with pytest.raises(ScriptValidationError, match="tentativas"):
            _make_generator(handler, auto_approve_judge=False).generate_script("x")
        assert judge_calls["n"] == 3  # 3 tentativas consumidas (fail-closed)


class _CtxRecorder:
    """Logger falso que registra (evento, contextvars) no momento da chamada."""

    def __init__(self) -> None:
        import structlog.contextvars

        self.records: list[tuple[str, dict]] = []
        self._cv = structlog.contextvars

    def _add(self, event: str) -> None:
        self.records.append((event, dict(self._cv.get_contextvars())))

    def info(self, event: str, **kwargs: object) -> None:
        self._add(event)

    def warning(self, event: str, **kwargs: object) -> None:
        self._add(event)

    def error(self, event: str, **kwargs: object) -> None:
        self._add(event)


def _patch_ollama_logger(monkeypatch, recorder: object) -> None:
    """
    Instala `recorder` como logger do ollama que a classe realmente usa.

    Patcha o `__globals__` do método em vez do módulo importado no teste:
    `test_core_factory` purga `sys.modules["src.core.generators.ollama"]`,
    e um import posterior criaria um segundo módulo com outro `logger`.
    """
    monkeypatch.setitem(
        OllamaScriptGenerator.generate_script.__globals__, "logger", recorder
    )


class TestJudgeObservability:
    """Logs do juiz herdam correlation_id via structlog contextvars (E07)."""

    def test_judge_logs_inherit_correlation_id(self, monkeypatch) -> None:
        import structlog.contextvars

        recorder = _CtxRecorder()
        _patch_ollama_logger(monkeypatch, recorder)

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                return httpx.Response(200, json=_judge_response(True))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        with structlog.contextvars.bound_contextvars(correlation_id="corr-e11"):
            _make_generator(handler, auto_approve_judge=False).generate_script("x")

        verdict = next(r for r in recorder.records if r[0] == "script_judge_verdict")
        assert verdict[1].get("correlation_id") == "corr-e11"

    def test_rejection_and_failure_logs_emitted(self, monkeypatch) -> None:
        recorder = _CtxRecorder()
        _patch_ollama_logger(monkeypatch, recorder)

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                return httpx.Response(200, json=_judge_response(False, "fora do tema"))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        with pytest.raises(ScriptValidationError):
            _make_generator(handler, auto_approve_judge=False).generate_script("x")

        rejected = [r for r in recorder.records if r[0] == "script_judge_rejected"]
        assert len(rejected) == 3  # uma reprovação por tentativa
        assert any(r[0] == "script_validation_failed" for r in recorder.records)
        approved = [r for r in recorder.records if r[0] == "script_judge_verdict"]
        assert len(approved) == 3

    def test_approved_judge_emits_verdict_without_warning(self, monkeypatch) -> None:
        recorder = _CtxRecorder()
        _patch_ollama_logger(monkeypatch, recorder)

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                return httpx.Response(200, json=_judge_response(True))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        _make_generator(handler, auto_approve_judge=False).generate_script("x")
        # Aprovação direta: nenhum warning de parse, mas o veredito é logado.
        assert not any(r[0] == "script_judge_unparseable" for r in recorder.records)
        assert any(r[0] == "script_judge_verdict" for r in recorder.records)

    def test_invalid_judge_json_logs_warning(self, monkeypatch) -> None:
        """Parse inválido do juiz emite warning (fail-closed, E11 restrito)."""
        recorder = _CtxRecorder()
        _patch_ollama_logger(monkeypatch, recorder)
        judge_n = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if _is_judge_call(request):
                judge_n["n"] += 1
                if judge_n["n"] == 1:
                    return httpx.Response(200, json={"response": "lixo {", "done": True})
                return httpx.Response(200, json=_judge_response(True))
            return httpx.Response(200, json=_ollama_response(VALID_SCRIPT["scenes"]))

        _make_generator(handler, auto_approve_judge=False).generate_script("x")
        warnings = [r for r in recorder.records if r[0] == "script_judge_unparseable"]
        assert len(warnings) == 1
        # Reprovação com reason padrão seguiu o warning.
        assert any(r[0] == "script_judge_rejected" for r in recorder.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
