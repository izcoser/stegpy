#!/usr/bin/env python3
# Module for processing images, audios and the least significant bits.

import os.path

import jpeglib
import numpy
from PIL import Image

try:
    from . import crypt
except:
    import crypt

MAGIC_NUMBER = b"stegv3"
JPEG_FORMATS = {"jpg", "jpeg"}
JPEG_BITS_TO_CODE = {1: 0, 2: 1, 4: 2}
JPEG_CODE_TO_BITS = {code: bits for bits, code in JPEG_BITS_TO_CODE.items()}
JPEG_ZIGZAG_ORDER = [
    (0, 0),
    (0, 1),
    (1, 0),
    (2, 0),
    (1, 1),
    (0, 2),
    (0, 3),
    (1, 2),
    (2, 1),
    (3, 0),
    (4, 0),
    (3, 1),
    (2, 2),
    (1, 3),
    (0, 4),
    (0, 5),
    (1, 4),
    (2, 3),
    (3, 2),
    (4, 1),
    (5, 0),
    (6, 0),
    (5, 1),
    (4, 2),
    (3, 3),
    (2, 4),
    (1, 5),
    (0, 6),
    (0, 7),
    (1, 6),
    (2, 5),
    (3, 4),
    (4, 3),
    (5, 2),
    (6, 1),
    (7, 0),
    (7, 1),
    (6, 2),
    (5, 3),
    (4, 4),
    (3, 5),
    (2, 6),
    (1, 7),
    (2, 7),
    (3, 6),
    (4, 5),
    (5, 4),
    (6, 3),
    (7, 2),
    (7, 3),
    (6, 4),
    (5, 5),
    (4, 6),
    (3, 7),
    (4, 7),
    (5, 6),
    (6, 5),
    (7, 4),
    (7, 5),
    (6, 6),
    (5, 7),
    (6, 7),
    (7, 6),
    (7, 7),
]
JPEG_ZIGZAG_OFFSETS = numpy.asarray(
    [row * 8 + col for row, col in JPEG_ZIGZAG_ORDER[1:]], dtype=numpy.int64
)


def get_format(filename):
    return os.path.splitext(filename)[1].lower().lstrip(".")


def is_jpeg_format(file_format):
    return file_format in JPEG_FORMATS


class HostElement:
    """This class holds information about a host element."""

    def __init__(self, filename):
        self.filename = filename
        self.format = get_format(filename)
        self.header, self.data = get_file(filename)

    def save(self):
        self.filename = "_" + self.filename
        if self.format.lower() == "wav":
            sound = numpy.concatenate((self.header, self.data))
            sound.tofile(self.filename)
        elif self.format.lower() == "gif":
            gif = []
            for frame, palette in zip(self.data, self.header[0]):
                image = Image.fromarray(frame, mode="P")
                image.putpalette(palette)
                gif.append(image)
            gif[0].save(
                self.filename,
                save_all=len(gif) > 1,
                append_images=gif[1:],
                loop=0,
                duration=self.header[1],
            )
        elif is_jpeg_format(self.format):
            self.header.write_dct(self.filename)
        else:
            if not self.filename.lower().endswith(("png", "bmp", "webp")):
                print("Host has a lossy format and will be converted to PNG.")
                self.filename = os.path.splitext(self.filename)[0] + ".png"
            image = Image.fromarray(self.data)
            image.save(self.filename, lossless=True, minimize_size=True, optimize=True)
        print("Information encoded in {}.".format(self.filename))

    def insert_message(self, message, bits=2, parasite_filename=None, password=None):
        raw_message_len = len(message).to_bytes(4, "big")
        formatted_message = format_message(message, raw_message_len, parasite_filename)
        if password:
            formatted_message = crypt.encrypt_info(password, formatted_message)
        if is_jpeg_format(self.format):
            self.data = encode_jpeg_message(self.data, formatted_message, bits)
        else:
            self.data = encode_message(self.data, formatted_message, bits)

    def read_message(self, password=None):
        if is_jpeg_format(self.format):
            msg = decode_jpeg_message(self.data)
        else:
            msg = decode_message(self.data)

        if password:
            try:
                msg = crypt.decrypt_embedded_info(password, msg)
            except:
                print("Wrong password.")
                return

        check_magic_number(msg)
        msg_len = int.from_bytes(bytes(msg[6:10]), "big")
        filename_len = int.from_bytes(bytes(msg[10:11]), "big")

        start = filename_len + 11
        end = start + msg_len
        end_filename = filename_len + 11
        if filename_len > 0:
            filename = "_" + bytes(msg[11:end_filename]).decode("utf-8")

        else:
            text = bytes(msg[start:end]).decode("utf-8")
            print(text)
            return

        with open(filename, "wb") as f:
            f.write(bytes(msg[start:end]))

        print("File {} succesfully extracted from {}".format(filename, self.filename))

    def free_space(self, bits=2):
        if is_jpeg_format(self.format):
            self.free = jpeg_free_space(self.data, bits)
            return self.free

        shape = self.data.shape
        self.data.shape = -1
        free = self.data.size * bits // 8
        self.data.shape = shape
        self.free = free
        return free

    def print_free_space(self, bits=2):
        free = self.free_space(bits)
        print(
            "File: {}, free: (bytes) {:,}, encoding: 4 bit".format(
                self.filename, free, bits
            )
        )


