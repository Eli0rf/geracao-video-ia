"""
Testes para os contratos do motor de geração (src/core/interfaces.py).

Cobre os tipos de domínio `Scene` e `Script` e a conformidade das
implementações com os Protocols. Sem I/O real.
"""

import pytest

from src.core.fakes import (
    FakeAudioSynthesizer,
    FakeScriptGenerator,
    FakeVideoGenerator,
)
from src.core.interfaces import (
    AudioSynthesizer,
    Scene,
    Script,
    ScriptGenerator,
    VideoGenerator,
)


class TestScene:
    def test_create_scene(self) -> None:
        scene = Scene(narration="Um gato na lua", visual_prompt="cat on moon")
        assert scene.narration == "Um gato na lua"
        assert scene.visual_prompt == "cat on moon"

    def test_scene_is_frozen(self) -> None:
        scene = Scene(narration="a", visual_prompt="b")
        with pytest.raises(AttributeError):
            scene.narration = "outro"  # type: ignore[misc]

    def test_scene_missing_field(self) -> None:
        with pytest.raises(TypeError):
            Scene(visual_prompt="b")  # type: ignore[call-arg]


class TestScript:
    def test_create_script(self) -> None:
        scene = Scene(narration="a", visual_prompt="b")
        script = Script(scenes=(scene,), source_prompt="prompt original")
        assert len(script.scenes) == 1
        assert script.source_prompt == "prompt original"

    def test_empty_scenes_rejected(self) -> None:
        with pytest.raises(ValueError, match="ao menos uma cena"):
            Script(scenes=(), source_prompt="p")


class TestFakesConformance:
    """As fakes devem satisfazer os Protocols definidos em interfaces.py."""

    def test_fake_script_generator_conforms(self) -> None:
        assert isinstance(FakeScriptGenerator(), ScriptGenerator)

    def test_fake_audio_synthesizer_conforms(self) -> None:
        assert isinstance(FakeAudioSynthesizer(), AudioSynthesizer)

    def test_fake_video_generator_conforms(self) -> None:
        assert isinstance(FakeVideoGenerator(), VideoGenerator)
