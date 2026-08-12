from config import parse_config
import pytest

def test_timeout_present():
    assert parse_config({'timeout': 60}) == 60

def test_timeout_missing():
    assert parse_config({}) == 30
