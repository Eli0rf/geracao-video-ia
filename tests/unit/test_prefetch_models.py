"""
Testes para scripts/prefetch_models.py (E07) — pré-baixa de pesos sem gerar
nenhum vídeo: apenas `from_pretrained()` com torch_dtype apropriado.

torch/diffusers são injetados falsos em sys.modules — nenhum download real.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prefetch_models.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("prefetch_models", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _inject_ai_modules() -> types.ModuleType:
    torch_mod = types.ModuleType("torch")
    torch_mod.float16 = "fake-float16"  # type: ignore[attr-defined]
    sys.modules["torch"] = torch_mod

    diffusers = types.ModuleType("diffusers")
    for name in ("WanPipeline", "AnimateDiffPipeline", "MotionAdapter"):
        cls = MagicMock(name=name)
        cls.from_pretrained = MagicMock(return_value=MagicMock(name=f"{name}_instance"))
        setattr(diffusers, name, cls)
    sys.modules["diffusers"] = diffusers
    return diffusers


def _cleanup() -> None:
    for name in ("torch", "diffusers", "prefetch_models"):
        sys.modules.pop(name, None)


class TestPrefetchAll:
    def test_downloads_wan_and_animatediff_with_dtype(self) -> None:
        _inject_ai_modules()
        mod = _load_module()
        try:
            assert mod.main(["--model", "all"]) == 0
            d = sys.modules["diffusers"]

            d.WanPipeline.from_pretrained.assert_called_once()  # type: ignore[attr-defined]
            wan_args, wan_kwargs = d.WanPipeline.from_pretrained.call_args  # type: ignore[attr-defined]
            assert "Wan2.1" in wan_args[0]
            assert wan_kwargs["torch_dtype"] == "fake-float16"

            d.MotionAdapter.from_pretrained.assert_called_once()  # type: ignore[attr-defined]
            ad_args, ad_kwargs = d.AnimateDiffPipeline.from_pretrained.call_args  # type: ignore[attr-defined]
            assert "stable-diffusion" in ad_args[0]
            assert ad_kwargs["motion_adapter"] is not None
            assert ad_kwargs["torch_dtype"] == "fake-float16"
        finally:
            _cleanup()


class TestPrefetchSelective:
    def test_wan_only_skips_animatediff(self) -> None:
        _inject_ai_modules()
        mod = _load_module()
        try:
            assert mod.main(["--model", "wan"]) == 0
            d = sys.modules["diffusers"]
            d.WanPipeline.from_pretrained.assert_called_once()  # type: ignore[attr-defined]
            d.AnimateDiffPipeline.from_pretrained.assert_not_called()  # type: ignore[attr-defined]
        finally:
            _cleanup()

    def test_animatediff_only_skips_wan(self) -> None:
        _inject_ai_modules()
        mod = _load_module()
        try:
            assert mod.main(["--model", "animatediff"]) == 0
            d = sys.modules["diffusers"]
            d.WanPipeline.from_pretrained.assert_not_called()  # type: ignore[attr-defined]
            d.AnimateDiffPipeline.from_pretrained.assert_called_once()  # type: ignore[attr-defined]
        finally:
            _cleanup()


class TestPrefetchErrors:
    def test_missing_ai_extra_returns_1(self) -> None:
        sys.modules["diffusers"] = None  # força ImportError determinístico
        mod = _load_module()
        try:
            assert mod.main(["--model", "wan"]) == 1
        finally:
            sys.modules.pop("diffusers", None)

    def test_load_failure_returns_1(self) -> None:
        d = _inject_ai_modules()
        d.WanPipeline.from_pretrained.side_effect = RuntimeError("repo inexistente")  # type: ignore[attr-defined]
        mod = _load_module()
        try:
            assert mod.main(["--model", "wan"]) == 1
        finally:
            _cleanup()
