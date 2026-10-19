"""YONEPSE static-data endpoint URLs.

All paths are relative to the GitHub Pages base URL.
Canonical folder-based endpoints (not legacy paths).

Verified against https://github.com/Shubhamnpk/yonepse (main branch):
- securities list lives under data/other/
- index definitions live under data/market/
- index history is sharded monthly under data/indices/monthly/
- dividend history lives under data/dividend/
"""

BASE_URL = "https://shubhamnpk.github.io/yonepse"

# Reference / metadata
ALL_SECURITIES = f"{BASE_URL}/data/other/securities.json"
INDICES = f"{BASE_URL}/data/market/indices.json"
SECTOR_INDICES = f"{BASE_URL}/data/market/sector_indices.json"

# Market
MARKET_HISTORY = f"{BASE_URL}/data/market/history.json"
MARKET_SUMMARY = f"{BASE_URL}/data/market/summary.json"
MARKET_STATUS = f"{BASE_URL}/data/market/status.json"

# LTP history
LTP_MANIFEST = f"{BASE_URL}/data/ltp/manifest.json"
LTP_MONTHLY_TEMPLATE = f"{BASE_URL}/data/ltp/monthly/{{month}}.json"
LTP_DAILY_TEMPLATE = f"{BASE_URL}/data/ltp/daily/{{date}}.json"

# Index history
INDEX_MANIFEST = f"{BASE_URL}/data/indices/manifest.json"
INDEX_MONTHLY_TEMPLATE = f"{BASE_URL}/data/indices/monthly/{{month}}.json"

# Company / fundamentals
COMPANY_PROFILES = f"{BASE_URL}/data/company/profiles.json"
COMPANY_FINANCIALS = f"{BASE_URL}/data/company/financials.json"

# IPO
IPO_OLD = f"{BASE_URL}/data/ipo/old.json"
IPO_UPCOMING = f"{BASE_URL}/data/ipo/upcoming.json"

# Dividends
DIVIDEND_HISTORY = f"{BASE_URL}/data/dividend/history.json"
DIVIDEND_META = f"{BASE_URL}/data/dividend/meta.json"

# Backwards-compatible aliases (legacy names)
PROPOSED_DIVIDEND_LATEST = DIVIDEND_HISTORY
PROPOSED_DIVIDEND_HISTORY = DIVIDEND_HISTORY
