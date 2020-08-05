"""
Program that converts a fluentd config file to a master agent config file.

Usage:
    python3 -m config_script [--help] [--unified_agent_log_level level]
    [--unified_agent_log_dirpath path] <fluentd path> <master path>
Where:
    master path: directory to store master agent config file in
    fluentd path: path to the fluentd config file
"""

import argparse
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


def validate_args(parser: argparse.ArgumentParser,
                  args: argparse.Namespace) -> None:
    """Validate paths of config file and master dir."""
    if not os.path.isfile(args.config_path):
        parser.print_usage()
        print(f'{parser.prog}: error: {args.config_path} is invalid file')
    elif not os.path.isdir(args.master_dir):
        parser.print_usage()
        print(f'{parser.prog}: error: {args.master_dir} is invalid directory')
    else:
        return
    sys.exit()


def create_parser() -> argparse.ArgumentParser:
    """Create a parser and optional arguments."""
    parser = argparse.ArgumentParser(description='Configuration Converter',
                                     prog='PROG')
    parser.add_argument('config_path', help='path of fluentd config file')
    parser.add_argument('master_dir',
                        help='directory to store master ' + 'config file in')
    parser.add_argument(
        '--unified_agent_log_level',
        default='info',
        metavar='level',
        choices=['info', 'fatal', 'error', 'warn', 'debug', 'trace'],
        help='default: info, other options: fatal,error,warn,debug,trace')
    parser.add_argument('--unified_agent_log_dirpath',
                        metavar='path',
                        default='/var/log/ops_agent/ops_agent.log',
                        help='default: /var/log/ops_agent/ops_agent.log')
    return parser


if __name__ == '__main__':
    parser: argparse.ArgumentParser = create_parser()
    args: argparse.Namespace = parser.parse_args()
    validate_args(parser, args)
    file_name: str = os.path.splitext(os.path.basename(args.config_path))[0]
    get_object([args.config_path, args.master_dir])
    convert_object([
        args.master_dir, file_name, args.unified_agent_log_level,
        args.unified_agent_log_dirpath
    ])
    subprocess.run(['rm', os.path.join(args.master_dir, 'config.json')],
                   check=True)
