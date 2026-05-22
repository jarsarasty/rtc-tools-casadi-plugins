import pytest


@pytest.fixture(scope="session", autouse=True)
def load_plugin():
    pytest.importorskip("rtctools_highs")
