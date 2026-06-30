"""Single source of truth for everything read out of PropNex Investment Suite
for the Spottiswoode Suites trial valuation (extracted 2026-06-28 via the mbx
UI-automation harness; app valuation snapshot date = 24 Jun 2026).

Every number here was read from the on-screen accessibility tree (UI automation
only) and saved alongside a screenshot + XML dump under research/captures/.
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Development facts (Property Info tab)
# ─────────────────────────────────────────────────────────────────────────────
DEVELOPMENT = {
    "name": "Spottiswoode Suites",
    "address": "16 Spottiswoode Park Road, Singapore",
    "type": "Apartment / Condominium",
    "region": "RCR",
    "district": "D2 - Anson, Tanjong Pagar",
    "subtown": "Everton Park",
    "top_year": 2017,
    "tenure": "Freehold",
    "land_size_sqft": 38911,
    "plot_ratio": 2.8,
    "total_units": 183,
    "storeys": 36,
    "developer": "Spottiswoode Development Pte Ltd (Centurion + Lian Beng JV)",
}

# ─────────────────────────────────────────────────────────────────────────────
# Subject unit (Tower View, block 16, floor 18, stack 03)
# ─────────────────────────────────────────────────────────────────────────────
SUBJECT = {
    "unit": "#18-03",
    "bedrooms": 3,            # compact / SOHO 3BR
    "size_sqft": 743,
    "floor": 18,
    "tenure": "Freehold",
    "last_txn_date": "2021-05-07",
    "last_txn_price": 1_500_000,
    "last_txn_psf": 2020,
    "app_est_val": 1_661_000,   # the app's own AVM estimate
    "app_est_psf": 2236,
    "app_est_pl": 161_000,
    "holding": "5y 1m",
    "caveats": 2,
}

# Same-stair line (#xx-03) reference units from Tower View
STACK_03 = [
    # unit, sqft, bed, last_date, last_psf, est_val_psf
    {"unit": "#36-03", "sqft": 1378, "bed": 3, "date": "2013-03-01", "psf": 1859, "est_psf": 1723},
    {"unit": "#18-03", "sqft": 743,  "bed": 3, "date": "2021-05-07", "psf": 2020, "est_psf": 2236},
    {"unit": "#17-03", "sqft": 743,  "bed": 3, "date": "2013-02-04", "psf": 2107, "est_psf": 2234},
]

# ─────────────────────────────────────────────────────────────────────────────
# Recent resale transactions (Sale tab, 10Y filter, harvested table)
# date, level, stack, bedrooms, size_sqft, psf, price
# ─────────────────────────────────────────────────────────────────────────────
TRANSACTIONS = [
    ("2026-02-03", 28, "04", 1, 441, 2352, 1_038_000),
    ("2026-01-09",  9, "08", 1, 452, 2146,   970_000),
    ("2025-12-03", 23, "06", 1, 452, 2389, 1_080_000),
    ("2025-09-10", 19, "08", 1, 441, 2275, 1_003_888),
    ("2025-07-16", 25, "04", 1, 452, 2278, 1_030_000),
    ("2025-05-16", 25, "06", 1, 463, 2344, 1_085_000),
    ("2025-03-25", 10, "01", 2, 581, 2581, 1_500_000),
    ("2024-10-15", 17, "01", 2, 581, 2581, 1_500_000),
    ("2024-09-05", 12, "05", 1, 441, 2358, 1_040_000),
    ("2024-08-29", 13, "07", 2, 538, 2453, 1_320_000),
    ("2024-08-15", 15, "04", 1, 452, 2327, 1_052_000),
    ("2024-07-25", 19, "05", 1, 441, 2426, 1_070_000),
    ("2024-07-19", 18, "07", 2, 538, 2471, 1_330_000),
    ("2024-05-09", 30, "07", 3, 1033, 2419, 2_500_000),
    ("2024-04-26", 16, "05", 1, 441, 2266, 1_000_000),
]

# Price band over the 10Y window (Sale tab header)
SALE_BAND = {"low_psf": 1571, "avg_psf": 2206, "high_psf": 2581,
             "low_price": 970_000, "avg_price": 1_405_287, "high_price": 2_500_000}

# ─────────────────────────────────────────────────────────────────────────────
# Rental comparables (Rent tab, recent — May 2026)
# bedrooms, size_band, psf, monthly_rent
# ─────────────────────────────────────────────────────────────────────────────
RENTALS = [
    (2, "500-600", 7.82, 4300),
    (3, "700-800", 6.13, 4600),   # <- subject-relevant (743 sqft 3BR)
    (1, "400-500", 7.56, 3400),
    (2, "600-700", 6.62, 4300),
    (3, "700-800", 5.93, 4450),   # <- subject-relevant
]
RENT_BAND = {"low": 1500, "avg": 3384, "high": 7000,
             "low_psf": 3.33, "avg_psf": 6.07, "high_psf": 9.11}

# ─────────────────────────────────────────────────────────────────────────────
# Profitability tab (matched buy→sell pairs, realised holding returns)
# ─────────────────────────────────────────────────────────────────────────────
PROFIT_BAND = {"low": 1000, "avg": 90_877, "high": 346_000,
               "low_psf": 2, "avg_psf": 142, "high_psf": 459}
PROFIT_EXAMPLES = [
    {"unit": "#17-01", "sqft": 581, "buy": ("2021-04", 1_238_000, 2130),
     "sell": ("2024-10-15", 1_500_000, 2581), "profit": 262_000, "hold": "3y5m", "annualised": 5.69},
]

# ─────────────────────────────────────────────────────────────────────────────
# Nearby projects (Nearby Properties tab, 200m radius, 6 projects)
# ─────────────────────────────────────────────────────────────────────────────
NEARBY = [
    {"name": "Spottiswoode Suites", "tenure": "Freehold", "top": 2017, "units": 183,
     "beds": "1,2,3", "size": "400-1500", "sale_psf": (1571, 2581), "sales_vol": 102,
     "rent_psf": (3.33, 9.11), "yield_avg": 2.91, "rental_vol": 847},
    {"name": "Spottiswoode 18", "tenure": "Freehold", "top": 2015, "units": 251,
     "beds": "1,2", "size": "300-1400", "sale_psf": (1433, 2529), "sales_vol": 107,
     "rent_psf": (2.58, 11.43), "yield_avg": 3.19, "rental_vol": 1638},
    {"name": "Sky Everton (2023 FH)", "tenure": "Freehold", "top": 2023, "units": 262,
     "beds": "1,2,3", "size": "—", "sale_psf": (2053, 3406), "sales_vol": None,
     "rent_psf": (5.29, 11.63), "yield_avg": 2.94, "rental_vol": None},
    {"name": "Spottiswoode Residences", "tenure": "Freehold", "top": 2014, "units": None,
     "beds": "—", "size": "—", "sale_psf": None, "sales_vol": None,
     "rent_psf": None, "yield_avg": 2.94, "rental_vol": None},
    {"name": "Older FH walk-up (1985)", "tenure": "Freehold", "top": 1985, "units": None,
     "beds": "—", "size": "—", "sale_psf": None, "sales_vol": None,
     "rent_psf": None, "yield_avg": 1.79, "rental_vol": None},
    {"name": "Spottiswoode Park (1970)", "tenure": "—", "top": 1970, "units": None,
     "beds": "—", "size": "—", "sale_psf": None, "sales_vol": None,
     "rent_psf": None, "yield_avg": None, "rental_vol": None},
]
AREA_BAND = {"sale_avg_psf": 2196, "rent_avg_psf": 5.47}

# ─────────────────────────────────────────────────────────────────────────────
# Macro / regulatory context (external research, triangulated — 2026)
# ─────────────────────────────────────────────────────────────────────────────
MACRO = {
    "ura_index_q1_2026_overall": 0.3,     # % q-o-q (flash)
    "ura_index_q4_2025_overall": 0.6,
    "ura_rcr_nonlanded_q1_2026": 0.9,     # % q-o-q
    "sale_volume_qoq_q1_2026": -40,       # %
    "sora_feb_2026": 1.00,                # %
    "fixed_mortgage_from": 1.40,          # % p.a.
    "absd_sc": {"1st": 0, "2nd": 20, "3rd": 30},
    "absd_pr": {"1st": 5, "2nd": 30, "3rd": 30},
    "absd_foreigner": 60,
    "ssd_new": {"<=1y": 16, "1-2y": 12, "2-3y": 8, "3-4y": 4, ">4y": 0},  # bought on/after 4 Jul 2025
    "catalyst": "Cantonment MRT (Circle Line 6) opens 12 Jul 2026 — ~4th line in walking distance",
}
