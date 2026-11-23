#!/usr/bin/env python3
"""Authenticated browser dashboard for precious-metals prices."""

from __future__ import annotations

import argparse
import asyncio
import hmac
import logging
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from get_gold_silver_comexlive import get_gold_silver
from get_gold_silver_moneycontrol import get_gold_price, get_silver_price
from get_usdinr_moneycontrol import get_usdinr
from gold_price_converter import (
    add_duty_and_gst as gold_duty_gst,
    convert_gold_price_usd_oz_to_inr_10g,
)
from silver_price_converter import (
    add_duty_and_gst as silver_duty_gst,
    convert_silver_price_usd_oz_to_inr_kg,
)


_BASE_DIR = Path(__file__).resolve().parent
_TEMPLATE = _BASE_DIR / "templates" / "precious_metals_dashboard.html"
_LOGIN_TEMPLATE = _BASE_DIR / "templates" / "precious_metals_login.html"
_logger = logging.getLogger(__name__)
_data_cache: dict[str, Any] | None = None
_refresh_lock = asyncio.Lock()
_session_secret = os.environ.get("PRECIOUS_DASHBOARD_SECRET_KEY") or secrets.token_urlsafe(48)

api = FastAPI(title="Precious Metals Dashboard", version="1.0.0")
api.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    session_cookie="precious_metals_session",
    max_age=8 * 60 * 60,
    same_site="strict",
    https_only=os.environ.get("PRECIOUS_DASHBOARD_COOKIE_SECURE", "0").lower()
    in {"1", "true", "yes"},
)


def _read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def _fetch_one(name: str, fetcher: Callable[[], Any]) -> tuple[str, Any, str | None]:
    try:
        return name, _serialize(fetcher()), None
    except Exception as error:
        _logger.warning("Could not fetch %s: %s", name, error)
        return name, None, str(error)


def collect_dashboard_data() -> dict[str, Any]:
    """Fetch sources concurrently and prepare values for the browser UI."""
    jobs: tuple[tuple[str, Callable[[], Any]], ...] = (
        ("comex", get_gold_silver),
        ("usdinr", get_usdinr),
        ("mcx_gold", get_gold_price),
        ("mcx_silver", get_silver_price),
    )
    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        results = list(executor.map(lambda item: _fetch_one(*item), jobs))

    values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, value, error in results:
        if error:
            errors[name] = error
        values[name] = value

    comex = values.get("comex")
    gold_comex, silver_comex = comex if comex else (None, None)
    usdinr = values.get("usdinr")
    rate = usdinr.rate if usdinr else None

    prices: dict[str, float | None] = {
        "gold_comex_inr": None,
        "gold_comex_after_tax": None,
        "silver_comex_inr": None,
        "silver_comex_after_tax": None,
    }
    if rate is not None and gold_comex is not None:
        gold_inr = convert_gold_price_usd_oz_to_inr_10g(gold_comex.last, rate, use_troy=True)
        prices["gold_comex_inr"] = gold_inr
        prices["gold_comex_after_tax"] = gold_duty_gst(gold_inr)
    if rate is not None and silver_comex is not None:
        silver_inr = convert_silver_price_usd_oz_to_inr_kg(silver_comex.last, rate, use_troy=True)
        prices["silver_comex_inr"] = silver_inr
        prices["silver_comex_after_tax"] = silver_duty_gst(silver_inr)

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "usdinr": _serialize(usdinr) if usdinr else None,
        "gold_comex": _serialize(gold_comex) if gold_comex else None,
        "silver_comex": _serialize(silver_comex) if silver_comex else None,
        "mcx_gold": values.get("mcx_gold"),
        "mcx_silver": values.get("mcx_silver"),
        "prices": prices,
        "errors": errors,
    }


async def _refresh_data() -> dict[str, Any]:
    global _data_cache
    async with _refresh_lock:
        payload = await asyncio.to_thread(collect_dashboard_data)
        _data_cache = payload
        return payload


def _is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True


def _credentials_configured() -> bool:
    return bool(os.environ.get("PRECIOUS_DASHBOARD_USERNAME")) and bool(
        os.environ.get("PRECIOUS_DASHBOARD_PASSWORD")
    )


def _login_page(error: str = "") -> HTMLResponse:
    page = _read_template(_LOGIN_TEMPLATE)
    page = page.replace("{{ERROR}}", error)
    return HTMLResponse(page)


@api.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _is_authenticated(request):
        return RedirectResponse("/", status_code=303)
    if not _credentials_configured():
        return HTMLResponse(
            "Set PRECIOUS_DASHBOARD_USERNAME and PRECIOUS_DASHBOARD_PASSWORD "
            "before using the dashboard.",
            status_code=503,
        )
    return _login_page()


@api.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    expected_username = os.environ.get("PRECIOUS_DASHBOARD_USERNAME", "")
    expected_password = os.environ.get("PRECIOUS_DASHBOARD_PASSWORD", "")
    username_ok = hmac.compare_digest(username, expected_username)
    password_ok = hmac.compare_digest(password, expected_password)
    if not _credentials_configured() or not (username_ok and password_ok):
        return _login_page("The username or password was not accepted.")
    request.session.clear()
    request.session["authenticated"] = True
    return RedirectResponse("/", status_code=303)


@api.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@api.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_read_template(_TEMPLATE))


@api.get("/api/data")
async def get_dashboard_data(request: Request) -> dict[str, Any]:
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Sign in to view dashboard data")
    if _data_cache is not None:
        return _data_cache
    try:
        return await _refresh_data()
    except Exception as error:
        _logger.exception("Initial precious-metals data fetch failed")
        raise HTTPException(status_code=503, detail=f"Could not fetch market data: {error}") from error


@api.post("/api/refresh")
async def refresh_dashboard_data(request: Request) -> dict[str, Any]:
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Sign in to refresh dashboard data")
    try:
        return await _refresh_data()
    except Exception as error:
        _logger.exception("Precious-metals refresh failed")
        raise HTTPException(status_code=503, detail=f"Could not refresh market data: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Precious-metals browser dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Web server host")
    parser.add_argument("--port", type=int, default=8002, help="Web server port")
    parser.add_argument(
        "--reload", action="store_true", help="Enable development auto-reload"
    )
    args = parser.parse_args()

    if not _credentials_configured():
        parser.error(
            "set PRECIOUS_DASHBOARD_USERNAME and PRECIOUS_DASHBOARD_PASSWORD first"
        )
    if not os.environ.get("PRECIOUS_DASHBOARD_SECRET_KEY"):
        _logger.warning(
            "PRECIOUS_DASHBOARD_SECRET_KEY is unset; sessions will not survive a server restart"
        )
    uvicorn.run("precious_metals_dashboard:api", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
