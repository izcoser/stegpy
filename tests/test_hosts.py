from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from stegpy import lsb
from stegpy.lsb import HostElement


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


def create_gif_host(path):
    first_pixels = np.zeros((24, 24, 3), dtype=np.uint8)
    first_pixels[:, :, 0] = 255
    second_pixels = np.zeros((24, 24, 3), dtype=np.uint8)
    second_pixels[:, :, 1] = 255

    first = Image.fromarray(first_pixels, mode="RGB")
    second = Image.fromarray(second_pixels, mode="RGB")
    first.save(
        path,
        save_all=True,
        append_images=[second],
        duration=[80, 120],
        loop=0,
        optimize=False,
    )


def create_wav_host(path, size=12000):
    Path(path).write_bytes(b"RIFF" + b"\x00" * (size - 4))


def assert_lsb_capacity_boundary(filename, bits):
    host = HostElement(filename)
    capacity = host.free_space(bits)

    lsb.encode_message(host.data.copy(), b"x" * capacity, bits)

    with pytest.raises(SystemExit):
        lsb.encode_message(host.data.copy(), b"x" * (capacity + 1), bits)


@pytest.mark.parametrize("bits", [1, 2, 4])
def test_lsb_free_space_matches_encoding_boundary(tmp_path, monkeypatch, bits):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png", size=(41, 37))
    create_gif_host("host.gif")
    create_wav_host("host.wav", size=22345)

    for filename in ["host.png", "host.gif", "host.wav"]:
        assert_lsb_capacity_boundary(filename, bits)


@pytest.mark.parametrize("bits", [1, 2, 4])
def test_jpeg_free_space_matches_encoding_boundary(tmp_path, monkeypatch, bits):
    monkeypatch.chdir(tmp_path)
    create_jpeg_host("host.jpg")
    capacity = HostElement("host.jpg").free_space(bits)

    lsb.encode_jpeg_message(HostElement("host.jpg").data, b"x" * capacity, bits)

    with pytest.raises(SystemExit):
        lsb.encode_jpeg_message(
            HostElement("host.jpg").data, b"x" * (capacity + 1), bits
        )


def test_png_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png")

    host = HostElement("host.png")
    host.insert_message(b"hello world", bits=2)
    host.save()
    save_output = capsys.readouterr().out

    assert Path("_host.png").exists()
    assert "Information encoded in _host.png." in save_output

    extracted = HostElement("_host.png")
    extracted.read_message()
    read_output = capsys.readouterr().out

    assert "hello world" in read_output


def test_png_file_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png")
    payload = b"\x00\x01\x02secret file payload"
    Path("secret.bin").write_bytes(payload)

    host = HostElement("host.png")
    host.insert_message(payload, bits=1, parasite_filename="secret.bin")
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.png")
    extracted.read_message()
    read_output = capsys.readouterr().out

    assert Path("_secret.bin").read_bytes() == payload
    assert "File _secret.bin succesfully extracted from _host.png" in read_output


def test_png_binary_payload_without_filename_is_written_to_file(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png")
    payload = b"\x9d\xff\x00binary payload"

    host = HostElement("host.png")
    host.insert_message(payload, bits=2)
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.png")
    extracted.read_message()
    read_output = capsys.readouterr().out

    assert Path("_message.bin").read_bytes() == payload
    assert "Decoded payload is not valid UTF-8; wrote raw bytes to _message.bin" in read_output


def test_png_encrypted_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png")

    host = HostElement("host.png")
    host.insert_message(b"top secret", bits=4, password="hunter2")
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.png")
    extracted.read_message("hunter2")
    read_output = capsys.readouterr().out

    assert "top secret" in read_output


def test_wrong_password_reports_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.png")

    host = HostElement("host.png")
    host.insert_message(b"top secret", bits=2, password="hunter2")
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.png")
    extracted.read_message("incorrect")
    read_output = capsys.readouterr().out

    assert "Wrong password." in read_output


def test_jpeg_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_jpeg_host("host.jpg")

    host = HostElement("host.jpg")
    host.insert_message(b"jpeg payload", bits=2)
    host.save()
    save_output = capsys.readouterr().out

    assert Path("_host.jpg").exists()
    assert "Information encoded in _host.jpg." in save_output

    extracted = HostElement("_host.jpg")
    extracted.read_message()
    read_output = capsys.readouterr().out

    assert "jpeg payload" in read_output


def test_jpeg_file_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_jpeg_host("host.jpg")
    payload = b"\x00\x01\x02secret jpeg file payload"
    Path("secret.bin").write_bytes(payload)

    host = HostElement("host.jpg")
    host.insert_message(payload, bits=1, parasite_filename="secret.bin")
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.jpg")
    extracted.read_message()
    read_output = capsys.readouterr().out

    assert Path("_secret.bin").read_bytes() == payload
    assert "File _secret.bin succesfully extracted from _host.jpg" in read_output


def test_jpeg_encrypted_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_jpeg_host("host.jpg")

    host = HostElement("host.jpg")
    host.insert_message(b"top secret jpeg", bits=2, password="hunter2")
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.jpg")
    extracted.read_message("hunter2")
    read_output = capsys.readouterr().out

    assert "top secret jpeg" in read_output


def test_unsupported_image_host_is_saved_as_png(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_rgb_host("host.tiff")

    host = HostElement("host.tiff")
    host.insert_message(b"tiff host", bits=2)
    host.save()
    output = capsys.readouterr().out

    assert Path("_host.png").exists()
    assert "Host has a lossy format and will be converted to PNG." in output


def test_gif_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_gif_host("host.gif")

    host = HostElement("host.gif")
    host.insert_message(b"gif payload", bits=2)
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.gif")
    extracted.read_message()
    output = capsys.readouterr().out

    assert "gif payload" in output


def test_wav_text_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_wav_host("host.wav")

    host = HostElement("host.wav")
    host.insert_message(b"audio payload", bits=2)
    host.save()
    capsys.readouterr()

    extracted = HostElement("_host.wav")
    extracted.read_message()
    output = capsys.readouterr().out

    assert "audio payload" in output


def test_empty_wav_decode_reports_no_payload(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    create_wav_host("host.wav", size=10000)

    host = HostElement("host.wav")
    with pytest.raises(SystemExit):
        host.read_message()
    output = capsys.readouterr().out

    assert "ERROR! No encoded info found!" in output
