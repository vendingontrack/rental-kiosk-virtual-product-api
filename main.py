"""
Virtual Product Mock Server

A FastAPI server implementing the external virtual product API contract
defined in SD-3708. Used for development and Go integration testing.

Configurable via environment variables:
    API_KEY           - Expected X-API-Key value (default: "test-api-key")
    DATA_FILE         - Path to JSON file with product data (default: examples/golf.json)
    PORT              - Server port (default: 8099)
    RESPONSE_DELAY_MS - Artificial delay in ms on responses except /ping (default: 0)
    FAIL_PURCHASE     - When "true", POST /purchase always returns failure

Or via command-line argument:
    python main.py [path/to/data.json]
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY: str = os.getenv("API_KEY", "test-api-key")
PORT: int = int(os.getenv("PORT", "8099"))
RESPONSE_DELAY_MS: int = int(os.getenv("RESPONSE_DELAY_MS", "0"))
FAIL_PURCHASE: bool = os.getenv("FAIL_PURCHASE", "false").lower() == "true"

# Resolve data file path from command-line arg or environment
_data_file: Optional[str] = None
if len(sys.argv) > 1:
    _data_file = sys.argv[1]
else:
    _data_file = os.getenv("DATA_FILE", "examples/golf.json")

# Convert to absolute path if relative
DATA_FILE: Path = Path(_data_file)
if not DATA_FILE.is_absolute():
    DATA_FILE = Path(__file__).parent / DATA_FILE

# Load product data from JSON file
def _load_product_data() -> dict:
    """Load product data from the configured JSON file."""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger = logging.getLogger("mock-server")
        logger.error(f"Product data file not found: {DATA_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger = logging.getLogger("mock-server")
        logger.error(f"Invalid JSON in {DATA_FILE}: {e}")
        sys.exit(1)

# ---------------------------------------------------------------------------
# Logging  (stdout so Go test runner can capture)
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [mock-server] %(levelname)s %(message)s",
)
logger = logging.getLogger("mock-server")


# Product data will be loaded at runtime
_product_data_cache: Optional[dict] = None

def _build_sku_index(preset_data: dict) -> dict:
    """Return {sku: variant_dict} for quick validation."""
    index: dict = {}
    for cat in preset_data.get("categories", []):
        for variant in cat.get("variants", []):
            index[variant["sku"]] = variant
    return index


def _get_product_data() -> dict:
    """Get product data, loading from file on first call and caching."""
    global _product_data_cache
    if _product_data_cache is None:
        _product_data_cache = _load_product_data()
    return _product_data_cache


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PurchaseRequest(BaseModel):
    sku: str
    customer_identifier: str
    transaction_id: str
    amount_paid_in_cents: int


class PurchaseResponse(BaseModel):
    confirmation_id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Virtual Product Mock Server", version="1.0.0")

# Track transaction_ids for idempotency
_transaction_results: dict[str, PurchaseResponse] = {}


# ---------------------------------------------------------------------------
# Middleware: optional artificial delay
# ---------------------------------------------------------------------------


@app.middleware("http")
async def delay_middleware(request: Request, call_next):
    # Skip delay for /ping so the health-check used by StartMockServer isn't blocked.
    if RESPONSE_DELAY_MS > 0 and request.url.path != "/ping":
        await asyncio.sleep(RESPONSE_DELAY_MS / 1000.0)
    response = await call_next(request)
    return response


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def _validate_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return x_api_key


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/ping")
async def ping(x_api_key: Optional[str] = Header(None)):
    _validate_api_key(x_api_key)
    return {"status": "ok"}


@app.get("/products")
async def list_products(x_api_key: Optional[str] = Header(None)):
    _validate_api_key(x_api_key)
    return JSONResponse(content=_get_product_data())


@app.post("/purchase", response_model=PurchaseResponse)
async def purchase(
    body: PurchaseRequest,
    x_api_key: Optional[str] = Header(None),
):
    _validate_api_key(x_api_key)

    logger.info(
        "Purchase request: sku=%s customer=%s txn=%s amount=%d",
        body.sku,
        body.customer_identifier,
        body.transaction_id,
        body.amount_paid_in_cents,
    )

    # Idempotency: return cached result for repeated transaction_id
    if body.transaction_id in _transaction_results:
        logger.info(
            "Returning cached result for transaction_id=%s",
            body.transaction_id,
        )
        cached = _transaction_results[body.transaction_id]
        return cached

    # Check FAIL_PURCHASE toggle
    if FAIL_PURCHASE:
        result = PurchaseResponse(
            confirmation_id="",
            status="failed",
            message="Purchase rejected",
        )
        _transaction_results[body.transaction_id] = result
        return result

    # Validate SKU exists in current preset
    sku_index = _build_sku_index(_get_product_data())
    if body.sku not in sku_index:
        result = PurchaseResponse(
            confirmation_id="",
            status="failed",
            message=f"Unknown SKU: {body.sku}",
        )
        _transaction_results[body.transaction_id] = result
        return result

    # Success
    confirmation_id = f"MOCK-{uuid.uuid4()}"
    result = PurchaseResponse(
        confirmation_id=confirmation_id,
        status="confirmed",
        message="Booking confirmed",
    )
    _transaction_results[body.transaction_id] = result

    logger.info(
        "Purchase confirmed: confirmation_id=%s txn=%s",
        confirmation_id,
        body.transaction_id,
    )
    return result


# ---------------------------------------------------------------------------
# Entry point (for subprocess usage: python main.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(
        "Starting mock server on port %d (data_file=%s)",
        PORT,
        DATA_FILE,
    )
    logger.info(
        "Config: API_KEY=%s RESPONSE_DELAY_MS=%d FAIL_PURCHASE=%s",
        API_KEY,
        RESPONSE_DELAY_MS,
        FAIL_PURCHASE,
    )
    # Validate data file can be loaded on startup
    _get_product_data()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
