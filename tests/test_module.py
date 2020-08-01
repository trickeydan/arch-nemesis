"""Test that the arch_nemesis imports as expected."""

import arch_nemesis


def test_module() -> None:
    """Test that the module behaves as expected."""
    assert arch_nemesis.__version__ is not None
