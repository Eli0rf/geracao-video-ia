"""
Testes para a factory do motor de geração (src/core/factory.py).

Cobre a resolução de implementações e o fallback automático:
    - get_generator("fake") → FakeVideoGenerator
    - modelo real indisponível (ModelUnavailableError) → fallback fake
    - módulo de modelo ausente (ImportError) → fallback fake
    - get_script_generator()/get_audio_synthesizer() sem serviço real → fake

Sem I/O real — módulos "reais" são injetados em sys.modules quando necessário.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from src.core import factory
from src.core.factory import (
    get_audio_synthesizer,
    get_fake_generator,
    get_generator,
    get_script_generator,
)
from src.core.fakes import (
    FakeAudioSynthesizer,
    FakeScriptGenerator,
    FakeVideoGenerator,
)
from src.core.interfaces import AudioSynthesizer, ScriptGenerator, VideoGenerator


def _inject_module(name: str, **attrs: object) -> None:
    """Injeta um módulo falso em sys.modules com os atributos dados."""
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


class TestGetGenerator:
    def test_fake_model_returns_fake(self) -> None:
        assert isinstance(get_generator("fake"), FakeVideoGenerator)

    def test_module_absent_falls_back_to_fake(self) -> None:
        # Módulo animatediff ainda não existe neste bloco → ImportError → fake
        assert isinstance(get_generator("animatediff"), FakeVideoGenerator)

    def test_unavailable_model_falls_back_to_fake(self) -> None:
        # Módulo existe mas is_available() == False → ModelUnavailableError → fake
        fake_model = MagicMock()
        fake_model.is_available.return_value = False
        _inject_module(
            "src.core.generators",
            animatediff=types.ModuleType("src.core.generators.animatediff"),
        )
        _inject_module(
            "src.core.generators.animatediff",
            AnimateDiffGenerator=MagicMock(return_value=fake_model),
        )
        importlib.reload(factory)

        marker = FakeVideoGenerator()
        try:
            with patch.object(factory, "get_fake_generator", return_value=marker) as mock_fake:
                result = factory.get_generator("animatediff")
                assert result is marker
                mock_fake.assert_called_once()
        finally:
            sys.modules.pop("src.core.generators.animatediff", None)
            sys.modules.pop("src.core.generators", None)
            importlib.reload(factory)

    def test_returns_real_when_model_available(self) -> None:
        # Módulo existe e is_available() == True → retorna a implementação real
        good_model = MagicMock()
        good_model.is_available.return_value = True
        _inject_module(
            "src.core.generators",
            animatediff=types.ModuleType("src.core.generators.animatediff"),
        )
        _inject_module(
            "src.core.generators.animatediff",
            AnimateDiffGenerator=MagicMock(return_value=good_model),
        )
        importlib.reload(factory)
        try:
            assert factory.get_generator("animatediff") is good_model
        finally:
            sys.modules.pop("src.core.generators.animatediff", None)
            sys.modules.pop("src.core.generators", None)
            importlib.reload(factory)


class TestGetScriptGenerator:
    def test_falls_back_to_fake_when_ollama_absent(self) -> None:
        # Módulo ollama ainda não existe neste bloco → ImportError → fake
        gen = get_script_generator()
        assert isinstance(gen, ScriptGenerator)

    def test_returns_real_when_ollama_available(self) -> None:
        # Módulo existe e is_available() == True → retorna a implementação real
        _inject_module(
            "src.core.generators",
            ollama=types.ModuleType("src.core.generators.ollama"),
        )
        available = MagicMock()
        available.is_available.return_value = True
        _inject_module(
            "src.core.generators.ollama",
            OllamaScriptGenerator=MagicMock(return_value=available),
        )
        importlib.reload(factory)
        try:
            assert factory.get_script_generator() is available
        finally:
            sys.modules.pop("src.core.generators.ollama", None)
            sys.modules.pop("src.core.generators", None)
            importlib.reload(factory)

    def test_falls_back_when_ollama_unavailable(self) -> None:
        _inject_module(
            "src.core.generators",
            ollama=types.ModuleType("src.core.generators.ollama"),
        )
        unavailable = MagicMock()
        unavailable.is_available.return_value = False
        _inject_module(
            "src.core.generators.ollama",
            OllamaScriptGenerator=MagicMock(return_value=unavailable),
        )
        importlib.reload(factory)
        try:
            assert isinstance(factory.get_script_generator(), FakeScriptGenerator)
        finally:
            sys.modules.pop("src.core.generators.ollama", None)
            sys.modules.pop("src.core.generators", None)
            importlib.reload(factory)


class TestGetAudioSynthesizer:
    def test_falls_back_to_fake_when_piper_absent(self) -> None:
        # Módulo piper ainda não existe neste bloco → ImportError → fake
        assert isinstance(get_audio_synthesizer(), AudioSynthesizer)

    def test_returns_real_when_piper_available(self) -> None:
        # Módulo existe e is_available() == True → retorna a implementação real
        _inject_module(
            "src.core.generators",
            piper=types.ModuleType("src.core.generators.piper"),
        )
        available = MagicMock()
        available.is_available.return_value = True
        _inject_module(
            "src.core.generators.piper",
            PiperAudioSynthesizer=MagicMock(return_value=available),
        )
        importlib.reload(factory)
        try:
            assert factory.get_audio_synthesizer() is available
        finally:
            sys.modules.pop("src.core.generators.piper", None)
            sys.modules.pop("src.core.generators", None)
            importlib.reload(factory)

    def test_falls_back_when_piper_unavailable(self) -> None:
        _inject_module(
            "src.core.generators",
            piper=types.ModuleType("src.core.generators.piper"),
        )
        unavailable = MagicMock()
        unavailable.is_available.return_value = False
        _inject_module(
            "src.core.generators.piper",
            PiperAudioSynthesizer=MagicMock(return_value=unavailable),
        )
        importlib.reload(factory)
        try:
            assert isinstance(factory.get_audio_synthesizer(), FakeAudioSynthesizer)
        finally:
            sys.modules.pop("src.core.generators.piper", None)
            sys.modules.pop("src.core.generators", None)
            importlib.reload(factory)


class TestGetFakeGenerator:
    def test_returns_video_generator(self) -> None:
        assert isinstance(get_fake_generator(), VideoGenerator)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

