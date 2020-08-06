"""
File to run tests for the config_converter algorithm

Usage: python3 -m pytest
Note: Run this file from the parent directory (outside test folder)
"""

import json
import subprocess
import tempfile


def read_file(path):
    """Reads file contents at path."""
    with open(path, 'rt') as f:
        return f.read()


def check_stats(output_str, expected_stats):
    """Checks stats printed out are correct."""
    output_stats = output_str.strip()
    assert json.loads(output_stats) == expected_stats


def check_equality(config_name):
    """Checks mapped configurations generated are correct."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        subprocess.run([
            'python3', '-B', '-m', 'config_script',
            f'test/data/{config_name}.conf', tmpdirname
        ],
                       check=True)
        expected = read_file(f'test/data/{config_name}.yaml')
        observed = read_file(f'{tmpdirname}/{config_name}.yaml')
    assert expected == observed


def test_types():
    for prg in {
            'config_script.py',
            'config_converter/config_mapper/config_mapper.py'
    }:
        subprocess.run(['python3', '-B', '-m', 'pytype', prg], check=True)


def test_no_in_tail(capfd):
    check_equality('no_in_tail')
    expected_stats = {
        'attributes_num': 5,
        'attributes_recognized': 0,
        'attributes_unrecognized': 3,
        'attributes_skipped': 2,
        'entities_num': 2,
        'entities_skipped': 1,
        'entities_unrecognized': 1,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 0,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_deprecated(capfd):
    check_equality('in_tail_deprecated')
    expected_stats = {
        'attributes_num': 11,
        'attributes_recognized': 9,
        'attributes_unrecognized': 0,
        'attributes_skipped': 2,
        'entities_num': 2,
        'entities_skipped': 1,
        'entities_unrecognized': 0,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 1,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_normal(capfd):
    check_equality('in_tail_normal')
    expected_stats = {
        'attributes_num': 9,
        'attributes_recognized': 8,
        'attributes_unrecognized': 0,
        'attributes_skipped': 1,
        'entities_num': 3,
        'entities_skipped': 1,
        'entities_unrecognized': 0,
        'entities_recognized_success': 2,
        'entities_recognized_partial': 0,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_unknown(capfd):
    check_equality('in_tail_unknown')
    expected_stats = {
        'attributes_num': 11,
        'attributes_recognized': 9,
        'attributes_unrecognized': 1,
        'attributes_skipped': 1,
        'entities_num': 3,
        'entities_skipped': 1,
        'entities_unrecognized': 0,
        'entities_recognized_success': 1,
        'entities_recognized_partial': 1,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_double(capfd):
    check_equality('in_tail_double')
    expected_stats = {
        'attributes_num': 16,
        'attributes_recognized': 16,
        'attributes_unrecognized': 0,
        'attributes_skipped': 0,
        'entities_num': 4,
        'entities_skipped': 0,
        'entities_unrecognized': 0,
        'entities_recognized_success': 4,
        'entities_recognized_partial': 0,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_include(capfd):
    check_equality('in_tail_include')
    expected_stats = {
        'attributes_num': 26,
        'attributes_recognized': 22,
        'attributes_unrecognized': 1,
        'attributes_skipped': 3,
        'entities_num': 6,
        'entities_skipped': 2,
        'entities_unrecognized': 0,
        'entities_recognized_success': 2,
        'entities_recognized_partial': 2,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_syslog_endpoint(capfd):
    check_equality('in_syslog_endpoint')
    expected_stats = {
        'attributes_num': 12,
        'attributes_recognized': 0,
        'attributes_unrecognized': 12,
        'attributes_skipped': 0,
        'entities_num': 2,
        'entities_skipped': 0,
        'entities_unrecognized': 2,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 0,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_rabbitmq(capfd):
    check_equality('in_tail_rabbitmq')
    expected_stats = {
        'attributes_num': 28,
        'attributes_recognized': 24,
        'attributes_unrecognized': 0,
        'attributes_skipped': 4,
        'entities_num': 4,
        'entities_skipped': 0,
        'entities_unrecognized': 0,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 4,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_chef(capfd):
    check_equality('in_tail_chef')
    expected_stats = {
        'attributes_num': 72,
        'attributes_recognized': 60,
        'attributes_unrecognized': 0,
        'attributes_skipped': 12,
        'entities_num': 12,
        'entities_skipped': 0,
        'entities_unrecognized': 0,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 12,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)


def test_in_tail_cli(capfd):
    config_name = 'in_tail_cli'
    with tempfile.TemporaryDirectory() as tmpdirname:
        subprocess.run([
            'python3', '-B', '-m', 'config_script',
            '--master_agent_log_level=error',
            '--master_agent_log_dirpath=/tmp',
            f'test/data/{config_name}.conf', tmpdirname
        ],
                       check=True)
        expected = read_file(f'test/data/{config_name}.yaml')
        observed = read_file(f'{tmpdirname}/{config_name}.yaml')
    assert observed == expected
    expected_stats = {
        'attributes_num': 22,
        'attributes_recognized': 9,
        'attributes_unrecognized': 0,
        'attributes_skipped': 13,
        'entities_num': 1,
        'entities_skipped': 0,
        'entities_unrecognized': 0,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 1,
        'entities_recognized_failure': 0
    }
    check_stats(capfd.readouterr().out, expected_stats)
