"""Tiny REST surface — health for ops, board/drivers for deep links.

The WebSocket is the product; REST exists for curl-ability and the frontend's
"view driver source" panel (driver_code rides /api/drivers on purpose — the
registry stores exactly the text that passed on silicon, and showing it is
part of the honesty story).
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

import selfaware
from selfaware.api.state import AppState

router = APIRouter()


def _state(request: Request) -> AppState:
    return request.app.state.selfaware


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": selfaware.__version__}


@router.get("/api/board")
async def board(request: Request) -> dict[str, Any]:
    return _state(request).session.board_status().model_dump(mode="json")


@router.get("/api/drivers")
async def drivers(request: Request) -> list[dict[str, Any]]:
    """Every registered driver, INCLUDING driver_code (see module docstring)."""
    return [record.model_dump(mode="json") for record in _state(request).registry.list()]


@router.get("/api/drivers/{slug}")
async def driver(request: Request, slug: str) -> dict[str, Any]:
    record = _state(request).registry.get(slug)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no driver registered for {slug!r}")
    return record.model_dump(mode="json")
