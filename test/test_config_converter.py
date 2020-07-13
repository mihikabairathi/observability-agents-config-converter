"""
File to run tests for the config_converter algorithm

Usage: python3 -m pytest
Note: Run this file from the parent directory (outside test folder)
"""

import subprocess
import config_converter.config_converter as config_converter


def read_file(path):
    with open(path, 'rt') as f:
        return f.read()


def check_equality(config_name):
    fluentd_path = f'test/data/cases/{config_name}.conf'
    master_path = 'test/data/observed'
    config_obj = config_converter.get_object([fluentd_path, master_path])
    config_converter.write_to_yaml(
        config_converter.ConfigConverter(config_obj).result, master_path,
        config_name)
    expected = read_file(f'test/data/cases/{config_name}.yaml')
    observed = read_file(f'{master_path}/{config_name}.yaml')
    assert expected == observed
    subprocess.run(["rm", 'test/data/observed/config.json'], check=True)


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
