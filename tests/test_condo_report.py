"""Generic condo-valuation report builder: rendering robustness."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "build_condo_report", os.path.join(ROOT, "deliverables", "build_condo_report.py"))
bcr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bcr)


def test_render_minimal_digest_no_crash():
    html = bcr.render({"subject": {"name": "X"}, "summary": "s"})
    assert "X" in html and "<html" in html


def test_render_full_sections_and_grid():
    html = bcr.render({
        "subject": {"name": "Unit A", "development": "Dev", "size_sqft": 1000,
                    "floor": 3, "bedrooms": 3, "tenure": "Freehold"},
        "asof": "2032-05-06",
        "summary": "sum",
        "valuation": {"estimate_psf": 2000, "estimate_price": 2_000_000,
                      "low_psf": 1900, "high_psf": 2100, "low_price": 1_900_000,
                      "high_price": 2_100_000, "params_note": "params",
                      "grid": [{"label": "c1", "raw_psf": 1950, "time_adj": 1.01,
                                "floor_adj": 1.0, "size_adj": 0.99, "type_adj": 1.0,
                                "adj_psf": 1980, "weight": 0.8}]},
        "comps_table": [{"date": "2031-01", "size_sqft": 990, "level": "L2",
                         "psf": 1950, "price": 1_930_500, "note": "n"}],
        "advisory": {"stance": "BUY", "detail": "d", "cost_stack": ["BSD x"]},
        "verification": [{"claim": "c", "status": "confirmed", "note": "n"}],
    })
    assert "2032-05-06" in html          # asof used, nothing hardcoded
    assert "S$2,000,000" in html and "1,980" in html
    assert "BUY" in html and "BSD x" in html


def test_render_escapes_html():
    html = bcr.render({"subject": {"name": "<script>x</script>"}, "summary": ""})
    assert "<script>x" not in html


def test_profitability_table_and_plain_sources():
    html = bcr.render({
        "subject": {"name": "X"}, "summary": "",
        "profitability": [{"unit": "#01-01 (500 sqft)", "bought": "2020 @ $1m",
                           "sold": "2025 @ $1.2m", "profit": "$200,000", "holding": "5y",
                           "annualised": "3.7%"}],
        "sources": ["https://example.com/a", "research/captures/foo (screen dump)"],
    })
    assert "已实现回报" in html and "$200,000" in html and "3.7%" in html
    assert "<a href='https://example.com/a'>" in html
    assert "<a href='research/captures" not in html  # non-URL sources are plain text
