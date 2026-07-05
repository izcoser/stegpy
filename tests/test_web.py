import io
import subprocess

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from stegpy import web
from stegpy.web import app


client = TestClient(app, base_url="http://localhost")
public_client = TestClient(app, base_url="https://stegpy.coseri.xyz")


def create_png_bytes(size=(32, 32)):
    pixels = np.arange(size[0] * size[1] * 3, dtype=np.uint8).reshape(
        size[1], size[0], 3
    )
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="PNG")
    output.seek(0)
    return output.getvalue()


def create_jpeg_bytes(size=(128, 128)):
    y = np.arange(size[1], dtype=np.uint16).reshape(size[1], 1)
    x = np.arange(size[0], dtype=np.uint16).reshape(1, size[0])
    pixels = np.empty((size[1], size[0], 3), dtype=np.uint8)
    pixels[:, :, 0] = ((x * 7) + (y * 13)) % 256
    pixels[:, :, 1] = ((x * 11) ^ (y * 5)) % 256
    pixels[:, :, 2] = ((x * 3) + (y * 17) + ((x * y) % 31)) % 256
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="JPEG", quality=95, subsampling=0)
    output.seek(0)
    return output.getvalue()


def create_gif_bytes(size=(24, 24)):
    first_pixels = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    first_pixels[:, :, 0] = 255
    second_pixels = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    second_pixels[:, :, 1] = 255
    output = io.BytesIO()
    first = Image.fromarray(first_pixels, mode="RGB")
    second = Image.fromarray(second_pixels, mode="RGB")
    first.save(
        output,
        format="GIF",
        save_all=True,
        append_images=[second],
        duration=[80, 120],
        loop=0,
        optimize=False,
    )
    output.seek(0)
    return output.getvalue()


def create_mp4_bytes(size=(240, 160), count=18):
    if not web.video.ffmpeg_available():
        pytest.skip("ffmpeg and ffprobe are required for video tests")

    width, height = size
    rng = np.random.default_rng(12)
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
            "-movflags",
            "frag_keyframe+empty_moov",
            "-f",
            "mp4",
            "pipe:1",
        ],
        input=b"".join(frame.tobytes() for frame in frames),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip(completed.stderr.decode("utf-8", "replace"))

    return completed.stdout


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "stegpy"}


def test_frontend_explains_video_dct_mode():
    html = client.get("/").text
    script = client.get("/app.js?v=local-video-1").text

    assert "id=\"video-mode-note\"" in html
    assert "only on localhost" in html
    assert "styles.css?v=local-video-1" in html
    assert "app.js?v=local-video-1" in html
    assert "accept=\".png,.bmp,.gif,.webp,.wav,.jpg,.jpeg,image/png" in html
    assert "isVideoMode" in script
    assert "isLocalWebUi" in script
    assert "VIDEO_ACCEPT" in script
    assert "usable (video DCT)" in script


