import numpy as np
import pytest

from stegpy import lsb


@pytest.mark.parametrize("bits", [1, 2, 4])
def test_encode_decode_round_trip_across_bit_depths(bits):
    host = np.arange(1800, dtype=np.uint8).reshape(20, 30, 3)
    message = b"stegpy characterization"

    encoded = lsb.encode_message(host.copy(), message, bits)
    decoded = lsb.decode_message(encoded.copy())

    assert bytes(decoded[: len(message)]) == message


def test_format_message_for_text_payload():
    message = b"hello"
    encoded_length = len(message).to_bytes(4, "big")

    formatted = lsb.format_message(message, encoded_length)

    assert formatted[:6] == lsb.MAGIC_NUMBER
    assert formatted[6:10] == encoded_length
    assert formatted[10] == 0
    assert formatted[11:] == message


def test_format_message_for_file_payload():
    message = b"hello"
    encoded_length = len(message).to_bytes(4, "big")

    formatted = lsb.format_message(message, encoded_length, "payload.bin")

    assert formatted[:6] == lsb.MAGIC_NUMBER
    assert formatted[6:10] == encoded_length
    assert formatted[10] == len("payload.bin")
    assert formatted[11 : 11 + len("payload.bin")] == b"payload.bin"
    assert formatted[11 + len("payload.bin") :] == message


def test_encode_message_rejects_too_large_payload():
    host = np.zeros((2, 2, 3), dtype=np.uint8)

    with pytest.raises(SystemExit):
        lsb.encode_message(host, b"this payload is too large", 1)
