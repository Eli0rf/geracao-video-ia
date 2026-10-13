"""
Testes para VideoAssembler (src/core/assembly/ffmpeg.py).

Cobrem:
    - Funções puras de construção de comando (sem FFmpeg instalado).
    - Orquestração de `assemble()` com `subprocess.run` mockado.

Nenhum teste aqui depende do binário FFmpeg. A execução real fica nos
testes de integração (tests/integration/test_ffmpeg_assembly.py), marcados
com skipif.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.assembly.ffmpeg import (
    VideoAssembler,
    build_concat_command,
    build_concat_list,
    build_mux_command,
)
from src.core.errors import AssemblyError, GenerationTimeoutError


def _assembler(**kw: object) -> VideoAssembler:
    return VideoAssembler(**kw)  # type: ignore[arg-type]


class TestBuildConcatList:
    def test_one_line_per_clip_in_order(self, tmp_path: Path) -> None:
        clips = [tmp_path / "a.mp4", tmp_path / "b.mp4", tmp_path / "c.mp4"]
        content = build_concat_list(clips)
        lines = content.splitlines()
        assert len(lines) == 3
        assert lines[0].startswith("file '")
        assert lines[0].endswith("a.mp4'")
        assert lines[1].endswith("b.mp4'")
        assert lines[2].endswith("c.mp4'")

    def test_uses_absolute_paths(self) -> None:
        content = build_concat_list([Path("relative.mp4")])
        assert "file '" in content
        assert str(Path("relative.mp4").resolve()) in content

    def test_single_clip(self, tmp_path: Path) -> None:
        content = build_concat_list([tmp_path / "only.mp4"])
        assert content.count("file '") == 1


class TestBuildConcatCommand:
    def test_contains_concat_demuxer_flags(self, tmp_path: Path) -> None:
        cmd = build_concat_command(tmp_path / "list.txt", tmp_path / "out.mp4", 848, 480)
        assert "-f" in cmd
        assert "concat" in cmd
        assert "-safe" in cmd
        assert "0" in cmd

    def test_contains_scale_and_fps_filter(self, tmp_path: Path) -> None:
        cmd = build_concat_command(tmp_path / "list.txt", tmp_path / "out.mp4", 1280, 720, fps=30)
        vf_index = cmd.index("-vf")
        assert cmd[vf_index + 1] == "scale=1280:720,fps=30"

    def test_discards_audio_and_output_last(self, tmp_path: Path) -> None:
        out = tmp_path / "out.mp4"
        cmd = build_concat_command(tmp_path / "list.txt", out, 848, 480)
        assert "-an" in cmd
        assert cmd[-1] == str(out)
        assert "libx264" in cmd

    def test_no_shell_flag(self, tmp_path: Path) -> None:
        cmd = build_concat_command(tmp_path / "list.txt", tmp_path / "out.mp4", 848, 480)
        assert "-shell" not in cmd

class TestBuildMuxCommand:
    def test_maps_video_and_audio(self, tmp_path: Path) -> None:
        cmd = build_mux_command(tmp_path / "v.mp4", tmp_path / "a.wav", tmp_path / "out.mp4")
        assert "0:v" in cmd
        assert "1:a" in cmd
        assert "aac" in cmd
        assert "-shortest" in cmd

    def test_inputs_and_output(self, tmp_path: Path) -> None:
        video, audio, out = tmp_path / "v.mp4", tmp_path / "a.wav", tmp_path / "out.mp4"
        cmd = build_mux_command(video, audio, out)
        assert str(video) in cmd
        assert str(audio) in cmd
        assert cmd[-1] == str(out)
        assert cmd[0] == "ffmpeg"


class TestIsAvailable:
    def test_available_when_binary_present(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            assert _assembler().is_available() is True

    def test_unavailable_when_binary_missing(self) -> None:
        with patch("shutil.which", return_value=None):
            assert _assembler().is_available() is False


def _fake_run(returncode: int = 0) -> MagicMock:
    return MagicMock(return_value=subprocess.CompletedProcess([], returncode, b"", b""))


class TestAssemble:
    def test_success_returns_out_path_and_runs_two_steps(self, tmp_path: Path) -> None:
        clips = [tmp_path / "c0.mp4", tmp_path / "c1.mp4"]
        for c in clips:
            c.write_bytes(b"x")
        audio = tmp_path / "narracao.wav"
        audio.write_bytes(b"x")
        out = tmp_path / "final.mp4"
        fake_run = _fake_run(0)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", fake_run),
        ):
            result = _assembler().assemble(clips, audio, out, 848, 480)

        assert result == out
        assert fake_run.call_count == 2  # passo 1 (concat) + passo 2 (mux)
        for call in fake_run.call_args_list:
            assert call.kwargs["shell"] is False

    def test_concat_list_written_with_correct_content(self, tmp_path: Path) -> None:
        clips = [tmp_path / "c0.mp4", tmp_path / "c1.mp4"]
        for c in clips:
            c.write_bytes(b"x")
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")

        # Captura o conteúdo da lista durante a 1ª chamada (temp dir ainda existe)
        captured: dict[str, str] = {}

        def _capture(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "concat" in cmd:
                list_path = Path(cmd[cmd.index("-i") + 1])
                captured["content"] = list_path.read_text(encoding="utf-8")
            return subprocess.CompletedProcess([], 0, b"", b"")

        fake_run = MagicMock(side_effect=_capture)
        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", fake_run),
        ):
            _assembler().assemble(clips, audio, tmp_path / "final.mp4", 640, 360)

        assert captured["content"] == build_concat_list(clips)

    def test_first_command_is_concat_second_is_mux(self, tmp_path: Path) -> None:
        clips = [tmp_path / "c0.mp4"]
        clips[0].write_bytes(b"x")
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")
        fake_run = _fake_run(0)

        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", fake_run),
        ):
            _assembler().assemble(clips, audio, tmp_path / "final.mp4", 848, 480)

        first_cmd = fake_run.call_args_list[0].args[0]
        second_cmd = fake_run.call_args_list[1].args[0]
        assert "concat" in first_cmd
        assert "-shortest" in second_cmd

    def test_creates_output_parent_dir(self, tmp_path: Path) -> None:
        clips = [tmp_path / "c0.mp4"]
        clips[0].write_bytes(b"x")
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")
        out = tmp_path / "nested" / "dir" / "final.mp4"
        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", _fake_run(0)),
        ):
            _assembler().assemble(clips, audio, out, 848, 480)
        assert out.parent.exists()

    def test_empty_clips_raises(self, tmp_path: Path) -> None:
        with pytest.raises(AssemblyError, match="Nenhum clipe"):
            _assembler().assemble([], tmp_path / "a.wav", tmp_path / "o.mp4", 848, 480)

    def test_binary_missing_raises(self, tmp_path: Path) -> None:
        clips = [tmp_path / "c0.mp4"]
        clips[0].write_bytes(b"x")
        with patch("shutil.which", return_value=None):
            with pytest.raises(AssemblyError, match="não encontrado"):
                _assembler().assemble(clips, tmp_path / "a.wav", tmp_path / "o.mp4", 848, 480)

    def test_nonzero_return_raises(self, tmp_path: Path) -> None:
        clips = [tmp_path / "c0.mp4"]
        clips[0].write_bytes(b"x")
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")
        fake_run = MagicMock(return_value=subprocess.CompletedProcess([], 1, b"", b"erro ffmpeg"))
        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", fake_run),
        ):
            with pytest.raises(AssemblyError, match="FFmpeg falhou"):
                _assembler().assemble(clips, audio, tmp_path / "o.mp4", 848, 480)

    def test_timeout_raises_timeout_error(self, tmp_path: Path) -> None:
        clips = [tmp_path / "c0.mp4"]
        clips[0].write_bytes(b"x")
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"x")
        fake_run = MagicMock(side_effect=subprocess.TimeoutExpired("ffmpeg", 5))
        with (
            patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("subprocess.run", fake_run),
        ):
            with pytest.raises(GenerationTimeoutError):
                _assembler(timeout=5).assemble(clips, audio, tmp_path / "o.mp4", 848, 480)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

