"""
tests utility funcionality
"""

from ..system.utility.utils import retry_config


def test_retry_config_values():
    """"tests that retry_config returns expected values"""
    cfg = retry_config()
    # basic contract checks
    assert hasattr(cfg, "attempts")
    assert getattr(cfg, "attempts") == 5
    assert hasattr(cfg, "initial_delay")
    assert getattr(cfg, "initial_delay") == 1
    assert hasattr(cfg, "http_status_codes")
    assert 429 in getattr(cfg, "http_status_codes")
