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
    output_stats = \
        '{\n  "attributes_num": 5,' +\
        '\n  "attributes_recognized": 0,' +\
        '\n  "attributes_unrecognized": 3,' +\
        '\n  "attributes_skipped": 2,' +\
        '\n  "entities_num": 2,' +\
        '\n  "entities_skipped": 1,' +\
        '\n  "entities_unrecognized": 1,' +\
        '\n  "entities_recognized_success": 0,' +\
        '\n  "entities_recognized_partial": 0,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_deprecated(capfd):
    check_equality('in_tail_deprecated')
    output_stats = \
        '{\n  "attributes_num": 11,' +\
        '\n  "attributes_recognized": 9,' +\
        '\n  "attributes_unrecognized": 0,' +\
        '\n  "attributes_skipped": 2,' +\
        '\n  "entities_num": 2,' +\
        '\n  "entities_skipped": 1,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 0,' +\
        '\n  "entities_recognized_partial": 1,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_normal(capfd):
    check_equality('in_tail_normal')
    output_stats = \
        '{\n  "attributes_num": 9,' +\
        '\n  "attributes_recognized": 8,' +\
        '\n  "attributes_unrecognized": 0,' +\
        '\n  "attributes_skipped": 1,' +\
        '\n  "entities_num": 3,' +\
        '\n  "entities_skipped": 1,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 2,' +\
        '\n  "entities_recognized_partial": 0,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_unknown(capfd):
    check_equality('in_tail_unknown')
    output_stats = \
        '{\n  "attributes_num": 11,' +\
        '\n  "attributes_recognized": 9,' +\
        '\n  "attributes_unrecognized": 1,' +\
        '\n  "attributes_skipped": 1,' +\
        '\n  "entities_num": 3,' +\
        '\n  "entities_skipped": 1,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 1,' +\
        '\n  "entities_recognized_partial": 1,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_double(capfd):
    check_equality('in_tail_double')
    output_stats = \
        '{\n  "attributes_num": 16,' +\
        '\n  "attributes_recognized": 16,' +\
        '\n  "attributes_unrecognized": 0,' +\
        '\n  "attributes_skipped": 0,' +\
        '\n  "entities_num": 4,' +\
        '\n  "entities_skipped": 0,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 4,' +\
        '\n  "entities_recognized_partial": 0,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_include(capfd):
    check_equality('in_tail_include')
    output_stats = \
        '{\n  "attributes_num": 26,' +\
        '\n  "attributes_recognized": 22,' +\
        '\n  "attributes_unrecognized": 1,' +\
        '\n  "attributes_skipped": 3,' +\
        '\n  "entities_num": 6,' +\
        '\n  "entities_skipped": 2,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 2,' +\
        '\n  "entities_recognized_partial": 2,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_syslog_endpoint(capfd):
    check_equality('in_syslog_endpoint')
    output_stats = \
        '{\n  "attributes_num": 12,' +\
        '\n  "attributes_recognized": 0,' +\
        '\n  "attributes_unrecognized": 12,' +\
        '\n  "attributes_skipped": 0,' +\
        '\n  "entities_num": 2,' +\
        '\n  "entities_skipped": 0,' +\
        '\n  "entities_unrecognized": 2,' +\
        '\n  "entities_recognized_success": 0,' +\
        '\n  "entities_recognized_partial": 0,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_rabbitmq(capfd):
    check_equality('in_tail_rabbitmq')
    output_stats = \
        '{\n  "attributes_num": 28,' +\
        '\n  "attributes_recognized": 24,' +\
        '\n  "attributes_unrecognized": 0,' +\
        '\n  "attributes_skipped": 4,' +\
        '\n  "entities_num": 4,' +\
        '\n  "entities_skipped": 0,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 0,' +\
        '\n  "entities_recognized_partial": 4,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_chef(capfd):
    check_equality('in_tail_chef')
    output_stats = \
        '{\n  "attributes_num": 72,' +\
        '\n  "attributes_recognized": 60,' +\
        '\n  "attributes_unrecognized": 0,' +\
        '\n  "attributes_skipped": 12,' +\
        '\n  "entities_num": 12,' +\
        '\n  "entities_skipped": 0,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 0,' +\
        '\n  "entities_recognized_partial": 12,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out


def test_in_tail_cli(capfd):
    config_name = 'in_tail_cli'
    with tempfile.TemporaryDirectory() as tmpdirname:
        subprocess.run([
            'python3', '-B', '-m', 'config_script', '--log_level=error',
            '--log_filepath=/tmp', f'test/data/{config_name}.conf', tmpdirname
        ],
                       check=True)
        expected = read_file(f'test/data/{config_name}.yaml')
        observed = read_file(f'{tmpdirname}/{config_name}.yaml')
    output_stats = \
        '{\n  "attributes_num": 22,' +\
        '\n  "attributes_recognized": 9,' +\
        '\n  "attributes_unrecognized": 0,' +\
        '\n  "attributes_skipped": 13,' +\
        '\n  "entities_num": 1,' +\
        '\n  "entities_skipped": 0,' +\
        '\n  "entities_unrecognized": 0,' +\
        '\n  "entities_recognized_success": 0,' +\
        '\n  "entities_recognized_partial": 1,' +\
        '\n  "entities_recognized_failure": 0\n}'
    assert output_stats in capfd.readouterr().out
    assert expected == observed
