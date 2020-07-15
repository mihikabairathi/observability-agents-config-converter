"""
Program that converts a fluentd config file to master agent config file.

Usage: python3 -m [--help] config_script <path to file> <path to dir>
"""

import os
import subprocess
import sys


def read_file(path: str) -> str:
    """Reads contents of file at path."""
    with open(path, 'rt') as f:
        return f.read()


def get_object(args: list) -> None:
    """Run ruby exec file and get message object."""
    try:
        subprocess.run(['config_converter/config_parser/bin/config_parser'] +
                       args,
                       check=True)
    except subprocess.CalledProcessError:
        sys.exit()
    if not os.path.exists(args[-1] + '/config.json'):
        sys.exit()


def convert_object(args: list) -> None:
    """Run config_mapper python file to create yaml file."""
    config_json: str = read_file(f'{args[0]}/config.json')
    cli_args = args + [config_json]
    try:
        subprocess.run([
            'python3', '-B', '-m',
            'config_converter.config_mapper.config_mapper'
        ] + cli_args,
                       check=True)
    except subprocess.CalledProcessError:
        sys.exit()


if __name__ == '__main__':
    args_passed = sys.argv[1:]  # list of config_path and master_directory
    get_object(args_passed)
    fluentd_path = args_passed[0]
    master_dir = args_passed[1]
    file_name = os.path.splitext(os.path.basename(fluentd_path))[0]
    convert_object([master_dir, file_name])
    subprocess.run(['rm', f'{args_passed[-1]}/config.json'], check=True)
