"""
File to run tests for the config_converter algorithm

Usage: python3 -m pytest
Note: Run this file from the parent directory (outside test folder)
"""

import subprocess
import tempfile


def read_file(path):
    """Reads file contents at path."""
    with open(path, 'rt') as f:
        return f.read()


def check_equality(config_name):
    with tempfile.TemporaryDirectory() as tmpdirname:
        subprocess.run([
            "python3", "-B", "-m", "config_script",
            f'test/data/{config_name}.conf', tmpdirname
        ],
                       check=True)
        expected = read_file(f'test/data/{config_name}.yaml')
        observed = read_file(f'{tmpdirname}/{config_name}.yaml')
    assert expected == observed


def test_no_in_tail():
    check_equality('no_in_tail')


def test_in_tail_deprecated():
    check_equality('in_tail_deprecated')


def test_in_tail():
    check_equality('in_tail')


def test_in_tail_unknown():
    check_equality("in_tail_unknown")


def test_in_tail_double():
    check_equality('in_tail_double')
