#!/usr/bin/env python3
# Module for robust video steganography through decoded-frame DCT embedding.

import contextlib
import json
import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy

try:
    from . import crypt, lsb
except:
    import crypt
    import lsb


VIDEO_FORMATS = {"mp4", "m4v", "mov", "mkv", "webm", "avi"}
DEFAULT_REPETITION = 9
DEFAULT_MARGIN = 80.0
DEFAULT_CRF = 20
BLOCK_SIZE = 8
COEFFICIENT_A = (1, 2)
COEFFICIENT_B = (2, 1)


class VideoProcessingError(RuntimeError):
    """Raised when ffmpeg or ffprobe cannot process a video host."""


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: str
    frame_count: int


def is_video_format(file_format):
    return str(file_format).lower().lstrip(".") in VIDEO_FORMATS


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def require_ffmpeg():
    if not ffmpeg_available():
        raise VideoProcessingError(
            "Video support requires ffmpeg and ffprobe to be installed."
        )


def prefixed_output_path(filename):
    path = Path(filename)
    return path.with_name("_" + path.stem + ".mp4")


def _run_json(command):
    require_ffmpeg()
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise VideoProcessingError(completed.stderr.strip() or "ffprobe failed.")
    return json.loads(completed.stdout)


def _parse_rate(rate):
    if not rate or rate == "0/0":
        return None
    if "/" not in rate:
        try:
            value = float(rate)
        except ValueError:
            return None
        if value <= 0:
            return None
        return rate

    numerator, denominator = rate.split("/", 1)
    try:
        numerator = int(numerator)
        denominator = int(denominator)
    except ValueError:
        return None

    if numerator <= 0 or denominator <= 0:
        return None
    return f"{numerator}/{denominator}"


def _rate_as_float(rate):
    parsed = _parse_rate(rate)
    if not parsed:
        return None
    if "/" not in parsed:
        return float(parsed)
    numerator, denominator = parsed.split("/", 1)
    return int(numerator) / int(denominator)


def probe_video(filename, count_frames=True):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
    ]
    if count_frames:
        command.append("-count_frames")
    command.extend(
        [
            "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate,nb_read_frames,nb_frames,duration",
            "-of",
            "json",
            os.fspath(filename),
        ]
    )

    data = _run_json(command)
    streams = data.get("streams", [])
    if not streams:
        raise VideoProcessingError("No video stream was found in this host file.")

    stream = streams[0]
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    fps = _parse_rate(stream.get("avg_frame_rate")) or _parse_rate(
        stream.get("r_frame_rate")
    )
    if not width or not height or not fps:
        raise VideoProcessingError("Could not determine video dimensions or frame rate.")

    try:
        frame_count = _stream_frame_count(stream, fps)
    except VideoProcessingError:
        if count_frames:
            raise
        frame_count = 0
    return VideoInfo(width=width, height=height, fps=fps, frame_count=frame_count)


def _stream_frame_count(stream, fps):
    for key in ("nb_read_frames", "nb_frames"):
        value = stream.get(key)
        if value and str(value).isdigit():
            return int(value)

    duration = stream.get("duration")
    fps_value = _rate_as_float(fps)
    if duration and fps_value:
        try:
            return max(1, math.ceil(float(duration) * fps_value))
        except ValueError:
            pass

    raise VideoProcessingError("Could not determine how many frames the video has.")


def _build_dct_matrix(size=BLOCK_SIZE):
    matrix = numpy.zeros((size, size), dtype=numpy.float32)
    for coefficient in range(size):
        scale = (1 / size) ** 0.5 if coefficient == 0 else (2 / size) ** 0.5
        for sample in range(size):
            matrix[coefficient, sample] = scale * numpy.cos(
                numpy.pi * (2 * sample + 1) * coefficient / (2 * size)
            )
    return matrix


DCT_MATRIX = _build_dct_matrix()
INVERSE_DCT_MATRIX = DCT_MATRIX.T


