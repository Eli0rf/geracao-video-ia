"""
Testes para AnimateDiffGenerator (src/core/generators/animatediff.py).

Mock total de torch/diffusers — nenhum peso baixado, nenhuma GPU usada.
Os módulos pesados são injetados em sys.modules via fixtures.
"""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.errors import GenerationError


def _inject_torch(mps_available: bool) -> MagicMock:
    """Injeta um torch falso com o backend MPS configurável."""
    torch_mod = types.ModuleType("torch")
    backends = types.ModuleType("torch.backends")
    mps = types.ModuleType("torch.backends.mps")
    mps.is_available = MagicMock(return_value=mps_available)  # type: ignore[attr-defined]
    backends.mps = mps  # type: ignore[attr-defined]
    torch_mod.backends = backends  # type: ignore[attr-defined]
    sys.modules["torch"] = torch_mod
    sys.modules["torch.backends"] = backends
    sys.modules["torch.backends.mps"] = mps
    return MagicMock()


def _inject_diffusers(pipeline_mock: MagicMock) -> None:
    """Injeta diffusers falso com AnimateDiffPipeline e export_to_video."""
    diffusers = types.ModuleType("diffusers")
    cls_mock = MagicMock()
    cls_mock.from_pretrained = MagicMock(return_value=pipeline_mock)
    diffusers.AnimateDiffPipeline = cls_mock  # type: ignore[attr-defined]
    sys.modules["diffusers"] = diffusers
    utils = types.ModuleType("diffusers.utils")
    utils.export_to_video = MagicMock(return_value=None)  # type: ignore[attr-defined]
    sys.modules["diffusers.utils"] = utils


def _cleanup() -> None:
    for name in ["torch", "torch.backends", "torch.backends.mps", "diffusers", "diffusers.utils"]:
        sys.modules.pop(name, None)


@pytest.fixture
def mps_env() -> object:
    """torch com MPS disponível + pipeline mockado que retorna frames."""
    _inject_torch(mps_available=True)
    pipe = MagicMock()
    pipe.return_value.frames = [[MagicMock(), MagicMock()]]
    _inject_diffusers(pipe)
    try:
        yield pipe
    finally:
        _cleanup()


@pytest.fixture
def cpu_env() -> object:
    """torch sem MPS (fallback CPU) + pipeline mockado."""
    _inject_torch(mps_available=False)
    pipe = MagicMock()
    pipe.return_value.frames = [[MagicMock()]]
    _inject_diffusers(pipe)
    try:
        yield pipe
    finally:
        _cleanup()


class TestDeviceResolution:
    def test_uses_mps_when_available(self, mps_env: object) -> None:
        from src.core.generators.animatediff import AnimateDiffGenerator

        gen = AnimateDiffGenerator()
        assert gen.device == "mps"

    def test_falls_back_to_cpu_without_mps(self, cpu_env: object) -> None:
        from src.core.generators.animatediff import AnimateDiffGenerator

        gen = AnimateDiffGenerator()
        assert gen.device == "cpu"

    def test_force_cpu_overrides_mps(self, mps_env: object) -> None:
        from src.core.generators.animatediff import AnimateDiffGenerator

        gen = AnimateDiffGenerator(force_cpu=True)
        assert gen.device == "cpu"


class TestIsAvailable:
    def test_false_without_torch(self) -> None:
        from src.core.generators.animatediff import AnimateDiffGenerator

        assert AnimateDiffGenerator.is_available_static() is False

    def test_true_with_deps(self, mps_env: object) -> None:
        from src.core.generators.animatediff import AnimateDiffGenerator

        assert AnimateDiffGenerator().is_available() is True


class TestGenerate:
    def test_generate_calls_pipeline_with_prompt(
        self, mps_env: object, tmp_path: Path
    ) -> None:
        import sys

        from src.core.generators.animatediff import AnimateDiffGenerator

        pipe = mps_env
        assert isinstance(pipe, MagicMock)
        # export_to_video mockado cria o arquivo para validar o fluxo
        exporter = sys.modules["diffusers.utils"].export_to_video  # type: ignore[union-attr]
        assert isinstance(exporter, MagicMock)

        def _write(frames: object, path: str, fps: int = 8) -> None:
            Path(path).write_bytes(b"FAKE-MP4")

        exporter.side_effect = _write
        out = tmp_path / "clip.mp4"
        gen = AnimateDiffGenerator()
        result = gen.generate("um gato pixel art", out, duration_seconds=2)
        assert result == out
        assert out.is_file()
        # prompt injetado no pipeline (via from_pretrained → pipe.to(device))
        fp = sys.modules["diffusers"].AnimateDiffPipeline.from_pretrained  # type: ignore[union-attr]
        assert isinstance(fp, MagicMock)
        loaded = fp.return_value
        # .to(device) pode clonar: aceita chamada no original ou no clone
        calls = str(loaded.mock_calls)
        to_clone = loaded.to.return_value if isinstance(loaded.to, MagicMock) else None
        clone_calls = str(to_clone.mock_calls) if isinstance(to_clone, MagicMock) else ""
        assert "um gato pixel art" in calls + clone_calls

    def test_generate_wraps_pipeline_error(self, mps_env: object, tmp_path: Path) -> None:
        import sys

        from src.core.generators.animatediff import AnimateDiffGenerator

        # falha no carregamento (from_pretrained) → GenerationError
        diffusers = sys.modules["diffusers"]
        assert isinstance(diffusers.AnimateDiffPipeline, MagicMock)
        fp = diffusers.AnimateDiffPipeline.from_pretrained  # type: ignore[union-attr]
        assert isinstance(fp, MagicMock)
        fp.side_effect = RuntimeError("CUDA OOM")
        gen = AnimateDiffGenerator()
        with pytest.raises(GenerationError, match="AnimateDiff"):
            gen.generate("prompt", tmp_path / "clip.mp4")

    def test_name_and_vram(self, mps_env: object) -> None:
        from src.core.generators.animatediff import AnimateDiffGenerator

        gen = AnimateDiffGenerator()
        assert gen.name == "animatediff"
        assert gen.min_vram_gb == 4


class TestFactoryIntegration:
    def test_factory_returns_real_when_available(self, mps_env: object) -> None:
        from src.core import factory

        importlib.reload(factory)
        try:
            gen = factory.get_generator("animatediff")
            assert gen.name == "animatediff"
        finally:
            importlib.reload(factory)

    def test_factory_falls_back_without_deps(self) -> None:
        from src.core import factory
        from src.core.fakes import FakeVideoGenerator

        importlib.reload(factory)
        try:
            assert isinstance(factory.get_generator("animatediff"), FakeVideoGenerator)
        finally:
            importlib.reload(factory)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
