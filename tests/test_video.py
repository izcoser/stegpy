import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from stegpy import steg, video


def require_video_support():
    if not video.ffmpeg_available():
        pytest.skip("ffmpeg and ffprobe are required for video tests")


def synthetic_frames(size=(240, 160), count=18):
    width, height = size
    rng = np.random.default_rng(42)
    frames = []

    for index in range(count):
        x = np.linspace(0, 255, width, dtype=np.float32)[None, :]
        y = np.linspace(0, 255, height, dtype=np.float32)[:, None]
        frame = np.empty((height, width, 3), dtype=np.float32)
        frame[:, :, 0] = (x + index * 5) % 256
        frame[:, :, 1] = (y + index * 3) % 256
        frame[:, :, 2] = ((x + y) / 2 + index * 7) % 256
        frame += rng.normal(0, 8, frame.shape)
        frames.append(np.clip(frame, 0, 255).astype(np.uint8))

    return frames


def create_video_host(path, size=(240, 160), count=18):
    require_video_support()
    frames = synthetic_frames(size=size, count=count)
    width, height = size
    completed = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            "12",
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        input=b"".join(frame.tobytes() for frame in frames),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(completed.stderr.decode("utf-8", "replace"))


def test_video_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_video_host("host.mp4")

    output_path = video.insert_message("host.mp4", b"video payload")
    save_output = capsys.readouterr().out

    assert output_path == Path("_host.mp4")
    assert Path("_host.mp4").exists()
    assert "Information encoded in _host.mp4." in save_output

    video.read_message("_host.mp4")
    read_output = capsys.readouterr().out

    assert "video payload" in read_output


def test_video_free_space_reports_robust_payload_capacity(tmp_path):
    create_video_host(tmp_path / "host.mp4")

    capacity = video.video_free_space(tmp_path / "host.mp4")

    assert capacity == (30 * 20 * 18) // video.DEFAULT_REPETITION // 8


def test_video_encrypted_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_video_host("host.mp4")

    video.insert_message("host.mp4", b"secret", password="hunter2")
    capsys.readouterr()

    video.read_message("_host.mp4", password="hunter2")
    read_output = capsys.readouterr().out

    assert "secret" in read_output


def test_video_payload_survives_an_extra_h264_compression_pass(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    create_video_host("host.mp4")
    video.insert_message("host.mp4", b"second pass")
    capsys.readouterr()

    completed = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            "_host.mp4",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-an",
            "recompressed.mp4",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(completed.stderr.decode("utf-8", "replace"))

    video.read_message("recompressed.mp4")
    read_output = capsys.readouterr().out

    assert "second pass" in read_output


def test_cli_video_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_video_host("host.mp4")

    monkeypatch.setattr(sys, "argv", ["stegpy", "hello from video cli", "host.mp4"])
    steg.main()
    save_output = capsys.readouterr().out

    assert Path("_host.mp4").exists()
    assert "Information encoded in _host.mp4." in save_output

    monkeypatch.setattr(sys, "argv", ["stegpy", "_host.mp4"])
    steg.main()
    decode_output = capsys.readouterr().out

    assert "hello from video cli" in decode_output
