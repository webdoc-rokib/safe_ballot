import os
import binascii
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

load_dotenv()

def _get_key() -> bytes:
    hex_key = os.getenv('AES_KEY_HEX')
    if not hex_key:
        raise RuntimeError(
            'AES_KEY_HEX must be set in the environment (e.g. in .env) and be a 64-character hex string (32 bytes)'
        )
    try:
        key = binascii.unhexlify(hex_key)
        if len(key) != 32:
            raise RuntimeError('AES_KEY_HEX must decode to 32 bytes (256 bits)')
        return key
    except (binascii.Error, TypeError) as e:
        raise RuntimeError('AES_KEY_HEX must be a valid hex string representing 32 bytes') from e

def encrypt_vote(plaintext: str, associated_data: str | None = None) -> str:
    key = _get_key()
    # AES-GCM authenticated encryption with 96-bit (12 byte) nonce
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    aad = associated_data.encode('utf-8') if associated_data is not None else None
    ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), aad)
    # store nonce + ciphertext (ciphertext includes tag)
    return binascii.hexlify(nonce + ct).decode('ascii')

def decrypt_vote(hex_ciphertext: str, associated_data: str | None = None) -> str:
    key = _get_key()
    data = binascii.unhexlify(hex_ciphertext)
    nonce = data[:12]
    ct = data[12:]
    aesgcm = AESGCM(key)
    aad = associated_data.encode('utf-8') if associated_data is not None else None
    plaintext = aesgcm.decrypt(nonce, ct, aad)
    return plaintext.decode('utf-8')
