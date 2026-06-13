from stegpy import crypt


def test_encrypt_and_decrypt_round_trip():
    token = crypt.encrypt_info("hunter2", b"hidden message")
    salt = token[:16]

    assert crypt.decrypt_info("hunter2", token[16:], salt) == b"hidden message"


def test_encrypt_info_uses_random_salt():
    first = crypt.encrypt_info("hunter2", b"hidden message")
    second = crypt.encrypt_info("hunter2", b"hidden message")

    assert first != second


def test_decrypt_embedded_info_ignores_decoded_host_trailing_bytes():
    token = crypt.encrypt_info("hunter2", b"hidden message")
    decoded_host_bytes = token + b"\x00\xffnot part of the token"

    assert crypt.decrypt_embedded_info("hunter2", decoded_host_bytes) == b"hidden message"
