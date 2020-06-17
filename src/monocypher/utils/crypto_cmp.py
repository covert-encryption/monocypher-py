from monocypher.utils import ensure_bytes_with_length
from monocypher._monocypher import lib


def crypto_verify16(a, b):
    ensure_bytes_with_length('a', a, 16)
    ensure_bytes_with_length('b', b, 16)

    rv = lib.crypto_verify16(a, b)
    return bool(rv == 0)


def crypto_verify32(a, b):
    ensure_bytes_with_length('a', a, 32)
    ensure_bytes_with_length('b', b, 32)

    rv = lib.crypto_verify32(a, b)
    return bool(rv == 0)


def crypto_verify64(a, b):
    ensure_bytes_with_length('a', a, 64)
    ensure_bytes_with_length('b', b, 64)

    rv = lib.crypto_verify64(a, b)
    return bool(rv == 0)
