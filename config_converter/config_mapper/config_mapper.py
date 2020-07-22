"""Converts fields of a fluentd config file to a master agent config file.

Usage: To run just this file:
    python3 -m config_converter.config_mapper.config_mapper
    <master path> <file name> <log level> <log filepath> <config json>
Where:
    master path: directory to store master agent config file in
    file name: what you want to name the master agent file
    config json: string of fluentd config parsed into a json format
To do:
    1. Stats like #fields converted, output as schema.
    2. Generate logs.
    3. Tests for right logs, stats, CLI additions.
    4. Extensive testing with sample files
"""

import sys
import yaml
from google.protobuf import json_format
from config_converter.config_mapper import config_pb2

# fields we cannot convert from fluentd to master agent configs
_UNSUPPORTED_FIELDS = [
    'emit_unmatched_lines', 'enable_stat_watcher', 'enable_watch_timer',
    'encoding', 'from_encoding', 'ignore_repeated_permission_error',
    'limit_recently_modified', 'open_on_every_update', 'path_timezone',
    'pos_file_compaction_interval', 'read_from_head', 'read_lines_limit',
    'skip_refresh_on_startup'
]
# plugins we know how to convert
_SUPPORTED_PLUGINS = ['in_tail']


def extract_root_dirs(config_obj: config_pb2.Directive) -> dict:
    """Checks all dirs, maps with corresponding params if supported."""
    logs_module = dict()
    plugin_prefix_map = {'source': 'in_', 'match': 'out_'}
    dir_name_map = {'source': 'sources', 'match': 'output'}
    # these dicts can be updated when more plugins are supported
    for d in config_obj.directives:
        if d.name not in plugin_prefix_map:
            print(f'Currently we do not support plugins of {d.name}')
            continue
        try:
            plugin_type = next(p.value for p in d.params if p.name == '@type')
        except StopIteration:
            print('Invalid configuration - missing @type param')
            sys.exit()
        plugin_name = plugin_prefix_map[d.name] + plugin_type
        if plugin_name not in _SUPPORTED_PLUGINS:
            print(f'We do not know plugin {plugin_name}')
        else:
            plugin_dir = dir_name_map[d.name]
            if plugin_dir not in logs_module:
                logs_module[plugin_dir] = []
            logs_module[plugin_dir].append(_convert_plugin(d, plugin_name))
    return {'logs_module': logs_module}


def _convert_plugin(d: config_pb2.Directive, plugin: str) -> dict:
    """Cases on plugin, calls corresponding mapping function."""
    result = dict()
    plugin_type_map = {'tail': 'file'}
    plugin_type = next(p.value for p in d.params if p.name == '@type')
    result['type'] = plugin_type_map[plugin_type]
    try:
        result['name'] = next(p.value for p in d.params if p.name == 'tag')
    except StopIteration:
        print('Invalid configuration - missing tag')
        sys.exit()
    if plugin == 'in_tail':
        result[f'{result["type"]}_{d.name}_config']: dict = _convert_in_tail(d)
    return result


def _convert_in_tail(d: config_pb2.Directive) -> dict:
    """Uses mapping rules to convert in_tail plugin fields."""
    fields = dict()
    # these fields may not belong to the same level, have a 1:1 mapping, etc
    # https://docs.fluentd.org/parser/multiline - shows formatN works for
    # 1 <= N <= 20
    special_fields = [
        'format', 'format_firstline', '@type', 'multiline_flush_interval',
        'expression'
    ] + [f'format{i}' for i in range(1, 21)]
    for p in d.params:
        if p.name == '@type' or p.name == 'tag':
            continue
        if p.name == 'exclude_path':
            fields['exclude_path'] = eval(p.value)  # string to list
        elif p.name == 'path':
            fields['path'] = p.value
        elif p.name == 'path_key':
            fields['path_field_name'] = p.value
        elif p.name == 'pos_file':
            fields['checkpoint_file'] = p.value
        elif p.name == 'refresh_interval':
            fields['refresh_interval'] = eval(p.value)  # string to time
        elif p.name == 'rotate_wait':
            fields['rotate_wait'] = eval(p.value)  # string to time
        elif p.name in special_fields:
            _convert_parse_dir(fields, p)
        elif p.name in _UNSUPPORTED_FIELDS:
            print(f'{p.name} cannot be mapped into master agent config file.')
        else:
            print(f'{p.name} is an unknown field.')
    for nd in d.directives:
        if nd.name == 'parse':
            for np in nd.params:
                _convert_parse_dir(fields, np)
        else:
            print(f'{nd.name} is an unknown directive.')
    return fields


def _convert_parse_dir(specific: dict, p: config_pb2.Param) -> None:
    """Create parser dir in master config."""
    parser_type_map = {
        'multiline': 'multiline',
        'none': 'none',
        'regex': 'regex',
        'apache2': 'regex',
        'apache_error': 'regex',
        'json': 'json',
        'nginx': 'regex'
    }
    specific['parser'] = specific.get('parser', dict())
    if p.name == 'expression':
        if 'regex_parser_config' not in specific['parser']:
            specific['parser']['regex_parser_config'] = dict()
        specific['parser']['regex_parser_config'][p.name] = p.value
    elif p.name == 'format' or p.name == '@type':
        if p.value not in parser_type_map:
            print('unknown parser format type ' + p.value)
        else:
            specific['parser']['type'] = parser_type_map[p.value]
    else:
        if 'multiline_parser_config' not in specific['parser']:
            specific['parser']['multiline_parser_config'] = dict()
        if p.name in [f'format{i}' for i in range(1, 21)]:
            f_num = p.name[6:]
            specific['parser']['multiline_parser_config'][f'format_{f_num}']\
                = p.value
        elif p.name == 'multiline_flush_interval':
            specific['parser']['multiline_parser_config']['flush_interval']\
                    = eval(p.value)  # string to time
        else:
            specific['parser']['multiline_parser_config'][p.name] = p.value


def write_to_yaml(result: dict, path: str, name: str) -> None:
    """Writes created result dictionary to a yaml file."""
    with open(f'{path}/{name}.yaml', 'w') as f:
        yaml.dump(result, f)


if __name__ == '__main__':
    master_path, file_name, config_json = sys.argv[1], sys.argv[2], sys.argv[5]
    log_level, log_filepath = sys.argv[3], sys.argv[4]
    yaml_dict: dict = extract_root_dirs(
        json_format.Parse(config_json, config_pb2.Directive()))
    yaml_dict['logging_level'] = log_level
    yaml_dict['log_file_path'] = log_filepath
    write_to_yaml(yaml_dict, master_path, file_name)
