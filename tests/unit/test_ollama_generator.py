"""
Testes para OllamaScriptGenerator (src/core/generators/ollama.py).

Isola a rede com httpx.MockTransport — nenhuma chamada real ao Ollama.
"""

import json

import httpx
import pytest

from src.core.errors import GenerationError, GenerationTimeoutError
from src.core.generators.ollama import OllamaScriptGenerator


def _client(handler: object) -> httpx.Client:
    """Cria um httpx.Client com MockTransport (sem I/O real)."""
    return httpx.Client(
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        base_url="http://testserver",
    )


def _make_generator(handler: object, **kwargs: object) -> OllamaScriptGenerator:
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
