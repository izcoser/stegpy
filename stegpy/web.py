import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from . import crypt, lsb


APP_ROOT = Path(__file__).resolve().parent.parent
SOURCE_STATIC_ROOT = APP_ROOT / "web-demo"
INSTALLED_STATIC_ROOT = Path(sys.prefix) / "web-demo"
STATIC_ROOT = (
    SOURCE_STATIC_ROOT if SOURCE_STATIC_ROOT.exists() else INSTALLED_STATIC_ROOT
)
SUPPORTED_HOST_EXTENSIONS = {"png", "bmp", "gif", "webp", "wav", "jpg", "jpeg"}
ALLOWED_BITS = {1, 2, 4}
MAX_HOST_BYTES = 20 * 1024 * 1024
MAX_PAYLOAD_BYTES = 20 * 1024 * 1024
MAX_MESSAGE_BYTES = 1 * 1024 * 1024
PAYLOAD_HEADER_BYTES = 11

app = FastAPI(title="stegpy demo")


def safe_filename(filename, fallback):
    name = Path(filename or fallback).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._")
    return name or fallback


def host_extension(filename):
    return Path(filename).suffix.lower().lstrip(".")


def validate_bits(bits):
    if bits not in ALLOWED_BITS:
        raise HTTPException(status_code=400, detail="Bits must be one of 1, 2, or 4.")
    return bits


def validate_host_name(filename):
    extension = host_extension(filename)
    if extension not in SUPPORTED_HOST_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_HOST_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported host format. Use one of: {supported}.",
        )


def embedded_filename_bytes(mode, filename=""):
    if mode == "text":
        return b""
    if mode != "file":
        raise HTTPException(status_code=400, detail="Mode must be text or file.")

    encoded = safe_filename(filename, "payload.bin").encode("utf-8")
    if len(encoded) > 255:
        raise HTTPException(
            status_code=400,
            detail="The embedded filename must be at most 255 bytes.",
        )
    return encoded


def encoded_payload_size(payload_bytes, filename_bytes=b"", encrypted=False):
    formatted_size = PAYLOAD_HEADER_BYTES + len(filename_bytes) + payload_bytes
    if encrypted:
        return crypt.encrypted_info_size(formatted_size)
    return formatted_size


def usable_payload_capacity(carrier_bytes, filename_bytes=b"", encrypted=False):
    low = 0
    high = max(0, carrier_bytes)

    while low < high:
        candidate = (low + high + 1) // 2
        if encoded_payload_size(candidate, filename_bytes, encrypted) <= carrier_bytes:
            low = candidate
        else:
            high = candidate - 1

    if encoded_payload_size(low, filename_bytes, encrypted) > carrier_bytes:
        return 0
    return low


async def save_upload(upload, directory, max_bytes, fallback):
    filename = safe_filename(upload.filename, fallback)
    path = directory / filename
    total = 0

    with path.open("wb") as output:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"{filename} exceeds the "
                        f"{max_bytes // (1024 * 1024)} MB demo limit."
                    ),
                )
            output.write(chunk)

    if total == 0:
        raise HTTPException(status_code=400, detail=f"{filename} is empty.")
    return path


def decode_payload(host):
    if lsb.is_jpeg_format(host.format):
        return lsb.decode_jpeg_message(host.data)
    return lsb.decode_message(host.data)


def parse_message(raw_message, password):
    message = raw_message
    if password:
        try:
            message = crypt.decrypt_embedded_info(password, message)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Wrong password.") from exc

    if len(message) < 11 or bytes(message[:6]) != lsb.MAGIC_NUMBER:
        raise HTTPException(
            status_code=400,
            detail="No stegpy payload was found in this host file.",
        )

    payload_length = int.from_bytes(bytes(message[6:10]), "big")
    filename_length = int.from_bytes(bytes(message[10:11]), "big")
    filename_start = 11
    payload_start = filename_start + filename_length
    payload_end = payload_start + payload_length

    if payload_end > len(message):
        raise HTTPException(status_code=400, detail="The stegpy payload is incomplete.")

    embedded_filename = ""
    if filename_length:
        embedded_filename = bytes(message[filename_start:payload_start]).decode("utf-8")

    return embedded_filename, bytes(message[payload_start:payload_end])


