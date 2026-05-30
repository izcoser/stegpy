from stegpy import crypt


def test_encrypt_and_decrypt_round_trip():
    token = crypt.encrypt_info("hunter2", b"hidden message")
    salt = token[:16]

    assert crypt.decrypt_info("hunter2", token[16:], salt) == b"hidden message"


def test_encrypt_info_uses_random_salt():
    first = crypt.encrypt_info("hunter2", b"hidden message")
    second = crypt.encrypt_info("hunter2", b"hidden message")

    assert first != second
