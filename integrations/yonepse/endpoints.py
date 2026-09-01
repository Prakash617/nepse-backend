"""YONEPSE static-data endpoint URLs.

All paths are relative to the GitHub Pages base URL.
Canonical folder-based endpoints (not legacy paths).
"""

BASE_URL = "https://shubhamnpk.github.io/yonepse"

# Reference / metadata
ALL_SECURITIES = f"{BASE_URL}/data/all_securities.json"
INDICES = f"{BASE_URL}/data/indices.json"
SECTOR_INDICES = f"{BASE_URL}/data/sector_indices.json"

# Market
MARKET_HISTORY = f"{BASE_URL}/data/market/history.json"
MARKET_SUMMARY = f"{BASE_URL}/data/market/summary.json"
MARKET_STATUS = f"{BASE_URL}/data/market/status.json"

# LTP history
LTP_MANIFEST = f"{BASE_URL}/data/ltp/manifest.json"
LTP_MONTHLY_TEMPLATE = f"{BASE_URL}/data/ltp/monthly/{{month}}.json"
LTP_DAILY_TEMPLATE = f"{BASE_URL}/data/ltp/daily/{{date}}.json"

# Company / fundamentals
COMPANY_PROFILES = f"{BASE_URL}/data/company/profiles.json"
COMPANY_FINANCIALS = f"{BASE_URL}/data/company/financials.json"

# IPO
IPO_OLD = f"{BASE_URL}/data/ipo/old.json"
IPO_UPCOMING = f"{BASE_URL}/data/ipo/upcoming.json"

# Dividends
PROPOSED_DIVIDEND_LATEST = f"{BASE_URL}/data/proposed_dividend/latest_1y.json"
PROPOSED_DIVIDEND_HISTORY = f"{BASE_URL}/data/proposed_dividend/history_all_years.json"
