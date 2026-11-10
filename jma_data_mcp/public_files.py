"""Read bounded data files from JMA's published download endpoints."""

import httpx


async def fetch_public_file(url: str, max_bytes: int) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            data = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ValueError("JMA download exceeds the configured size limit")
    return bytes(data)
