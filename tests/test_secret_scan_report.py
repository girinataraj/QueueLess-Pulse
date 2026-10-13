"""Reject empty history scans without rejecting nonzero multi-digit counts."""
import pytest
from scripts.verify_secrets import empty_history_scan

@pytest.mark.parametrize('count,empty',[(0,True),(10,False),(20,False),(100,False)])
def test_history_scan_requires_an_actual_zero_count(count,empty):
    output=f'9:04AM INF {count} commits scanned.\n9:04AM INF no leaks found\n'
    assert bool(empty_history_scan(output)) is empty
