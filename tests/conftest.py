"""Keep backend-selection tests independent of the developer's configured model."""

import pytest


@pytest.fixture(autouse=True)
def isolated_model_environment(monkeypatch):
    monkeypatch.delenv("BOARDSNAP_MODEL", raising=False)
