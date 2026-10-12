"""
src/core/factory.py — Resolução de implementações concretas dos contratos.

Ponto único que traduz um nome de modelo/configuração em uma instância
concreta (`VideoGenerator`, `ScriptGenerator`, `AudioSynthesizer`),
aplicando fallback automático quando a implementação preferida não está
disponível (vide ADR-003 e ADR-006).

Nenhum endpoint ou worker precisa conhecer as classes concretas — todos
 consomem via estas funções ou por injeção de dependência.
"""

import structlog

from src.core.errors import ModelUnavailableError
from src.core.fakes import (
    FakeAudioSynthesizer,
    FakeScriptGenerator,
    FakeVideoGenerator,
)
from src.core.interfaces import AudioSynthesizer, ScriptGenerator, VideoGenerator

logger = structlog.get_logger(__name__)


def _try_animatediff() -> VideoGenerator:
    """
    Tenta instanciar o AnimateDiff (fallback leve, ADR-003).

    Implementações reais de vídeo (AnimateDiff/Wan2.1) chegam nas tasks
    TASK-011/012; quando ausentes, cai para o fake.

    Raises:
        ModelUnavailableError: Se o modelo não pode ser carregado.
    """
    from src.core.generators.animatediff import AnimateDiffGenerator

    generator: VideoGenerator = AnimateDiffGenerator()
    if not generator.is_available():
        raise ModelUnavailableError("AnimateDiff indisponível (deps/VRAM).")
    return generator


def get_generator(model_name: str) -> VideoGenerator:
    """
    Retorna um `VideoGenerator` para o modelo pedido, com fallback.

    Estratégia:
      1. Tenta o modelo pedido (wan2.1, cogvideox, hunyuan, animatediff).
      2. Se indisponível, cai para AnimateDiff (fallback, ADR-003).
      3. Como último recurso, usa `FakeVideoGenerator` (nunca falha).

    Args:
        model_name: Nome do modelo (validado pelo endpoint).

    Returns:
        Instância de `VideoGenerator` utilizável.

    Raises:
        ModelUnavailableError: Se nem o fallback fake estiver disponível
            (não deve ocorrer em condições normais).
    """
    if model_name == "fake":
        return get_fake_generator()

    try:
        return _try_animatediff()
    except (ImportError, ModuleNotFoundError, ModelUnavailableError) as exc:
        logger.warning("video_generator_unavailable", model=model_name, reason=str(exc))

    logger.warning("video_generator_fallback_fake", requested=model_name)
    return get_fake_generator()


def get_fake_generator() -> VideoGenerator:
    """Atalho para o gerador falso (testes e fallback final)."""
    generator: VideoGenerator = FakeVideoGenerator()
    return generator


def get_script_generator() -> ScriptGenerator:
    """
    Retorna o `ScriptGenerator` real (Ollama) se disponível, senão o fake.

    Fallback automático garante que o pipeline nunca quebra por indispo-
    nibilidade do Ollama (ADR-006).
    """
    try:
        from src.core.generators.ollama import OllamaScriptGenerator

        ollama: ScriptGenerator = OllamaScriptGenerator()
        if ollama.is_available():
            return ollama
    except Exception as exc:  # captura ampla: qualquer falha de build cai no fake
        logger.warning("script_generator_build_failed", reason=str(exc))

    logger.warning("script_generator_fallback_fake")
    return FakeScriptGenerator()


def get_audio_synthesizer() -> AudioSynthesizer:
    """
    Retorna o `AudioSynthesizer` real (Piper) se disponível, senão o fake.

    Fallback automático garante que o pipeline nunca quebra por falta do
    binário Piper ou do modelo de voz (ADR-006).
    """
    try:
        from src.core.generators.piper import PiperAudioSynthesizer

        piper: AudioSynthesizer = PiperAudioSynthesizer()
        if piper.is_available():
            return piper
    except Exception as exc:  # captura ampla: qualquer falha de build cai no fake
        logger.warning("audio_synth_build_failed", reason=str(exc))

    logger.warning("audio_synth_fallback_fake")
    return FakeAudioSynthesizer()

