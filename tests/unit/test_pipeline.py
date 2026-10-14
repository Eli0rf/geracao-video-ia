"""
Testes para VideoPipeline (src/core/pipeline.py).

Usam fakes para todos os estágios — sem I/O real (Ollama/Piper/FFmpeg).
Verificam a ordem Script→Audio→Clipes→Assembly, a limpeza dos temporários
(sucesso e erro) e o helper puro concat_wav_files.
"""

import tempfile
import wave
from pathlib import Path

import pytest

from src.core.errors import GenerationError
from src.core.fakes import FakeAudioSynthesizer
from src.core.interfaces import Scene, Script
from src.core.pipeline import VideoPipeline, concat_wav_files
from src.models.video_job import VideoJob


class RecordingScriptGenerator:
    """Fake que registra a ordem das chamadas e devolve um roteiro conhecido."""

    def __init__(self, scenes: int = 2) -> None:
        self.calls: list[str] = []
        self._scenes = tuple(
            Scene(narration=f"narra {i}", visual_prompt=f"visual {i}") for i in range(scenes)
        )

    def generate_script(self, prompt: str) -> Script:
        self.calls.append("script")
        return Script(scenes=self._scenes, source_prompt=prompt)

    def is_available(self) -> bool:
        return True


class RecordingAudio:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def synthesize(self, text: str, out_path: Path) -> Path:
        self.calls.append(f"audio:{text}")
        # Gera um WAV válido para que concat_wav_files funcione.
        FakeAudioSynthesizer().synthesize(text, out_path)
        return out_path

    def is_available(self) -> bool:
        return True


