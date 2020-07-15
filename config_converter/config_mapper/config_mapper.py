"""Program that converts a fluentd config file to a master agent config file.

Usage: Run the exec file in the bin folder with 2 arguments - the
path to the config file to migrate, and a directory to store the output
master agent config file in.

To do:
1. Improve the CLI. Include a --help option. Allow optional args like
   log-level and log-filepath (see project docs).
2. Create a mapping for log_level if there in the fluentd config file and input
   default ones if not given
3. Generate stats like #fields converted, ignored, and output as schema
4. Generate logs
5. Fix types of numbers, lists
6. Generate tests to check if for right logs, right stats, above changes
"""

import copy
import sys
import yaml
from google.protobuf import json_format
from config_converter.config_mapper import config_pb2

# each sub dict contains fields that stay in the current level only
_MAIN_MAP = {
    'in_tail': {
        'exclude_path': 'exclude_path',
        'path': 'path',
        'path_key': 'path_field_name',
        'pos_file': 'checkpoint_file',
        'refresh_interval': 'refresh_interval',
        'rotate_wait': 'rotate_wait'
    }
}
# each sub list contains fields that need to be treated differently
# https://docs.fluentd.org/parser/multiline - shows formatN works for
# 1 <= N <= 20
_SPECIAL_MAP = {
    'in_tail': [
        'format', 'format_firstline', '@type', 'multiline_flush_interval',
        'expression'
    ] + [f'format{i}' for i in range(1, 21)]
}
# dictionary of dictionaries - one per main plugin type (source, match)
# each dict contains fields that go in the upper level
_OUTER_MAP = {'source': {'tag': 'name', '@type': 'type'}}
# each sub list contains known and allowed sub directives
_SUPPORTED_DIRS = {'in_tail': ['parse']}
_UNSUPPORTED_FIELDS = [
    'emit_unmatched_lines', 'enable_stat_watcher', 'enable_watch_timer',
    'encoding', 'from_encoding', 'ignore_repeated_permission_error',
    'limit_recently_modified', 'open_on_every_update', 'path_timezone',
    'pos_file_compaction_interval', 'read_from_head', 'read_lines_limit',
    'skip_refresh_on_startup'
]
_SUPPORTED_PLUGINS = ['in_tail']
_UNSUPPORTED_PLUGINS = ['in_forward', 'in_syslog']


def extract_root_dirs(config_obj: config_pb2.Directive) -> dict:
    """Checks root dirs, maps with corresponding params if supported."""
    result = {'logs_module': dict()}
    plugin_prefix_map = {'source': 'in_', 'match': 'out_'}
    dir_name_map = {'source': 'sources', 'match': 'output'}
    # these dicts can be updated when more plugins are supported
    for d in config_obj.directives:
        if d.name not in plugin_prefix_map:
            print("Currently we do not support plugins of " + d.name)
            continue
        for p in d.params:
            if p.name == '@type':
                # identify the plugin
                plugin = plugin_prefix_map[d.name] + p.value
                if plugin in _SUPPORTED_PLUGINS:
                    result['logs_module'][dir_name_map[d.name]] = \
                            result['logs_module'].get(
                                dir_name_map[d.name], [])
                    converted_dir: dict = _plugin_convert(d, plugin)
                    result['logs_module'][dir_name_map[d.name]]\
                                .append(converted_dir)
                elif plugin in _UNSUPPORTED_PLUGINS:
                    print("we dont support plugin " + plugin)
                else:
                    print("we dont know plugin " + plugin)
    return result


def _plugin_convert(d: config_pb2.Directive, plugin: str) -> dict:
    """Uses mapping rules passed to function to map all fields."""
    cur = {}
    outer_map = _OUTER_MAP[d.name]
    main_map = _MAIN_MAP[plugin]
    special_params = _SPECIAL_MAP[plugin]
    supported_dirs = _SUPPORTED_DIRS[plugin]
    plugin_type_map = {'tail': 'file'}
    outer_map_copy = copy.copy(outer_map)
    # ensure all outer level params needed are there in directive
    for p in d.params:
        if p.name in outer_map_copy:
            if p.name == '@type':
                cur[outer_map[p.name]] = plugin_type_map[p.value]
            else:
                cur[outer_map[p.name]] = p.value
            outer_map_copy.pop(p.name)
    if outer_map_copy != {}:
        print('invalid configuration')
        sys.exit()
    specific = {}
    for p in d.params:
        if p.name not in outer_map:
            if p.name in _UNSUPPORTED_FIELDS:
                print(f'parameter {p.name} cant be converted')
            elif p.name in special_params:
                _map_special_fields(specific, p, plugin)
            elif p.name not in main_map:
                print(f'parameter {p.name} is unknown')
            else:
                specific[main_map[p.name]] = p.value
    for nd in d.directives:
        if nd.name not in supported_dirs:
            print(f'directive {nd.name} is not supported')
        else:
            for np in nd.params:
                _map_special_fields(specific, np, plugin)
    cur[f'{cur["type"]}_{d.name}_config'] = specific
    return cur


def _map_special_fields(specific: dict, p: config_pb2.Param,
                        plugin: str) -> None:
    """Cases on p with all special_map dict, calls a map function."""
    if p.name in _SPECIAL_MAP[plugin]:
        if plugin == 'in_tail':
            _parser_dir(specific, p)


def _parser_dir(specific: dict, p: config_pb2.Param) -> None:
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
    specific['parser'] = specific.get('parser', {})
    if p.name == 'expression':
        specific['parser']['regex_parser_config'] = \
                specific['parser'].get('regex_parser_config', {})
        specific['parser']['regex_parser_config'][p.name] = p.value
    elif p.name == 'format' or p.name == '@type':
        if p.value not in parser_type_map:
            print('unknown parser format type ' + p.value)
        else:
            specific['parser']['type'] = parser_type_map[p.value]
    else:
        specific['parser']['multiline_parser_config'] = \
                specific['parser'].get('multiline_parser_config', {})
        if p.name in [f'format{i}' for i in range(1, 21)]:
            format_number = p.name[6:]
            specific['parser']['multiline_parser_config']\
                    [f'format_{format_number}'] = p.value
        elif p.name == 'multiline_flush_interval':
            specific['parser']['multiline_parser_config']['flush_interval']\
                    = p.value
        else:
            specific['parser']['multiline_parser_config'][p.name] = p.value


def write_to_yaml(result: dict, path: str, name: str) -> None:
    """Writes created result dictionary to a yaml file."""
    with open(f'{path}/{name}.yaml', 'w') as f:
        yaml.dump(result, f)


def read_file(path: str) -> str:
    """Returns contents of file at given path."""
    with open(path, 'rt') as f:
        return f.read()


if __name__ == '__main__':
    master_path, file_name = sys.argv[1], sys.argv[2]
    config_json = sys.argv[-1]
    yaml_dict = extract_root_dirs(
        json_format.Parse(config_json, config_pb2.Directive()))
    write_to_yaml(yaml_dict, master_path, file_name)
