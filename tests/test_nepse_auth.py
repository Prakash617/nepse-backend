"""Tests for NEPSE authentication and payload ID generation."""

from pathlib import Path

from integrations.nepse.auth import TokenParser, calculate_payload_id

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "nepse"


class TestTokenParser:
    """Tests for WASM-based token parsing."""

    def test_parse_token_response_returns_tuple(self) -> None:
        """TokenParser should return a (access_token, refresh_token) tuple."""
        parser = TokenParser()
        token_response = {
            "accessToken": "abcdefghijklmnopqrstuvwxyz",
            "refreshToken": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "salt1": 12345,
            "salt2": 67890,
            "salt3": 11111,
            "salt4": 22222,
            "salt5": 33333,
        }
        result = parser.parse_token_response(token_response)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_parse_token_response_deterministic(self) -> None:
        """TokenParser should produce the same output for the same input."""
        parser = TokenParser()
        token_response = {
            "accessToken": "abcdefghijklmnop",
            "refreshToken": "ABCDEFGHIJKLMNOP",
            "salt1": 100,
            "salt2": 200,
            "salt3": 300,
            "salt4": 400,
            "salt5": 500,
        }
        result1 = parser.parse_token_response(token_response)
        result2 = parser.parse_token_response(token_response)
        assert result1 == result2

    def test_parse_token_response_different_salts_different_output(self) -> None:
        """Different salt values should produce different token outputs."""
        parser = TokenParser()
        base = {
            "accessToken": "abcdefghijklmnopqrstuvwxyz0123456789",
            "refreshToken": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            "salt1": 100,
            "salt2": 200,
            "salt3": 300,
            "salt4": 400,
            "salt5": 500,
        }
        modified = base.copy()
        modified["salt1"] = 999
        modified["salt2"] = 888

        result1 = parser.parse_token_response(base)
        result2 = parser.parse_token_response(modified)
        # At least one of access or refresh tokens should differ
        assert result1 != result2, "Different salts should produce different token outputs"


class TestCalculatePayloadId:
    """Tests for payload ID calculation."""

    def test_stock_live_returns_base_payload(self) -> None:
        """stock-live payload should return the base calculation."""
        token_details = {"salt1": 100, "salt2": 200, "salt3": 300, "salt4": 400, "salt5": 500}
        result = calculate_payload_id(
            market_open_id=0,
            token_details=token_details,
            payload_type="stock-live",
            today=15,
        )
        # Base: _PAYLOAD_TABLE[0] + 0 + 2*15 = 147 + 0 + 30 = 177
        assert result == 177

    def test_sector_live_uses_salt_adjustment(self) -> None:
        """sector-live payload should apply salt-based adjustment."""
        token_details = {"salt1": 100, "salt2": 200, "salt3": 300, "salt4": 400, "salt5": 500}
        result = calculate_payload_id(
            market_open_id=0,
            token_details=token_details,
            payload_type="sector-live",
            today=15,
        )
        # Base: 147 + 0 + 30 = 177
        # 177 % 10 = 7, which is >= 5, so index_value = 1
        # Final: 177 + salt2 * 15 - salt1 = 177 + 200*15 - 100 = 177 + 3000 - 100 = 3077
        assert result == 3077

    def test_default_uses_salt_adjustment(self) -> None:
        """Default payload type should apply salt-based adjustment."""
        token_details = {"salt1": 100, "salt2": 200, "salt3": 300, "salt4": 400, "salt5": 500}
        result = calculate_payload_id(
            market_open_id=0,
            token_details=token_details,
            payload_type="default",
            today=15,
        )
        # Base: 147 + 0 + 30 = 177
        # 177 % 10 = 7, which is >= 5, so index_value = 3
        # Final: 177 + salt4 * 15 - salt3 = 177 + 400*15 - 300 = 177 + 6000 - 300 = 5877
        assert result == 5877

    def test_different_market_open_ids(self) -> None:
        """Different market_open_ids should produce different payloads."""
        token_details = {"salt1": 100, "salt2": 200, "salt3": 300, "salt4": 400, "salt5": 500}
        result1 = calculate_payload_id(0, token_details, "stock-live", today=15)
        result2 = calculate_payload_id(1, token_details, "stock-live", today=15)
        assert result1 != result2

    def test_different_days_produce_different_payloads(self) -> None:
        """Different days should produce different payloads."""
        token_details = {"salt1": 100, "salt2": 200, "salt3": 300, "salt4": 400, "salt5": 500}
        result1 = calculate_payload_id(0, token_details, "stock-live", today=15)
        result2 = calculate_payload_id(0, token_details, "stock-live", today=16)
        assert result1 != result2