class RecordingVideo:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str, out_path: Path, **kwargs: object) -> Path:
        self.calls.append(f"video:{prompt}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"clip")
        return out_path

    def is_available(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "rec"

    @property
    def min_vram_gb(self) -> int:
        return 0


class RecordingAssembler:
    def __init__(self) -> None:
        self.calls: list[tuple[int, Path]] = []

    def assemble(
        self, clips: list[Path], audio: Path, out_path: Path, width: int, height: int
    ) -> Path:
        self.calls.append((len(clips), out_path))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"mp4")
        return out_path


def _make_pipeline(tmp_path: Path, script: RecordingScriptGenerator, assembler: RecordingAssembler):
    audio = RecordingAudio()
    video = RecordingVideo()
    pipeline = VideoPipeline(
        script_generator=script,
        audio_synthesizer=audio,
        video_generator=video,
        assembler=assembler,
        output_dir=tmp_path / "outputs",
    )
    return pipeline, audio, video


class TestPipelineOrder:
    def test_runs_script_then_audio_then_clips_then_assembly(self, tmp_path: Path) -> None:
        script = RecordingScriptGenerator(scenes=2)
        assembler = RecordingAssembler()
        pipeline, audio, video = _make_pipeline(tmp_path, script, assembler)
        job = VideoJob(prompt="um gato", width=848, height=480)

        out = pipeline.run(job)

        # Ordem lógica dos estágios
        assert script.calls == ["script"]
        assert audio.calls == ["audio:narra 0", "audio:narra 1"]
        assert video.calls == ["video:visual 0", "video:visual 1"]
        # Assembly recebeu 2 clipes e gravou em outputs/{id}.mp4
        assert assembler.calls == [(2, tmp_path / "outputs" / f"{job.id}.mp4")]
        assert out == tmp_path / "outputs" / f"{job.id}.mp4"
        assert out.exists()


class TestPipelineCleanup:
    def test_temp_files_removed_on_success(self, tmp_path: Path) -> None:
        script = RecordingScriptGenerator(scenes=2)
        assembler = RecordingAssembler()
        pipeline, _, _ = _make_pipeline(tmp_path, script, assembler)

        pipeline.run(VideoJob(prompt="x"))

        # Nenhum diretório de trabalho temporário deve restar no temp dir.
        leftovers = list(Path(tempfile.gettempdir()).glob("gvpipeline_*"))
        assert leftovers == []

    def test_error_propagates_and_temp_removed(self, tmp_path: Path) -> None:
        class BoomVideo(RecordingVideo):
            def generate(self, prompt: str, out_path: Path, **kwargs: object) -> Path:
                raise GenerationError("falhou no clipe")

        script = RecordingScriptGenerator(scenes=2)
        audio = RecordingAudio()
        video = BoomVideo()
        assembler = RecordingAssembler()
        pipeline = VideoPipeline(
            script_generator=script,
            audio_synthesizer=audio,
            video_generator=video,
            assembler=assembler,
            output_dir=tmp_path / "outputs",
        )

        with pytest.raises(GenerationError, match="falhou no clipe"):
            pipeline.run(VideoJob(prompt="x"))

        assert list(Path(tempfile.gettempdir()).glob("gvpipeline_*")) == []
        # Assembly não deve ter sido chamado
        assert assembler.calls == []

    def test_error_in_script_propagates(self, tmp_path: Path) -> None:
        class BoomScript(RecordingScriptGenerator):
            def generate_script(self, prompt: str) -> Script:
                raise GenerationError("roteiro falhou")

        script = BoomScript()
        assembler = RecordingAssembler()
        pipeline, _, _ = _make_pipeline(tmp_path, script, assembler)

        with pytest.raises(GenerationError, match="roteiro falhou"):
            pipeline.run(VideoJob(prompt="x"))
        assert list(Path(tempfile.gettempdir()).glob("gvpipeline_*")) == []


def _write_wav(path: Path, seconds: float, rate: int = 22050) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return path


class TestConcatWavFiles:
    def test_concatenates_in_order(self, tmp_path: Path) -> None:
        a = _write_wav(tmp_path / "a.wav", 1)
        b = _write_wav(tmp_path / "b.wav", 2)
        out = tmp_path / "out.wav"

        concat_wav_files([a, b], out)

        with wave.open(str(out), "rb") as w:
            expected = int(22050 * 1) + int(22050 * 2)
            assert w.getnframes() == expected
            assert w.getframerate() == 22050

    def test_single_source(self, tmp_path: Path) -> None:
        a = _write_wav(tmp_path / "a.wav", 1)
        out = tmp_path / "out.wav"
        concat_wav_files([a], out)
        assert out.exists()

    def test_empty_sources_raises(self, tmp_path: Path) -> None:
        with pytest.raises(GenerationError, match="Nenhum áudio"):
            concat_wav_files([], tmp_path / "out.wav")

    def test_incompatible_format_raises(self, tmp_path: Path) -> None:
        a = _write_wav(tmp_path / "a.wav", 1, rate=22050)
        b = _write_wav(tmp_path / "b.wav", 1, rate=44100)
        with pytest.raises(GenerationError, match="incompatível"):
            concat_wav_files([a, b], tmp_path / "out.wav")


class TestStageDurations:
    def test_logs_each_stage_with_duration_ms(self, tmp_path: Path, monkeypatch) -> None:
        """Cada estágio crítico emite `pipeline_stage` com stage + duration_ms."""
        from src.core import pipeline as pipeline_mod

        records: list[tuple[str, dict]] = []

        class _Rec:
            def info(self, event: str, **kwargs: object) -> None:
                records.append((event, dict(kwargs)))  # type: ignore[arg-type]

            def warning(self, event: str, **kwargs: object) -> None:
                records.append((event, dict(kwargs)))  # type: ignore[arg-type]

        monkeypatch.setattr(pipeline_mod, "logger", _Rec())

        script = RecordingScriptGenerator(scenes=2)
        assembler = RecordingAssembler()
        pipeline, _, _ = _make_pipeline(tmp_path, script, assembler)
        job = VideoJob(prompt="um gato")
        pipeline.run(job)

        stages = [kw["stage"] for ev, kw in records if ev == "pipeline_stage"]
        assert stages == ["script", "audio", "video", "assembly"]
        for event, kw in records:
            if event == "pipeline_stage":
                assert isinstance(kw["duration_ms"], int | float)
                assert kw["duration_ms"] >= 0
                assert kw["job_id"] == job.id

        completed = next(kw for ev, kw in records if ev == "pipeline_completed")
        assert isinstance(completed["duration_ms"], int | float)
        assert completed["job_id"] == job.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
