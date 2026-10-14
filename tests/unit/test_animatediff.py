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
    """Injeta diffusers falso com AnimateDiffPipeline, MotionAdapter e export."""
    diffusers = types.ModuleType("diffusers")
    cls_mock = MagicMock()
    cls_mock.from_pretrained = MagicMock(return_value=pipeline_mock)
    diffusers.AnimateDiffPipeline = cls_mock  # type: ignore[attr-defined]
    motion_cls = MagicMock()
    motion_cls.from_pretrained = MagicMock(return_value=MagicMock(name="motion_adapter"))
    diffusers.MotionAdapter = motion_cls  # type: ignore[attr-defined]
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
        from src.core.devices import resolve_device

        assert resolve_device() == "mps"

    def test_falls_back_to_cpu_without_mps(self, cpu_env: object) -> None:
        from src.core.devices import resolve_device

        assert resolve_device() == "cpu"

    def test_force_cpu_overrides_mps(self, mps_env: object) -> None:
        from src.core.devices import resolve_device
        from src.core.generators.animatediff import AnimateDiffGenerator

        assert resolve_device(force_cpu=True) == "cpu"
        assert AnimateDiffGenerator(force_cpu=True).device == "cpu"

    def test_generator_resolves_mps(self, mps_env: object) -> None:
        from src.core.generators.animatediff import AnimateDiffGenerator

        assert AnimateDiffGenerator().device == "mps"

    def test_torch_missing_means_no_mps(self) -> None:
        import sys

        from src.core.devices import _torch_has_mps

        mods = ("torch", "torch.backends", "torch.backends.mps")
        saved = {k: sys.modules.pop(k, None) for k in mods}
        try:
            assert _torch_has_mps() is False
        finally:
            for k, v in saved.items():
                if v is not None:
                    sys.modules[k] = v


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


class TestLoadPipeline:
    def test_downloads_motion_adapter_then_base_sd(self, mps_env: object) -> None:
        """Carrega MotionAdapter (adapter) + base SD como pipeline (E07 fix)."""
        from src.core.generators.animatediff import AnimateDiffGenerator

        gen = AnimateDiffGenerator()
        pipe = gen._load_pipeline()
        # `.to(device)` devolve o clone do mock — assinar nele.
        assert pipe is mps_env.to.return_value

        d = sys.modules["diffusers"]
        d.MotionAdapter.from_pretrained.assert_called_once()  # type: ignore[attr-defined]
        adapter_repo = d.MotionAdapter.from_pretrained.call_args[0][0]  # type: ignore[attr-defined]
        assert adapter_repo == "guoyww/animatediff-motion-adapter-v1-5-2"

        args, kwargs = d.AnimateDiffPipeline.from_pretrained.call_args  # type: ignore[attr-defined]
        assert "stable-diffusion" in args[0]
        assert kwargs["motion_adapter"] is not None


class TestFailureCapture:
    def test_oom_logs_stack_trace_and_raises(
        self, mps_env: object, tmp_path: Path, monkeypatch
    ) -> None:
        from src.core.generators import animatediff as mod

        fake_logger = MagicMock()
        monkeypatch.setattr(mod, "logger", fake_logger)
        gen = mod.AnimateDiffGenerator()
        gen._pipe = MagicMock(side_effect=RuntimeError("MPS backend out of memory"))

        with pytest.raises(GenerationError, match="out of memory"):
            gen.generate("p", tmp_path / "c.mp4")

        assert fake_logger.error.called
        args, kwargs = fake_logger.error.call_args
        assert args[0] == "animatediff_out_of_memory"
        assert kwargs.get("exc_info") is True

    def test_inference_failure_logs_stack_trace(
        self, mps_env: object, tmp_path: Path, monkeypatch
    ) -> None:
        from src.core.generators import animatediff as mod

        fake_logger = MagicMock()
        monkeypatch.setattr(mod, "logger", fake_logger)
        gen = mod.AnimateDiffGenerator()
        gen._pipe = MagicMock(side_effect=RuntimeError("disco cheio"))

        with pytest.raises(GenerationError, match="falhou na infer"):
            gen.generate("p", tmp_path / "c.mp4")

        assert fake_logger.error.called
        args, kwargs = fake_logger.error.call_args
        assert args[0] == "animatediff_inference_failed"
        assert kwargs.get("exc_info") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
