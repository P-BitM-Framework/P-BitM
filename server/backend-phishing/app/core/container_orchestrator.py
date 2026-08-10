"""Call the admin-owned, campaign-scoped container lifecycle API."""

import httpx

from config import settings


def _headers() -> dict[str, str]:
    return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}


def _url(victim_id: str) -> str:
    return (
        f"{settings.ADMIN_API_URL.rstrip('/')}/api/campaigns/"
        f"{settings.CAMPAIGN_ID}"
        f"/internal/victims/{victim_id}/container"
    )


async def create_victim_container(
    victim_id: str,
    user_agent: str,
    theme: str,
    campaign_host: str,
) -> dict:
    async with httpx.AsyncClient(timeout=settings.WS_SESSION_STARTUP_TIMEOUT_SECONDS) as client:
        response = await client.post(
            _url(victim_id),
            headers=_headers(),
            json={
                "user_agent": user_agent,
                "theme": theme,
            },
        )
        response.raise_for_status()
        return response.json()


async def dump_victim_container(victim_id: str) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{_url(victim_id)}/dump",
            headers=_headers(),
        )
        response.raise_for_status()


async def destroy_victim_container(victim_id: str) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.delete(
            _url(victim_id),
            headers=_headers(),
        )
        response.raise_for_status()