def _carrier_count(info):
    blocks_per_frame = (info.width // BLOCK_SIZE) * (info.height // BLOCK_SIZE)
    return blocks_per_frame * info.frame_count


def video_free_space(filename, repetition=DEFAULT_REPETITION):
    repetition = _validate_repetition(repetition)
    info = probe_video(filename)
    return _carrier_count(info) // repetition // 8


def print_free_space(filename, repetition=DEFAULT_REPETITION):
    free = video_free_space(filename, repetition)
    print(
        "File: {}, free: (bytes) {:,}, encoding: video DCT/H.264".format(
            filename, free
        )
    )


def _validate_repetition(repetition):
    repetition = int(repetition)
    if repetition < 1 or repetition % 2 == 0:
        raise ValueError("Video repetition must be a positive odd number.")
    return repetition


def _payload_to_repeated_bits(payload, repetition):
    bits = numpy.unpackbits(numpy.frombuffer(payload, dtype=numpy.uint8))
    return numpy.repeat(bits, repetition).astype(numpy.uint8)


def _repeated_bits_to_payload(repeated_bits, repetition):
    usable = len(repeated_bits) - (len(repeated_bits) % repetition)
    if usable < repetition:
        return b""

    groups = repeated_bits[:usable].reshape(-1, repetition)
    bits = (groups.sum(axis=1) > (repetition // 2)).astype(numpy.uint8)
    usable_bits = len(bits) - (len(bits) % 8)
    if usable_bits < 8:
        return b""
    return numpy.packbits(bits[:usable_bits]).tobytes()


def _embed_bits_in_frame(frame, repeated_bits, bit_index, margin):
    if bit_index >= len(repeated_bits):
        return frame, bit_index

    pixels = frame.astype(numpy.float32)
    luminance = (
        0.299 * pixels[:, :, 0]
        + 0.587 * pixels[:, :, 1]
        + 0.114 * pixels[:, :, 2]
    )
    used_height = luminance.shape[0] // BLOCK_SIZE * BLOCK_SIZE
    used_width = luminance.shape[1] // BLOCK_SIZE * BLOCK_SIZE

    for top in range(0, used_height, BLOCK_SIZE):
        for left in range(0, used_width, BLOCK_SIZE):
            if bit_index >= len(repeated_bits):
                encoded = numpy.clip(numpy.rint(pixels), 0, 255)
                return encoded.astype(numpy.uint8), bit_index

            block = luminance[top : top + BLOCK_SIZE, left : left + BLOCK_SIZE] - 128.0
            coefficients = DCT_MATRIX @ block @ INVERSE_DCT_MATRIX
            first = coefficients[COEFFICIENT_A]
            second = coefficients[COEFFICIENT_B]
            center = (first + second) / 2.0

            if repeated_bits[bit_index]:
                coefficients[COEFFICIENT_A] = center + margin / 2.0
                coefficients[COEFFICIENT_B] = center - margin / 2.0
            else:
                coefficients[COEFFICIENT_A] = center - margin / 2.0
                coefficients[COEFFICIENT_B] = center + margin / 2.0

            updated = INVERSE_DCT_MATRIX @ coefficients @ DCT_MATRIX + 128.0
            delta = updated - luminance[top : top + BLOCK_SIZE, left : left + BLOCK_SIZE]
            pixels[top : top + BLOCK_SIZE, left : left + BLOCK_SIZE, :] += delta[
                :, :, None
            ]
            bit_index += 1

    return numpy.clip(numpy.rint(pixels), 0, 255).astype(numpy.uint8), bit_index


def _extract_bits_from_frame(frame):
    pixels = frame.astype(numpy.float32)
    luminance = (
        0.299 * pixels[:, :, 0]
        + 0.587 * pixels[:, :, 1]
        + 0.114 * pixels[:, :, 2]
    )
    used_height = luminance.shape[0] // BLOCK_SIZE * BLOCK_SIZE
    used_width = luminance.shape[1] // BLOCK_SIZE * BLOCK_SIZE
    bits = []

    for top in range(0, used_height, BLOCK_SIZE):
        for left in range(0, used_width, BLOCK_SIZE):
            block = luminance[top : top + BLOCK_SIZE, left : left + BLOCK_SIZE] - 128.0
            coefficients = DCT_MATRIX @ block @ INVERSE_DCT_MATRIX
            bits.append(
                1 if coefficients[COEFFICIENT_A] > coefficients[COEFFICIENT_B] else 0
            )

    return bits


def _decoder_command(filename):
    return [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        os.fspath(filename),
        "-map",
        "0:v:0",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
    ]


def _encoder_command(input_filename, output_filename, info, crf):
    return [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{info.width}x{info.height}",
        "-r",
        info.fps,
        "-i",
        "-",
        "-i",
        os.fspath(input_filename),
        "-map",
        "0:v:0",
        "-map",
        "1:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-shortest",
        os.fspath(output_filename),
    ]


def encode_payload(
    input_filename,
    payload,
    output_filename=None,
    repetition=DEFAULT_REPETITION,
    margin=DEFAULT_MARGIN,
    crf=DEFAULT_CRF,
):
    require_ffmpeg()
    repetition = _validate_repetition(repetition)
    input_filename = Path(input_filename)
    output_filename = (
        Path(output_filename) if output_filename else prefixed_output_path(input_filename)
    )
    info = probe_video(input_filename)
    carriers = _carrier_count(info)
    max_message_len = carriers // repetition // 8

    print("Host dimension: {:,} video DCT carriers".format(carriers))
    print("Message size: {:,} bytes".format(len(payload)))
    print("Maximum size: {:,} bytes".format(max_message_len))
    lsb.check_message_space(max_message_len, len(payload))

    repeated_bits = _payload_to_repeated_bits(payload, repetition)
    frame_size = info.width * info.height * 3
    decoder = subprocess.Popen(
        _decoder_command(input_filename),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        _encoder_command(input_filename, output_filename, info, crf),
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    bit_index = 0

    try:
        while True:
            raw_frame = decoder.stdout.read(frame_size)
            if not raw_frame:
                break
            if len(raw_frame) != frame_size:
                raise VideoProcessingError("ffmpeg returned a partial video frame.")

            frame = numpy.frombuffer(raw_frame, dtype=numpy.uint8).reshape(
                info.height, info.width, 3
            )
            frame, bit_index = _embed_bits_in_frame(
                frame.copy(), repeated_bits, bit_index, margin
            )
            encoder.stdin.write(frame.tobytes())

        encoder.stdin.close()
        decoder_error = decoder.stderr.read().decode("utf-8", "replace").strip()
        decoder_return = decoder.wait()
        encoder_error = encoder.stderr.read().decode("utf-8", "replace").strip()
        encoder_return = encoder.wait()
    except Exception:
        with contextlib.suppress(Exception):
            decoder.kill()
        with contextlib.suppress(Exception):
            encoder.kill()
        raise

    if decoder_return != 0:
        raise VideoProcessingError(decoder_error or "ffmpeg video decode failed.")
    if encoder_return != 0:
        raise VideoProcessingError(encoder_error or "ffmpeg video encode failed.")
    if bit_index < len(repeated_bits):
        raise VideoProcessingError("Video ended before the full payload was embedded.")

    print("Information encoded in {}.".format(output_filename))
    return output_filename


def decode_payload(input_filename, repetition=DEFAULT_REPETITION):
    require_ffmpeg()
    repetition = _validate_repetition(repetition)
    info = probe_video(input_filename, count_frames=False)
    frame_size = info.width * info.height * 3
    decoder = subprocess.Popen(
        _decoder_command(input_filename),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    extracted_bits = []

    while True:
        raw_frame = decoder.stdout.read(frame_size)
        if not raw_frame:
            break
        if len(raw_frame) != frame_size:
            decoder.kill()
            raise VideoProcessingError("ffmpeg returned a partial video frame.")
        frame = numpy.frombuffer(raw_frame, dtype=numpy.uint8).reshape(
            info.height, info.width, 3
        )
        extracted_bits.extend(_extract_bits_from_frame(frame))

    decoder_error = decoder.stderr.read().decode("utf-8", "replace").strip()
    decoder_return = decoder.wait()
    if decoder_return != 0:
        raise VideoProcessingError(decoder_error or "ffmpeg video decode failed.")

    if not extracted_bits:
        return b""
    return _repeated_bits_to_payload(
        numpy.asarray(extracted_bits, dtype=numpy.uint8), repetition
    )


def insert_message(
    input_filename,
    message,
    parasite_filename=None,
    password=None,
    output_filename=None,
    repetition=DEFAULT_REPETITION,
):
    raw_message_len = len(message).to_bytes(4, "big")
    formatted_message = lsb.format_message(message, raw_message_len, parasite_filename)
    if password:
        formatted_message = crypt.encrypt_info(password, formatted_message)
    return encode_payload(
        input_filename,
        formatted_message,
        output_filename=output_filename,
        repetition=repetition,
    )


def read_message(input_filename, password=None, repetition=DEFAULT_REPETITION):
    msg = decode_payload(input_filename, repetition=repetition)

    if password:
        try:
            msg = crypt.decrypt_embedded_info(password, msg)
        except:
            print("Wrong password.")
            return

    lsb.check_magic_number(msg)
    msg_len = int.from_bytes(bytes(msg[6:10]), "big")
    filename_len = int.from_bytes(bytes(msg[10:11]), "big")

    start = filename_len + 11
    end = start + msg_len
    end_filename = filename_len + 11
    if filename_len > 0:
        filename = "_" + bytes(msg[11:end_filename]).decode("utf-8")
    else:
        payload = bytes(msg[start:end])
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            filename = "_message.bin"
            with open(filename, "wb") as f:
                f.write(payload)
            print(
                "Decoded payload is not valid UTF-8; wrote raw bytes to {}".format(
                    filename
                )
            )
            return

        print(text)
        return

    with open(filename, "wb") as f:
        f.write(bytes(msg[start:end]))

    print("File {} succesfully extracted from {}".format(filename, input_filename))