def run_processing(callback):
    try:
        return callback()
    except SystemExit as exc:
        raise HTTPException(status_code=400, detail="Payload does not fit in host file.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Processing failed.") from exc


@app.get("/api/health")
def health():
    return {"ok": True, "service": "stegpy"}


@app.post("/api/capacity")
async def capacity(
    host: UploadFile = File(...),
    bits: int = Form(2),
    mode: str = Form("text"),
    filename: str = Form(""),
    encrypted: bool = Form(False),
):
    validate_bits(bits)
    validate_host_name(host.filename)
    filename_bytes = embedded_filename_bytes(mode, filename)
    workdir = Path(tempfile.mkdtemp(prefix="stegpy-"))

    try:
        host_path = await save_upload(host, workdir, MAX_HOST_BYTES, "host")

        def calculate():
            return lsb.HostElement(str(host_path)).free_space(bits)

        carrier_bytes = await run_in_threadpool(run_processing, calculate)
        capacity_bytes = usable_payload_capacity(
            carrier_bytes,
            filename_bytes=filename_bytes,
            encrypted=encrypted,
        )
        return JSONResponse(
            {
                "capacityBytes": capacity_bytes,
                "carrierCapacityBytes": carrier_bytes,
                "bits": bits,
                "mode": mode,
                "encrypted": encrypted,
            },
            background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
        )
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise


@app.post("/api/encode")
async def encode(
    host: UploadFile = File(...),
    mode: str = Form("text"),
    message: str = Form(""),
    payload: Optional[UploadFile] = File(None),
    bits: int = Form(2),
    password: str = Form(""),
):
    validate_bits(bits)
    validate_host_name(host.filename)
    workdir = Path(tempfile.mkdtemp(prefix="stegpy-"))

    try:
        host_path = await save_upload(host, workdir, MAX_HOST_BYTES, "host")
        embedded_filename = None

        if mode == "text":
            embedded_filename_bytes(mode)
            payload_bytes = message.encode("utf-8")
            if len(payload_bytes) > MAX_MESSAGE_BYTES:
                raise HTTPException(status_code=413, detail="Message is too large.")
        elif mode == "file":
            if payload is None or not payload.filename:
                raise HTTPException(status_code=400, detail="Choose a payload file.")
            embedded_filename = safe_filename(payload.filename, "payload.bin")
            embedded_filename_bytes(mode, embedded_filename)
            payload_path = await save_upload(
                payload, workdir, MAX_PAYLOAD_BYTES, embedded_filename
            )
            payload_bytes = payload_path.read_bytes()
        else:
            embedded_filename_bytes(mode)

        def encode_file():
            element = lsb.HostElement(str(host_path))
            element.insert_message(
                payload_bytes,
                bits=bits,
                parasite_filename=embedded_filename,
                password=password or None,
            )
            output_path = workdir / f"_{host_path.name}"
            element.save(output_path)
            return Path(element.filename)

        output_path = await run_in_threadpool(run_processing, encode_file)
        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Encoded output was not created.")

        return FileResponse(
            output_path,
            filename=output_path.name,
            background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
        )
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise


@app.post("/api/decode")
async def decode(host: UploadFile = File(...), password: str = Form("")):
    validate_host_name(host.filename)
    workdir = Path(tempfile.mkdtemp(prefix="stegpy-"))

    try:
        host_path = await save_upload(host, workdir, MAX_HOST_BYTES, "host")

        def extract():
            element = lsb.HostElement(str(host_path))
            return parse_message(decode_payload(element), password or None)

        embedded_filename, payload_bytes = await run_in_threadpool(
            run_processing, extract
        )

        if embedded_filename:
            filename = safe_filename(embedded_filename, "payload.bin")
            output_path = workdir / filename
            output_path.write_bytes(payload_bytes)
            return FileResponse(
                output_path,
                filename=filename,
                background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
            )

        try:
            text = payload_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="The decoded payload is not valid UTF-8 text.",
            ) from exc

        return JSONResponse(
            {"kind": "text", "message": text},
            background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
        )
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise


if STATIC_ROOT.exists():
    app.mount("/", StaticFiles(directory=STATIC_ROOT, html=True), name="static")
