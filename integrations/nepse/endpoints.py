"""NEPSE API endpoint definitions.

All endpoints verified from YONEPSE official_api/endpoints.py.
See docs/nepse-integration.md for details.
"""


DEFAULT_BASE_URL = "https://www.nepalstock.com"

ENDPOINTS: dict[str, dict[str, str]] = {
    # Authentication
    "authenticate_api": {"api": "/api/authenticate/prove", "method": "GET"},
    # Market data
    "marketopen_api": {"api": "/api/nots/nepse-data/market-open", "method": "GET"},
    "today_price_api": {"api": "/api/nots/nepse-data/today-price", "method": "POST"},
    "market_summary_api": {"api": "/api/nots/market-summary", "method": "GET"},
    "market_summary_history_api": {"api": "/api/nots/market-summary-history", "method": "GET"},
    "marketcap_api": {"api": "/api/nots/nepse-data/marcapbydate", "method": "GET"},
    "trading_average_api": {"api": "/api/nots/nepse-data/trading-average", "method": "GET"},
    "supply_demand_api": {"api": "/api/nots/nepse-data/supplydemand", "method": "GET"},
    "stock_live_api": {"api": "/api/nots/lives-market", "method": "GET"},
    # Securities
    "security_api": {"api": "/api/nots/company/list", "method": "GET"},
    "securities_list_api": {"api": "/api/nots/securities", "method": "GET"},
    "ticker_info_api": {"api": "/api/nots/security", "method": "POST"},
    "ticker_contact_api": {"api": "/api/nots/security/profile", "method": "GET"},
    "ticker_price_api": {"api": "/api/nots/market/security/price", "method": "GET"},
    "security_daily_trade_stat_api": {"api": "/api/nots/securityDailyTradeStat", "method": "GET"},
    # Indices
    "nepse_index_api": {"api": "/api/nots/nepse-index", "method": "GET"},
    "sector_index_api": {"api": "/api/nots/index", "method": "GET"},
    "head_indices_api": {"api": "/api/nots/index/history", "method": "GET"},
    "indices_live_api": {"api": "/api/nots/graph/index", "method": "POST"},
    # Sectors
    "sector_api": {"api": "/api/nots/sector", "method": "GET"},
    "sectorwise_summary_api": {"api": "/api/nots/sectorwise", "method": "GET"},
    # Top stocks
    "top_gainer": {"api": "/api/nots/top-ten/top-gainer", "method": "GET"},
    "top_loser": {"api": "/api/nots/top-ten/top-loser", "method": "GET"},
    "top_turnover": {"api": "/api/nots/top-ten/turnover", "method": "GET"},
    "top_trade": {"api": "/api/nots/top-ten/trade", "method": "GET"},
    "top_transaction": {"api": "/api/nots/top-ten/transaction", "method": "GET"},
    "top_trade_qty_api": {"api": "/api/nots/top-ten/trade-qty", "method": "GET"},
    # Company
    "company_financials_api": {"api": "/api/nots/application/reports", "method": "GET"},
    # Brokers
    "broker_api": {"api": "/api/nots/member", "method": "POST"},
    # News
    "disclosure": {"api": "/api/nots/news/companies/disclosure", "method": "GET"},
    "notice_api": {"api": "/api/web/notice/", "method": "GET"},
    "info_officer_api": {"api": "/api/web/info-officer", "method": "GET"},
}

# Valid top-stock categories for get_top_stocks()
TOP_STOCK_CATEGORIES = ("top_gainer", "top_loser", "top_turnover", "top_trade", "top_transaction")

# Valid index ID range (from YONEPSE upstream validation)
INDEX_ID_MIN = 51
INDEX_ID_MAX = 67
