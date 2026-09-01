"""NEPSE authentication and payload ID generation.

Adapted from YONEPSE official_api/auth.py.

Handles:
- WASM-based token parsing (access/refresh token decoding from salts)
- Payload ID calculation for POST endpoints (date-sensitive)
"""

import logging
import os
from datetime import datetime
from typing import Any

from wasmtime import Instance, Module, Store

logger = logging.getLogger(__name__)

WASM_FILE = os.path.join(os.path.dirname(__file__), "nepse.wasm")

# Lookup table for payload ID generation. Verified from YONEPSE upstream.
_PAYLOAD_TABLE: list[int] = [
    147, 117, 239, 143, 157, 312, 161, 612, 512, 804, 411, 527, 170, 511, 421, 667, 764, 621,
    301, 106, 133, 793, 411, 511, 312, 423, 344, 346, 653, 758, 342, 222, 236, 811, 711, 611,
    122, 447, 128, 199, 183, 135, 489, 703, 800, 745, 152, 863, 134, 211, 142, 564, 375, 793,
    212, 153, 138, 153, 648, 611, 151, 649, 318, 143, 117, 756, 119, 141, 717, 113, 112, 146,
    162, 660, 693, 261, 362, 354, 251, 641, 157, 178, 631, 192, 734, 445, 192, 883, 187, 122,
    591, 731, 852, 384, 565, 596, 451, 772, 624, 691,
]


class TokenParser:
    """Parse NEPSE access/refresh tokens using WASM functions.

    The NEPSE API obfuscates tokens using salts returned during authentication.
    The WASM module decodes the real tokens from these salts.
    """

    def __init__(self) -> None:
        self._store = Store()
        module = Module.from_file(self._store.engine, WASM_FILE)
        instance = Instance(self._store, module, [])

        self._cdx = instance.exports(self._store)["cdx"]
        self._rdx = instance.exports(self._store)["rdx"]
        self._bdx = instance.exports(self._store)["bdx"]
        self._ndx = instance.exports(self._store)["ndx"]
        self._mdx = instance.exports(self._store)["mdx"]
        logger.debug("TokenParser initialized with WASM module.")

    def parse_token_response(self, token_response: dict[str, Any]) -> tuple[str, str]:
        """Parse access and refresh tokens from the auth response.

        Args:
            token_response: Raw response from /api/authenticate/prove containing
                accessToken, refreshToken, and salt1-salt5.

        Returns:
            Tuple of (parsed_access_token, parsed_refresh_token).
        """
        salt1 = token_response["salt1"]
        salt2 = token_response["salt2"]
        salt3 = token_response["salt3"]
        salt4 = token_response["salt4"]
        salt5 = token_response["salt5"]

        # Compute indices for access token
        n = self._cdx(self._store, salt1, salt2, salt3, salt4, salt5)
        l = self._rdx(self._store, salt1, salt2, salt4, salt3, salt5)  # noqa: E741
        o = self._bdx(self._store, salt1, salt2, salt4, salt3, salt5)
        p = self._ndx(self._store, salt1, salt2, salt4, salt3, salt5)
        q = self._mdx(self._store, salt1, salt2, salt4, salt3, salt5)

        # Compute indices for refresh token
        i = self._cdx(self._store, salt2, salt1, salt3, salt5, salt4)
        r = self._rdx(self._store, salt2, salt1, salt3, salt4, salt5)
        s = self._bdx(self._store, salt2, salt1, salt4, salt3, salt5)
        t = self._ndx(self._store, salt2, salt1, salt4, salt3, salt5)
        u = self._mdx(self._store, salt2, salt1, salt4, salt3, salt5)

        access_token: str = token_response["accessToken"]
        refresh_token: str = token_response["refreshToken"]

        parsed_access = (
            access_token[0:n]
            + access_token[n + 1 : l]
            + access_token[l + 1 : o]
            + access_token[o + 1 : p]
            + access_token[p + 1 : q]
            + access_token[q + 1 :]
        )
        parsed_refresh = (
            refresh_token[0:i]
            + refresh_token[i + 1 : r]
            + refresh_token[r + 1 : s]
            + refresh_token[s + 1 : t]
            + refresh_token[t + 1 : u]
            + refresh_token[u + 1 :]
        )

        logger.debug("Successfully parsed access and refresh tokens.")
        return parsed_access, parsed_refresh


def calculate_payload_id(
    market_open_id: int,
    token_details: dict[str, Any],
    payload_type: str,
    today: int | None = None,
) -> int:
    """Calculate payload ID for POST endpoints.

    The NEPSE API requires a calculated payload ID in POST request bodies.
    This ID depends on the market-open ID, token salts, and the current day.

    Args:
        market_open_id: The 'id' field from /api/nots/nepse-data/market-open.
        token_details: The full token response dict (with salt1-salt5).
        payload_type: One of 'stock-live', 'sector-live', or 'default'.
        today: Override for datetime.now().day (used in tests).

    Returns:
        The calculated payload ID.
    """
    if today is None:
        today = datetime.now().day

    payload_id = _PAYLOAD_TABLE[market_open_id] + market_open_id + 2 * today

    if payload_type == "stock-live":
        return payload_id

    if payload_type == "sector-live":
        index_value = 3 if payload_id % 10 < 5 else 1
    else:
        index_value = 1 if payload_id % 10 < 5 else 3

    payload_id = (
        payload_id
        + token_details.get(f"salt{index_value + 1}", 0) * today
        - token_details.get(f"salt{index_value}", 0)
    )

    return payload_id
