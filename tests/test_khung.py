"""Kiểm tra khung repo: các gói import được. File dùng chung, không thuộc vai nào."""
import importlib

import pytest


@pytest.mark.parametrize("goi", ["engine", "agents", "metrics", "plots", "scenarios", "defenses"])
def test_import_goi(goi):
    importlib.import_module(goi)
