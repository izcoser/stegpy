from stegpy import crypt


def test_encrypt_and_decrypt_round_trip():
    token = crypt.encrypt_info("hunter2", b"hidden message")
    salt = token[:16]

    assert crypt.decrypt_info("hunter2", token[16:], salt) == b"hidden message"


def test_encrypt_info_uses_random_salt():
    first = crypt.encrypt_info("hunter2", b"hidden message")
    second = crypt.encrypt_info("hunter2", b"hidden message")

    assert first != second


def test_encrypted_info_size_matches_fernet_output():
    for info_length in [0, 1, 15, 16, 17, 100, 245, 246]:
        encrypted = crypt.encrypt_info("hunter2", b"x" * info_length)

        assert crypt.encrypted_info_size(info_length) == len(encrypted)


def test_decrypt_embedded_info_ignores_decoded_host_trailing_bytes():
    token = crypt.encrypt_info("hunter2", b"hidden message")
    decoded_host_bytes = token + b"\x00\xffnot part of the token"

    assert crypt.decrypt_embedded_info("hunter2", decoded_host_bytes) == b"hidden message"
