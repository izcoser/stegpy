#!/usr/bin/env python3
# Module for encrypting byte arrays.

import base64
import os
import string
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key(password, salt=None):
    if not salt:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )

    return [base64.urlsafe_b64encode(kdf.derive(password)), salt]


def encrypt_info(password, info):
    """Receives a password and a byte array. Returns a Fernet token."""
    password = bytes((password).encode("utf-8"))
    key, salt = derive_key(password)
    f = Fernet(key)
    token = f.encrypt(info)
    return bytes(salt) + bytes(token)


def decrypt_info(password, token, salt):
    """Receives a password and a Fernet token. Returns a byte array."""
    password = bytes((password).encode("utf-8"))
    key = derive_key(password, salt)[0]
    f = Fernet(key)
    info = f.decrypt(token)
    return info


def fernet_token_lengths(token):
    """Yield plausible Fernet token boundaries inside decoded host bytes."""
    valid_token_bytes = set(
        (string.ascii_letters + string.digits + "-_=").encode("ascii")
    )
    max_end = 0
    for byte in token:
        if byte not in valid_token_bytes:
            break
        max_end += 1

    padding_index = token.find(b"=")
    if padding_index != -1:
        padding_end = padding_index + 1
        while padding_end < len(token) and token[padding_end] == ord("="):
            padding_end += 1
        if padding_end <= max_end:
            yield padding_end

    start = 4
    for end in range(start, max_end + 1):
        if end % 4 == 0:
            yield end


def decrypt_embedded_info(password, encrypted_info):
    """Decrypt a salt-prefixed Fernet token decoded from a host file."""
    salt = bytes(encrypted_info[:16])
    token = bytes(encrypted_info[16:])
    password = bytes((password).encode("utf-8"))
    key = derive_key(password, salt)[0]
    f = Fernet(key)
    last_error = None

    for end in dict.fromkeys(fernet_token_lengths(token)):
        try:
            return f.decrypt(token[:end])
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    return f.decrypt(token)
