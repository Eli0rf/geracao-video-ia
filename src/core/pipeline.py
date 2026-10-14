"""
src/core/pipeline.py — Orquestrador do motor de geração (TASK-019).

Executa o fluxo completo na ordem:

    Script → Audio → Clipes → Assembly

Todas as dependências (`ScriptGenerator`, `AudioSynthesizer`,
`VideoGenerator`, `Assembler`) entram por injeção, permitindo testar o
pipeline inteiro com fakes — sem I/O real (Ollama/Piper/FFmpeg).

Os arquivos intermediários (áudios e clipes por cena) ficam em um diretório
temporário removido em `finally`, mesmo em caso de erro.
"""

import shutil
import tempfile
import time
import wave
from pathlib import Path

import structlog

from src.core.interfaces import (
    Assembler,
    AudioSynthesizer,
    ScriptGenerator,
    VideoGenerator,
)
from src.models.video_job import VideoJob

logger = structlog.get_logger(__name__)


def concat_wav_files(sources: list[Path], out_path: Path) -> Path:
    """
    Concatena arquivos WAV PCM (mesmo formato) em um único WAV.

    Usa apenas a stdlib (`wave`) — sem FFmpeg, testável com os fakes. Assume
    que todas as fontes compartilham canais, sample rate e largura de amostra
    (válido para as narrações geradas por um único sintetizador Piper).

    Args:
        sources: Caminhos dos WAVs, na ordem desejada.
        out_path: Caminho do WAV combinado de saída.

    Returns:
        O próprio `out_path`.

    Raises:
        GenerationError: `sources` vazio ou parâmetros de áudio incompatíveis.
    """
    from src.core.errors import GenerationError

    if not sources:
        raise GenerationError("Nenhum áudio fornecido para concatenação.")

    params: tuple[int, int, int, str] | None = None
    frames = bytearray()
    for src in sources:
        with wave.open(str(src), "rb") as w:
            current = (
                w.getnchannels(),
                w.getsampwidth(),
                w.getframerate(),
                w.getcomptype(),
            )
            if params is None:
                params = current
            elif current != params:
                raise GenerationError(
                    f"Áudio incompatível para concatenação: {src} ({current} != {params})."
                )
            frames.extend(w.readframes(w.getnframes()))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    assert params is not None  # sources não-vazio garantido acima
    nchannels, sampwidth, framerate, _ = params
    with wave.open(str(out_path), "wb") as out:
        out.setnchannels(nchannels)
        out.setsampwidth(sampwidth)
        out.setframerate(framerate)
        out.writeframes(bytes(frames))
    return out_path


class VideoPipeline:
    """
    Orquestra a geração de um vídeo a partir de um `VideoJob`.

    Args:
        script_generator: Gera o roteiro (ADR-006).
        audio_synthesizer: Sintetiza a narração de cada cena (ADR-006).
        video_generator: Gera o clipe de vídeo de cada cena (ADR-003).
        assembler: Monta o MP4 final (ADR-007).
        output_dir: Diretório destino dos vídeos finais.
    """

    def __init__(
        self,
        script_generator: ScriptGenerator,
        audio_synthesizer: AudioSynthesizer,
        video_generator: VideoGenerator,
        assembler: Assembler,
        output_dir: str | Path,
    ) -> None:
        self._script = script_generator
        self._audio = audio_synthesizer
        self._video = video_generator
        self._assembler = assembler
        self._output_dir = Path(output_dir)

    def run(self, job: VideoJob) -> Path:
        """
        Executa o pipeline completo para `job` e retorna o caminho do MP4.

        Raises:
            GenerationError: Falha em qualquer estágio (propagada).
        """
        out_path = self._output_dir / f"{job.id}.mp4"
        n_scenes = 0
        run_start = time.perf_counter()
        work = Path(tempfile.mkdtemp(prefix=f"gvpipeline_{job.id}_"))
        try:
            # ── Script: roteiro ───────────────────────────────────────────
            stage_start = time.perf_counter()
            script = self._script.generate_script(job.prompt)
            n_scenes = len(script.scenes)
            self._log_stage(job.id, "script", stage_start)

            # ── Audio: narração de cada cena + trilha combinada ──────────
            stage_start = time.perf_counter()
            audio_parts: list[Path] = []
            for i, scene in enumerate(script.scenes):
                part = work / f"audio_{i}.wav"
                self._audio.synthesize(scene.narration, part)
                audio_parts.append(part)
            narration = concat_wav_files(audio_parts, work / "narration.wav")
            self._log_stage(job.id, "audio", stage_start)

            # ── Clipes: vídeo de cada cena ──────────────────────────────
            stage_start = time.perf_counter()
            clips: list[Path] = []
            for i, scene in enumerate(script.scenes):
                clip = work / f"clip_{i}.mp4"
                self._video.generate(
                    scene.visual_prompt,
                    clip,
                    duration_seconds=job.duration_seconds,
                    width=job.width,
                    height=job.height,
                )
                clips.append(clip)
            self._log_stage(job.id, "video", stage_start)

            # ── Assembly: MP4 final ─────────────────────────────────────
            stage_start = time.perf_counter()
            result = self._assembler.assemble(
                clips, narration, out_path, job.width, job.height
            )
            self._log_stage(job.id, "assembly", stage_start)
        finally:
            # Limpeza garantida dos arquivos temporários, mesmo em erro.
            shutil.rmtree(work, ignore_errors=True)
            logger.info("pipeline_stage_done", job_id=job.id, scenes=n_scenes)

        duration_ms = round((time.perf_counter() - run_start) * 1000, 2)
        logger.info(
            "pipeline_completed",
            job_id=job.id,
            out=str(result),
            duration_ms=duration_ms,
        )
        return result

    @staticmethod
    def _log_stage(job_id: str, stage: str, started: float) -> None:
        """Registra a duração de um estágio crítico (E07 — métricas)."""
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "pipeline_stage",
            job_id=job_id,
            stage=stage,
            duration_ms=duration_ms,
        )
