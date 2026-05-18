from __future__ import annotations

from dataclasses import dataclass
from time import time

import aiohttp


@dataclass(frozen=True)
class KiroRefreshInput:
    auth_method: str
    refresh_token: str
    client_id: str | None = None
    client_secret: str | None = None
    region: str | None = None
    social_refresh_base_url: str | None = None
    oidc_base_url: str | None = None


@dataclass(frozen=True)
class KiroRefreshResult:
    access_token: str
    refresh_token: str
    expires_at: int
    profile_arn: str | None = None


class KiroRefreshError(Exception):
    def __init__(self, message: str, *, permanent: bool = False) -> None:
        super().__init__(message)
        self.permanent = permanent


async def refresh_kiro_token(data: KiroRefreshInput) -> KiroRefreshResult:
    auth_method = data.auth_method.lower().strip()
    if auth_method == "social":
        base = (data.social_refresh_base_url or "https://prod.us-east-1.auth.desktop.kiro.dev").rstrip("/")
        url = f"{base}/refreshToken"
        payload: dict[str, str] = {"refreshToken": data.refresh_token}
    else:
        if not data.client_id or not data.client_secret:
            raise KiroRefreshError("Kiro OIDC refresh requires client id and client secret", permanent=True)
        region = data.region or "us-east-1"
        base = (data.oidc_base_url or f"https://oidc.{region}.amazonaws.com").rstrip("/")
        url = f"{base}/token"
        payload = {
            "clientId": data.client_id,
            "clientSecret": data.client_secret,
            "refreshToken": data.refresh_token,
            "grantType": "refresh_token",
        }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status >= 400:
                body: dict[str, object] = {}
                try:
                    body = await response.json(content_type=None)
                except Exception:
                    pass
                raise KiroRefreshError(
                    f"Kiro refresh failed: HTTP {response.status}",
                    permanent=response.status in {400, 401, 403},
                )
            body = await response.json(content_type=None)
    access_token = str(body.get("accessToken") or "")
    new_refresh_token = str(body.get("refreshToken") or data.refresh_token)
    expires_in = int(body.get("expiresIn") or 0)
    if not access_token or expires_in <= 0:
        raise KiroRefreshError("Kiro refresh response missing access token or expiry", permanent=False)
    return KiroRefreshResult(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_at=int(time()) + expires_in,
        profile_arn=str(body["profileArn"]) if body.get("profileArn") else None,
    )
