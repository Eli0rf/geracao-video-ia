"""
src/core/interfaces.py — Contratos (Protocols) e tipos do motor de geração.

Define as interfaces que desacoplam o pipeline (orquestração) das
implementações concretas de IA:

    ScriptGenerator   → texto → roteiro estruturado (ADR-006)
    AudioSynthesizer  → texto → arquivo de áudio (ADR-006)
    VideoGenerator    → texto → clipe de vídeo (ADR-003)

Todas as implementações (reais ou fakes) devem satisfazer estes Protocols.
O módulo não importa nada de `src/` exceto tipos padrão — inversão de
dependência pura (vide ADR-003 e ADR-006).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

# ── Tipos de domínio do roteiro ───────────────────────────────────────────────


@dataclass(frozen=True)
class Scene:
    """
    Uma cena do roteiro.

    Representa uma unidade de vídeo: a narração falada (que vira áudio) e o
    prompt visual enviado ao gerador de vídeo.

    Attributes:
        narration: Texto que será sintetizado em áudio (TTS).
        visual_prompt: Prompt descritivo enviado ao VideoGenerator.
    """

    narration: str
    visual_prompt: str


@dataclass(frozen=True)
class Script:
    """
    Roteiro completo gerado a partir do prompt do usuário.

    Attributes:
        scenes: Lista ordenada de cenas (mínimo 1).
        source_prompt: Prompt original do usuário (rastreabilidade).
    """

    scenes: tuple[Scene, ...]
    source_prompt: str

    def __post_init__(self) -> None:
        """Valida que o roteiro tem ao menos uma cena."""
        if not self.scenes:
            raise ValueError("Script deve conter ao menos uma cena.")


# ── Interfaces (Protocols) ─────────────────────────────────────────────────────


@runtime_checkable
class ScriptGenerator(Protocol):
    """
    Gerador de roteiro: transforma um prompt de texto em um `Script`
    estruturado (lista de cenas com narração e prompt visual).

    Implementações: `OllamaScriptGenerator` (real), `FakeScriptGenerator`
    (testes/fallback). Vide ADR-006.
    """

    def generate_script(self, prompt: str) -> Script:
        """
        Gera um roteiro a partir do prompt.

        Args:
            prompt: Prompt de texto do usuário.

        Returns:
            Script com ao menos uma cena.

        Raises:
            GenerationError: Falha ao gerar/interpretar o roteiro.
        """
        ...

    def is_available(self) -> bool:
        """True se o serviço de roteiro está acessível."""
        ...


@runtime_checkable
class AudioSynthesizer(Protocol):
    """
    Sintetizador de áudio (TTS): transforma texto em um arquivo `.wav`.

    Implementações: `PiperAudioSynthesizer` (real), `FakeAudioSynthesizer`
    (testes/fallback). Vide ADR-006.
    """

    def synthesize(self, text: str, out_path: Path) -> Path:
        """
        Sintetiza `text` e salva em `out_path` (formato WAV).

        Args:
            text: Texto a ser sintetizado (narração da cena).
            out_path: Caminho destino do arquivo `.wav`.

        Returns:
            O próprio `out_path` (para encadeamento).

        Raises:
            GenerationError: Falha na síntese de áudio.
        """
        ...

    def is_available(self) -> bool:
        """True se o serviço de TTS está acessível (binário + voz)."""
        ...


@runtime_checkable
class Assembler(Protocol):
    """
    Montador do vídeo final: junta os clipes e mixa o áudio da narração.

    Implementações: `VideoAssembler` (real, FFmpeg — ADR-007) e um fake nos
    testes. Desacopla o `VideoPipeline` da ferramenta concreta de montagem.
    """

    def assemble(
        self,
        clips: list[Path],
        audio: Path,
        out_path: Path,
        width: int,
        height: int,
    ) -> Path:
        """
        Concatena `clips`, normaliza para `width`x`height` e mixa `audio`.

        Returns:
            O caminho do MP4 final (`out_path`).

        Raises:
            GenerationError: Falha na montagem.
        """
        ...


@runtime_checkable
class VideoGenerator(Protocol):
    """
    Gerador de vídeo (text-to-video): transforma um prompt em um clipe MP4.

    Implementações reais (`AnimateDiffGenerator`, `Wan21Generator`) dependem
    do extra `ai` e são implementadas em tasks futuras; `FakeVideoGenerator`
    serve para testes e fallback. Vide ADR-003.
    """

    def generate(self, prompt: str, out_path: Path, **kwargs: object) -> Path:
        """
        Gera um clipe de vídeo a partir do prompt e salva em `out_path`.

        Args:
            prompt: Prompt visual (da cena).
            out_path: Caminho destino do clipe `.mp4`.
            **kwargs: Parâmetros extras (duration_seconds, width, height, ...).

        Returns:
            O caminho do clipe gerado.

        Raises:
            GenerationError: Falha na geração do vídeo.
        """
        ...

    def is_available(self) -> bool:
        """True se o modelo pode ser carregado (VRAM/deps disponíveis)."""
        ...

    @property
    def name(self) -> str:
        """Identificador do modelo (ex: 'wan2.1', 'animatediff')."""
        ...

    @property
    def min_vram_gb(self) -> int:
        """VRAM mínima recomendada em GB para o modelo."""
        ...
