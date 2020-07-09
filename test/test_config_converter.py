"""
File to run tests for the config_converter algorithm

Usage: python3 -m pytest
Note: Run this file from the parent directory (outside test folder)
"""

import pytest
import os
import subprocess
import config_converter

def read_file(path):
    with open(path, 'rt') as f:
        return f.read()

def test_dummy():
    subprocess.run(["python3", "-B", "-m", "config_converter", 
        "test/data/no_in_tail.conf", 
                    "test/data"], check=True)
    expected = read_file("test/data/no_in_tail_expected.yaml")
    observed = read_file("test/data/no_in_tail.yaml")
    assert(expected == observed)