def get_file(filename):
    """Returns data from file in a list with the header and raw data."""
    if filename.lower().endswith("wav"):
        content = numpy.fromfile(filename, dtype=numpy.uint8)
        content = content[:10000], content[10000:]
    elif filename.lower().endswith("gif"):
        image = Image.open(filename)
        frames = []
        palettes = []
        try:
            while True:
                frames.append(numpy.array(image))
                palettes.append(image.getpalette())
                image.seek(image.tell() + 1)
        except EOFError:
            pass
        content = [palettes, image.info.get("duration", 100)], numpy.asarray(frames)
    elif is_jpeg_format(get_format(filename)):
        jpeg = jpeglib.read_dct(filename)
        content = jpeg, get_jpeg_channels(jpeg)
    else:
        image = Image.open(filename)
        if image.mode != "RGB":
            image = image.convert("RGB")
        content = None, numpy.array(image)
    return content


def get_jpeg_channels(jpeg):
    channels = [jpeg.Y]
    if getattr(jpeg, "Cb", None) is not None and getattr(jpeg, "Cr", None) is not None:
        channels.extend([jpeg.Cb, jpeg.Cr])
    return channels


def get_jpeg_carrier_sets(channels):
    carrier_sets = []
    total_carriers = 0

    for channel in channels:
        flat = channel.reshape(-1)
        block_count = channel.shape[0] * channel.shape[1]
        block_bases = (numpy.arange(block_count, dtype=numpy.int64) * 64).reshape(-1, 1)
        indices = (block_bases + JPEG_ZIGZAG_OFFSETS).reshape(-1)
        carrier_sets.append((flat, indices))
        total_carriers += len(indices)

    return carrier_sets, total_carriers


def set_jpeg_carrier_value(coeff, value, bits):
    coeff = int(coeff)
    value = int(value)
    modulus = 2**bits
    sign = -1 if coeff < 0 else 1
    abs_coeff = abs(coeff)

    if abs_coeff == 0 and value == 0:
        return 0

    if abs_coeff >= value:
        lower = abs_coeff - ((abs_coeff - value) % modulus)
    else:
        lower = value

    upper = lower + modulus
    candidates = [lower, upper]

    if value != 0:
        candidates = [
            candidate if candidate != 0 else candidate + modulus
            for candidate in candidates
        ]

    target = min(
        candidates, key=lambda candidate: (abs(candidate - abs_coeff), candidate)
    )

    if target == 0:
        return 0

    return sign * target


