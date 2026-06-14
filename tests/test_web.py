import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from stegpy import web
from stegpy.web import app


client = TestClient(app)


def create_png_bytes(size=(32, 32)):
    pixels = np.arange(size[0] * size[1] * 3, dtype=np.uint8).reshape(
        size[1], size[0], 3
    )
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="PNG")
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


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "stegpy"}


def test_capacity_endpoint_reports_png_capacity():
    host = create_png_bytes()

    response = client.post(
        "/api/capacity",
        data={"bits": "2"},
        files={"host": ("host.png", host, "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["capacityBytes"] == 32 * 32 * 3 * 2 // 8


def test_capacity_endpoint_accepts_mixed_mode_gif_frames():
    host = create_gif_bytes()

    response = client.post(
        "/api/capacity",
        data={"bits": "2"},
        files={"host": ("host.gif", host, "image/gif")},
    )

    assert response.status_code == 200
    assert response.json()["capacityBytes"] == 2 * 24 * 24 * 2 // 8


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