def test_capacity_endpoint_reports_usable_text_capacity():
    host = create_png_bytes()

    response = client.post(
        "/api/capacity",
        data={"bits": "2"},
        files={"host": ("host.png", host, "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "capacityBytes": 32 * 32 * 3 * 2 // 8 - 11,
        "carrierCapacityBytes": 32 * 32 * 3 * 2 // 8,
        "bits": 2,
        "mode": "text",
        "encrypted": False,
    }


@pytest.mark.parametrize("bits", [1, 2, 4])
def test_capacity_endpoint_reports_file_capacity_across_lsb_bit_depths(bits):
    host = create_png_bytes()
    filename = b"secret.bin"

    response = client.post(
        "/api/capacity",
        data={"bits": str(bits), "mode": "file", "filename": filename.decode()},
        files={"host": ("host.png", host, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    expected_carrier_capacity = 32 * 32 * 3 * bits // 8
    assert data["carrierCapacityBytes"] == expected_carrier_capacity
    assert data["capacityBytes"] == (
        expected_carrier_capacity - web.PAYLOAD_HEADER_BYTES - len(filename)
    )


@pytest.mark.parametrize("bits", [1, 2, 4])
def test_capacity_endpoint_reports_file_capacity_across_jpeg_bit_depths(bits):
    host = create_jpeg_bytes()
    filename = b"secret.bin"

    response = client.post(
        "/api/capacity",
        data={"bits": str(bits), "mode": "file", "filename": filename.decode()},
        files={"host": ("host.jpg", host, "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert web.encoded_payload_size(data["capacityBytes"], filename) <= data[
        "carrierCapacityBytes"
    ]
    assert web.encoded_payload_size(data["capacityBytes"] + 1, filename) > data[
        "carrierCapacityBytes"
    ]


def test_capacity_endpoint_accounts_for_filename_and_encryption():
    host = create_png_bytes()

    response = client.post(
        "/api/capacity",
        data={
            "bits": "2",
            "mode": "file",
            "filename": "secret.bin",
            "encrypted": "true",
        },
        files={"host": ("host.png", host, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    filename = b"secret.bin"
    assert data["carrierCapacityBytes"] == 768
    assert web.encoded_payload_size(
        data["capacityBytes"], filename, encrypted=True
    ) <= 768
    assert web.encoded_payload_size(
        data["capacityBytes"] + 1, filename, encrypted=True
    ) > 768


def test_capacity_endpoint_accepts_mixed_mode_gif_frames():
    host = create_gif_bytes()

    response = client.post(
        "/api/capacity",
        data={"bits": "2"},
        files={"host": ("host.gif", host, "image/gif")},
    )

    assert response.status_code == 200
    assert response.json()["capacityBytes"] == 2 * 24 * 24 * 2 // 8 - 11


def test_capacity_endpoint_reports_video_dct_capacity():
    host = create_mp4_bytes()

    response = client.post(
        "/api/capacity",
        data={"bits": "2"},
        files={"host": ("host.mp4", host, "video/mp4")},
    )

    assert response.status_code == 200
    data = response.json()
    expected_carrier_capacity = (30 * 20 * 18) // web.video.DEFAULT_REPETITION // 8
    assert data["carrierCapacityBytes"] == expected_carrier_capacity
    assert data["capacityBytes"] == expected_carrier_capacity - web.PAYLOAD_HEADER_BYTES


@pytest.mark.parametrize(
    ("endpoint", "data"),
    [
        ("/api/capacity", {"bits": "2"}),
        ("/api/encode", {"mode": "text", "message": "blocked"}),
        ("/api/decode", {}),
    ],
)
def test_public_demo_rejects_video_hosts(endpoint, data):
    response = public_client.post(
        endpoint,
        data=data,
        files={"host": ("host.mp4", b"not processed", "video/mp4")},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == web.PUBLIC_VIDEO_DISABLED_DETAIL


def test_video_hosts_are_limited_to_5_mb():
    response = client.post(
        "/api/capacity",
        data={"bits": "2"},
        files={
            "host": (
                "host.mp4",
                b"x" * (web.MAX_VIDEO_HOST_BYTES + 1),
                "video/mp4",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "host.mp4 exceeds the 5 MB demo limit."


def test_web_processing_runs_in_threadpool(monkeypatch):
    calls = []

    async def fake_run_in_threadpool(function, *args):
        calls.append(function)
        return function(*args)

    monkeypatch.setattr(web, "run_in_threadpool", fake_run_in_threadpool)
    host = create_png_bytes()

    with TestClient(app) as test_client:
        capacity_response = test_client.post(
            "/api/capacity",
            files={"host": ("host.png", host, "image/png")},
        )
        encode_response = test_client.post(
            "/api/encode",
            data={"mode": "text", "message": "threaded", "bits": "2"},
            files={"host": ("host.png", host, "image/png")},
        )
        decode_response = test_client.post(
            "/api/decode",
            files={"host": ("_host.png", encode_response.content, "image/png")},
        )

    assert capacity_response.status_code == 200
    assert encode_response.status_code == 200
    assert decode_response.status_code == 200
    assert calls == [web.run_processing, web.run_processing, web.run_processing]


def test_encode_and_decode_text_round_trip():
    host = create_png_bytes()

    encode_response = client.post(
        "/api/encode",
        data={"mode": "text", "message": "hello from web", "bits": "2"},
        files={"host": ("host.png", host, "image/png")},
    )

    assert encode_response.status_code == 200
    assert encode_response.headers["content-disposition"].endswith('filename="_host.png"')

    decode_response = client.post(
        "/api/decode",
        files={"host": ("_host.png", encode_response.content, "image/png")},
    )

    assert decode_response.status_code == 200
    assert decode_response.json() == {"kind": "text", "message": "hello from web"}


def test_encode_and_decode_encrypted_text_round_trip():
    host = create_png_bytes()

    encode_response = client.post(
        "/api/encode",
        data={
            "mode": "text",
            "message": "hello encrypted web",
            "bits": "4",
            "password": "hunter2",
        },
        files={"host": ("host.png", host, "image/png")},
    )

    assert encode_response.status_code == 200

    decode_response = client.post(
        "/api/decode",
        data={"password": "hunter2"},
        files={"host": ("_host.png", encode_response.content, "image/png")},
    )

    assert decode_response.status_code == 200
    assert decode_response.json() == {
        "kind": "text",
        "message": "hello encrypted web",
    }


def test_encode_and_decode_file_round_trip():
    host = create_png_bytes()
    payload = b"hidden file payload"

    encode_response = client.post(
        "/api/encode",
        data={"mode": "file", "bits": "1"},
        files={
            "host": ("host.png", host, "image/png"),
            "payload": ("secret.txt", payload, "text/plain"),
        },
    )

    assert encode_response.status_code == 200

    decode_response = client.post(
        "/api/decode",
        files={"host": ("_host.png", encode_response.content, "image/png")},
    )

    assert decode_response.status_code == 200
    assert decode_response.headers["content-disposition"].endswith('filename="secret.txt"')
    assert decode_response.content == payload


def test_encode_rejects_payload_over_demo_limit(monkeypatch):
    host = create_png_bytes()
    monkeypatch.setattr(web, "MAX_PAYLOAD_BYTES", 1024 * 1024)

    response = client.post(
        "/api/encode",
        data={"mode": "file", "bits": "1"},
        files={
            "host": ("host.png", host, "image/png"),
            "payload": (
                "secret.bin",
                b"x" * (1024 * 1024 + 1),
                "application/octet-stream",
            ),
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "secret.bin exceeds the 1 MB demo limit."


def test_encode_and_decode_video_text_round_trip():
    host = create_mp4_bytes()

    encode_response = client.post(
        "/api/encode",
        data={"mode": "text", "message": "hello from video web", "bits": "2"},
        files={"host": ("host.mp4", host, "video/mp4")},
    )

    assert encode_response.status_code == 200
    assert encode_response.headers["content-disposition"].endswith(
        'filename="_host.mp4"'
    )

    decode_response = client.post(
        "/api/decode",
        files={"host": ("_host.mp4", encode_response.content, "video/mp4")},
    )

    assert decode_response.status_code == 200
    assert decode_response.json() == {
        "kind": "text",
        "message": "hello from video web",
    }
