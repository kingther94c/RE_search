"""Shared fixtures: the URA transaction spine parses ONCE per pytest session.

Every module that needs the full store (or the engine-v2 condo slice) takes these
fixtures instead of calling TransactionStore.load() itself — the load parses a
136k-row JSON (~1s), so per-module copies grow suite time linearly.
"""
import pytest

from researcher.backtest.store import TransactionStore


@pytest.fixture(scope="session")
def store():
    return TransactionStore.load()


@pytest.fixture(scope="session")
def condo_store(store):
    # The engine-v2 condo spine — the exact filter value_unit documents.
    return store.exclude_bulk().psf_band(500, 6500)
