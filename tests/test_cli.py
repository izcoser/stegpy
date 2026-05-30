import sys
from pathlib import Path

import numpy as np
from PIL import Image

from stegpy import steg


def create_rgb_host(path, size=(32, 32)):
    pixels = np.arange(size[0] * size[1] * 3, dtype=np.uint8).reshape(
        size[1], size[0], 3
    )
    Image.fromarray(pixels).save(path)


def create_jpeg_host(path, size=(128, 128)):
    y = np.arange(size[1], dtype=np.uint16).reshape(size[1], 1)
    x = np.arange(size[0], dtype=np.uint16).reshape(1, size[0])
    pixels = np.empty((size[1], size[0], 3), dtype=np.uint8)
    pixels[:, :, 0] = ((x * 7) + (y * 13)) % 256
    pixels[:, :, 1] = ((x * 11) ^ (y * 5)) % 256
    pixels[:, :, 2] = ((x * 3) + (y * 17) + ((x * y) % 31)) % 256
    Image.fromarray(pixels).save(path, quality=95, subsampling=0)


def test_cli_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png")

    monkeypatch.setattr(sys, "argv", ["stegpy", "hello from cli", "host.png"])
    steg.main()
    save_output = capsys.readouterr().out

    assert Path("_host.png").exists()
    assert "Information encoded in _host.png." in save_output

    monkeypatch.setattr(sys, "argv", ["stegpy", "_host.png"])
    steg.main()
    decode_output = capsys.readouterr().out

    assert "hello from cli" in decode_output


def test_cli_jpeg_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_jpeg_host("host.jpg")

    monkeypatch.setattr(sys, "argv", ["stegpy", "hello from jpeg cli", "host.jpg"])
    steg.main()
    save_output = capsys.readouterr().out

    assert Path("_host.jpg").exists()
    assert "Information encoded in _host.jpg." in save_output

    monkeypatch.setattr(sys, "argv", ["stegpy", "_host.jpg"])
    steg.main()
    decode_output = capsys.readouterr().out

    assert "hello from jpeg cli" in decode_output


def test_cli_check_reports_capacity(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png")

    monkeypatch.setattr(sys, "argv", ["stegpy", "host.png", "-c"])
    steg.main()
    output = capsys.readouterr().out

    assert "File: host.png, free: (bytes)" in output
    assert "encoding: 4 bit" in output
