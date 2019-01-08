#!/usr/bin/env python3
# Module for encrypting byte arrays.

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def derive_key(password):
    kdf = PBKDF2HMAC(
         algorithm=hashes.SHA256(),
         length=32,
         salt=bytes(('whatever').encode('utf-8')),
         iterations=100000,
         backend=default_backend()
     )

    return base64.urlsafe_b64encode(kdf.derive(password))

def encrypt_info(password, info):
    ''' Receives a password and a byte array. Returns a Fernet token. '''
    password = bytes((password).encode('utf-8'))
    key = derive_key(password)
    f = Fernet(key)
    token = f.encrypt(info)
    return token

def decrypt_info(password, token):
    ''' Receives a password and a Fernet token. Returns a byte array. '''
    password = bytes((password).encode('utf-8'))
    key = derive_key(password)
    f = Fernet(key)
    info = f.decrypt(token)
    return info