def encode_jpeg_message(channels, message, bits):
    """Encodes a byte array in JPEG DCT coefficients."""
    carrier_sets, total_carriers = get_jpeg_carrier_sets(channels)
    total_coefficients = sum(channel.size for channel in channels)
    max_message_len = max(0, (total_carriers - 1) * bits // 8)

    print("Host dimension: {:,} DCT coefficients".format(total_coefficients))
    print("Message size: {:,} bytes".format(len(message)))
    print("Maximum size: {:,} bytes".format(max_message_len))

    check_message_space(max_message_len, len(message))

    first_flat, first_indices = carrier_sets[0]
    first_flat[first_indices[0]] = set_jpeg_carrier_value(
        first_flat[first_indices[0]], JPEG_BITS_TO_CODE[bits], 2
    )

    chunk_mask = 2**bits - 1
    divisor = 8 // bits
    payload_chunks = []

    for byte in message:
        for offset in range(divisor):
            payload_chunks.append(byte >> bits * offset & chunk_mask)

    chunk_index = 0
    metadata_written = False

    for flat, indices in carrier_sets:
        start = 1 if not metadata_written else 0
        metadata_written = True

        for index in indices[start:]:
            if chunk_index >= len(payload_chunks):
                return channels

            flat[index] = set_jpeg_carrier_value(
                flat[index], payload_chunks[chunk_index], bits
            )
            chunk_index += 1

    return channels


def decode_jpeg_message(channels):
    """Decodes JPEG DCT coefficients into a byte array."""
    carrier_sets, total_carriers = get_jpeg_carrier_sets(channels)
    if total_carriers == 0:
        return numpy.zeros(0, dtype=numpy.uint8)

    first_flat, first_indices = carrier_sets[0]
    bits_code = abs(int(first_flat[first_indices[0]])) & 3
    bits = JPEG_CODE_TO_BITS.get(bits_code, 2)
    chunk_mask = 2**bits - 1
    divisor = 8 // bits
    chunks = []
    metadata_read = False

    for flat, indices in carrier_sets:
        start = 1 if not metadata_read else 0
        metadata_read = True
        coeffs = numpy.abs(flat[indices[start:]].astype(numpy.int32))
        chunks.append((coeffs & chunk_mask).astype(numpy.uint8))

    payload_chunks = (
        numpy.concatenate(chunks) if chunks else numpy.zeros(0, dtype=numpy.uint8)
    )
    usable_chunks = len(payload_chunks) - (len(payload_chunks) % divisor)
    payload_chunks = payload_chunks[:usable_chunks]
    msg = numpy.zeros(len(payload_chunks) // divisor, dtype=numpy.uint8)

    for i in range(divisor):
        msg |= payload_chunks[i::divisor] << bits * i

    return msg


def jpeg_free_space(channels, bits=2):
    _, total_carriers = get_jpeg_carrier_sets(channels)
    return max(0, (total_carriers - 1) * bits // 8)


def format_message(message, msg_len, filename=None):
    if not filename:  # text
        message = MAGIC_NUMBER + msg_len + (0).to_bytes(1, "big") + message
    else:
        filename = filename.encode("utf-8")
        filename_len = len(filename).to_bytes(1, "big")
        message = MAGIC_NUMBER + msg_len + filename_len + filename + message
    return message


def encode_message(host_data, message, bits):
    """Encodes the byte array in the image numpy array."""
    shape = host_data.shape
    host_data.shape = (-1,)  # convert to 1D
    uneven = 0
    divisor = 8 // bits

    print("Host dimension: {:,} bytes".format(host_data.size))
    print("Message size: {:,} bytes".format(len(message)))
    print("Maximum size: {:,} bytes".format(host_data.size // divisor))

    check_message_space(host_data.size // divisor, len(message))

    if (
        host_data.size % divisor != 0
    ):  # Hacky way to deal with pixel arrays that cannot be divided evenly
        uneven = 1
        original_size = host_data.size
        host_data = numpy.resize(
            host_data, host_data.size + (divisor - host_data.size % divisor)
        )

    msg = numpy.zeros(len(host_data) // divisor, dtype=numpy.uint8)

    msg[: len(message)] = list(message)

    host_data[: divisor * len(message)] &= 256 - 2**bits  # clear last bit(s)
    for i in range(divisor):
        host_data[i::divisor] |= msg >> bits * i & (
            2**bits - 1
        )  # copy bits to host_data

    operand = 0 if (bits == 1) else (16 if (bits == 2) else 32)
    host_data[0] = (host_data[0] & 207) | operand  # 5th and 6th bits = log_2(bits)

    if uneven:
        host_data = numpy.resize(host_data, original_size)

    host_data.shape = shape  # restore the 3D shape

    return host_data


def check_message_space(max_message_len, message_len):
    """Checks if there's enough space to write the message."""
    if max_message_len < message_len:
        print("You have too few colors to store that message. Aborting.")
        exit(-1)
    else:
        print("Ok.")


def decode_message(host_data):
    """Decodes the image numpy array into a byte array."""
    host_data.shape = (-1,)  # convert to 1D
    bits = 2 ** int((host_data[0] & 48) >> 4)  # bits = 2 ^ (5th and 6th bits)
    divisor = 8 // bits

    if host_data.size % divisor != 0:
        host_data = numpy.resize(
            host_data, host_data.size + (divisor - host_data.size % divisor)
        )

    msg = numpy.zeros(len(host_data) // divisor, dtype=numpy.uint8)

    for i in range(divisor):
        msg |= (host_data[i::divisor] & (2**bits - 1)) << bits * i

    return msg


def check_magic_number(msg):
    if bytes(msg[0:6]) != MAGIC_NUMBER:
        print(bytes(msg[:6]))
        print("ERROR! No encoded info found!")
        exit(-1)


if __name__ == "__main__":
    message = "hello".encode("utf-8")
    host = HostElement("gif.gif")
    host.insert_message(message, bits=4)
    host.save()
