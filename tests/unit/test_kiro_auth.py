from __future__ import annotations

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer, TestClient

from app.modules.accounts.kiro_auth import (
    KiroRefreshError,
    KiroRefreshInput,
    KiroRefreshResult,
    refresh_kiro_token,
)

pytestmark = pytest.mark.unit


async def test_refresh_kiro_oidc_token_posts_to_region_oidc():
    seen: dict[str, object] = {}

    async def handler(request: web.Request) -> web.Response:
        seen["payload"] = await request.json()
        return web.json_response(
            {
                "accessToken": "new-access",
                "refreshToken": "new-refresh",
                "expiresIn": 3600,
                "profileArn": "arn:new",
            }
        )

    app = web.Application()
    app.router.add_post("/token", handler)

    async with TestClient(TestServer(app)) as client:
        base_url = str(client.make_url(""))
        result = await refresh_kiro_token(
            KiroRefreshInput(
                auth_method="idc",
                refresh_token="old-refresh",
                client_id="client-id",
                client_secret="client-secret",
                region="us-east-1",
                social_refresh_base_url=None,
                oidc_base_url=base_url,
            )
        )

    assert result.access_token == "new-access"
    assert result.refresh_token == "new-refresh"
    assert result.profile_arn == "arn:new"
    assert seen["payload"]["grantType"] == "refresh_token"  # type: ignore[index]


async def test_refresh_kiro_social_token_posts_to_social_endpoint():
    seen: dict[str, object] = {}

    async def handler(request: web.Request) -> web.Response:
        seen["payload"] = await request.json()
        return web.json_response(
            {
                "accessToken": "social-access",
                "refreshToken": "social-refresh",
                "expiresIn": 7200,
            }
        )

    app = web.Application()
    app.router.add_post("/refreshToken", handler)

    async with TestClient(TestServer(app)) as client:
        base_url = str(client.make_url(""))
        result = await refresh_kiro_token(
            KiroRefreshInput(
                auth_method="social",
                refresh_token="old-social-refresh",
                social_refresh_base_url=base_url,
            )
        )

    assert result.access_token == "social-access"
    assert seen["payload"]["refreshToken"] == "old-social-refresh"  # type: ignore[index]


async def test_refresh_kiro_oidc_missing_credentials_raises_permanent():
    with pytest.raises(KiroRefreshError) as exc_info:
        await refresh_kiro_token(
            KiroRefreshInput(
                auth_method="idc",
                refresh_token="tok",
                client_id=None,
                client_secret=None,
            )
        )
    assert exc_info.value.permanent is True


async def test_refresh_kiro_http_error_marks_permanent_on_401():
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=401, text="Unauthorized")

    app = web.Application()
    app.router.add_post("/token", handler)

    async with TestClient(TestServer(app)) as client:
        base_url = str(client.make_url(""))
        with pytest.raises(KiroRefreshError) as exc_info:
            await refresh_kiro_token(
                KiroRefreshInput(
                    auth_method="idc",
                    refresh_token="tok",
                    client_id="cid",
                    client_secret="csec",
                    oidc_base_url=base_url,
                )
            )
    assert exc_info.value.permanent is True


async def test_refresh_kiro_http_500_marks_non_permanent():
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=500, text="Internal Server Error")

    app = web.Application()
    app.router.add_post("/token", handler)

    async with TestClient(TestServer(app)) as client:
        base_url = str(client.make_url(""))
        with pytest.raises(KiroRefreshError) as exc_info:
            await refresh_kiro_token(
                KiroRefreshInput(
                    auth_method="idc",
                    refresh_token="tok",
                    client_id="cid",
                    client_secret="csec",
                    oidc_base_url=base_url,
                )
            )
    assert exc_info.value.permanent is False
