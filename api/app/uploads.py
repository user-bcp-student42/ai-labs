from __future__ import annotations

import hashlib
import re
from pathlib import Path

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
MAX_NAME_LENGTH = 128
ALLOWED_EXTENSIONS = frozenset({".txt", ".md"})
SAFE_NAME_PATTERN = re.compile(r"[A-Za-z0-9._ -]{1,%d}" % MAX_NAME_LENGTH)


class InvalidUploadError(Exception):
    """El nombre o la extensión del archivo no están permitidos."""


class UploadTooLargeError(Exception):
    """El archivo supera MAX_UPLOAD_BYTES."""


class DuplicateUploadError(Exception):
    """El usuario ya tiene un archivo con ese nombre."""


def safe_file_name(raw_name: str | None) -> str:
    name = Path(raw_name or "").name
    if not SAFE_NAME_PATTERN.fullmatch(name):
        raise InvalidUploadError(name)
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise InvalidUploadError(name)
    return name


def store_upload(upload_dir: str | Path, username: str, file_name: str, content: bytes) -> Path:
    user_directory_name = hashlib.sha256(username.encode("utf-8")).hexdigest()
    user_directory = Path(upload_dir) / user_directory_name
    user_directory.mkdir(parents=True, exist_ok=True)
    target = user_directory / file_name
    try:
        with target.open("xb") as uploaded_file:
            uploaded_file.write(content)
    except FileExistsError as error:
        raise DuplicateUploadError(file_name) from error
    return target


async def read_bounded(file: UploadFile) -> bytes:
    content = bytearray()
    while chunk := await file.read(READ_CHUNK_BYTES):
        content.extend(chunk)
        if len(content) > MAX_UPLOAD_BYTES:
            raise UploadTooLargeError()
    return bytes(content)
