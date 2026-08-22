from __future__ import annotations

import httpx


class SourceFetchError(RuntimeError):
    pass


def download_bytes(url: str, *, timeout: float = 120, headers: dict | None = None) -> bytes:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers or {"User-Agent": "VeriFinder/1.0"}) as client:
            response = client.get(url)
        if response.is_error:
            raise SourceFetchError(f"{url} returned HTTP {response.status_code}")
        return response.content
    except httpx.HTTPError as error:
        raise SourceFetchError(f"{url} could not be reached: {error}") from error
