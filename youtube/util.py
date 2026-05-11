import base64
import hashlib
import typing

from common.default import DEFAULT


def with_default[T](cls, factory: typing.Callable[[], T]) -> T:
    value = cls._DEFAULT
    if value is DEFAULT:
        cls._DEFAULT = value = factory()
    return value


def simple_hash(url: str):
    sha_hash = hashlib.blake2b(url.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha_hash[:16]).rstrip(b'=').decode('utf-8')
