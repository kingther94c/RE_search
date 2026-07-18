"""Render smoke tests for the ACTIVE engine renderers.

The superseded v1 renderer had four dedicated render tests while the live
renderers had none (only the report_out routing lint). These keep the live
render() paths from shipping broken: a real engine result must render to
non-trivial HTML without raising, and the out-of-scope path must render too.
"""
import pytest

from deliverables import build_condo_valuation_report as condo_r
from deliverables import build_landed_valuation_report as landed_r
from researcher.backtest.store import TransactionStore
from researcher.engine.value_landed import LandedSpec, value_landed
from researcher.engine.value_unit import SubjectSpec, value


@pytest.fixture(scope="module")
def store():
    return TransactionStore.load()


def test_condo_renderer_renders_a_real_valuation(store):
    v = value(SubjectSpec("TREASURE AT TAMPINES", 936, floor=12, asof="2026-07-01"),
              store.exclude_bulk().psf_band(500, 6500))
    assert not v.get("error"), v
    out = condo_r.render(v)
    assert len(out) > 2000
    assert f"{v['fair_value']['psf']:,.0f}" in out or str(round(v["fair_value"]["psf"])) in out


def test_condo_renderer_renders_the_error_path(store):
    v = value(SubjectSpec("NO SUCH CONDO XYZ", 900, floor=10, asof="2026-07-01"),
              store.exclude_bulk().psf_band(500, 6500))
    assert v.get("error")
    out = condo_r.render(v)
    assert out and "NO SUCH CONDO XYZ" in out


def test_landed_renderer_renders_a_real_valuation(store):
    v = value_landed(LandedSpec("ALNWICK ROAD", 2800, "Terrace", asof="2026-07-01"), store)
    assert not v.get("error"), v
    out = landed_r.render(v)
    assert len(out) > 2000
    assert "ALNWICK ROAD" in out
