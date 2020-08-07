"""Converts fields of a fluentd config file to a master agent config file.

Usage: To run just this file:
    python3 -m config_converter.config_mapper.config_mapper
    <master path> <file name> <log level> <log filepath>
    <master agent log level> <master agent log dirpath> <config json>
Where:
    master path: directory to store master agent config file in
    file name: what you want to name the master agent file
    config json: string of fluentd config parsed into a json format
"""

import json
import logging
import os
import sys
from pathlib import Path
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


def _initialize_stats(directive: config_pb2.Directive) -> dict:
    """Initializes the stats dict to print out."""
    stats = {
        'attributes_num': _get_aggregated_num_attributes(directive),
        'attributes_recognized': 0,
        'attributes_unrecognized': 0,
        'attributes_skipped': 0,
        'entities_num': _get_num_sub_entities(directive),
        'entities_skipped': 0,
        'entities_unrecognized': 0,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 0,
        'entities_recognized_failure': 0,
        'warning_logs': 0,
        'error_logs': 0
    }
    return stats


def _get_aggregated_num_attributes(directive: config_pb2.Directive) -> int:
    """Takes a directive, returns total number of attributes in all sub
    directives and at the current level."""
    num_attrs = len(list(directive.params))
    for nested_directive in directive.directives:
        num_attrs += _get_aggregated_num_attributes(nested_directive)
    return num_attrs


def _get_num_sub_entities(directive: config_pb2.Directive) -> int:
    """Takes a directive, returns total number of sub directives
    (excluding itself)."""
    num_ents = len(list(directive.directives))
    for nested_directive in directive.directives:
        num_ents += _get_num_sub_entities(nested_directive)
    return num_ents


def extract_root_dirs(config_obj: config_pb2.Directive) -> tuple:
    """Checks all dirs, maps with corresponding params if supported."""
    logs_module = dict()
    result = {'logs_module': logs_module}
    stats = _initialize_stats(config_obj)
    plugin_prefix_map = {'source': 'in_'}
    dir_name_map = {'source': 'sources'}
    # these dicts can be updated when more plugins are supported
    for directive in config_obj.directives:
        if directive.name not in plugin_prefix_map:
            stats['entities_skipped'] += 1
            stats['attributes_skipped'] += _get_aggregated_num_attributes(
                directive)
            logging.warning(
                'Skip mapping %s due to missing functionality in master agent',
                directive.name)
            stats['warning_logs'] += 1
            continue
        try:
            plugin_type = next(param.value for param in directive.params
                               if param.name == '@type')
        except StopIteration:
            logging.error('Invalid configuration - missing @type param')
            stats['error_logs'] += 1
            sys.exit()
        plugin_name = plugin_prefix_map[directive.name] + plugin_type
        if plugin_name not in _SUPPORTED_PLUGINS:
            stats['entities_unrecognized'] += 1
            stats['attributes_unrecognized'] += _get_aggregated_num_attributes(
                directive)
            logging.error('We do not know plugin %s', plugin_name)
            stats['error_logs'] += 1
        else:
            plugin_dir = dir_name_map[directive.name]
            if plugin_dir not in logs_module:
                logs_module[plugin_dir] = []
            current_attribute_count = stats['attributes_recognized']
            # stats are updated after converting plugin
            logs_module[plugin_dir].append(
                _convert_plugin(directive, plugin_name, stats))
            current_dir_attribute_count: int = _get_aggregated_num_attributes(
                directive)
            if (stats['attributes_recognized'] == current_attribute_count +
                    current_dir_attribute_count):
                stats['entities_recognized_success'] += 1
            elif stats['attributes_recognized'] == current_attribute_count:
                stats['entities_recognized_failure'] += 1
            else:
                stats['entities_recognized_partial'] += 1
            try:
                result['logging_level'] = next(param.value
                                               for param in directive.params
                                               if param.name == '@log_level')
                stats['attributes_recognized'] += 1
            except StopIteration:
                continue
    return (result, stats)


def _convert_plugin(directive: config_pb2.Directive, plugin: str,
                    stats: dict) -> dict:
    """Returns dict of mapped fields and values.

    Cases on type of plugin, calls corresponding mapping function, which
    returns a new dict of master agent fields and their values.

    Args:
        directive: an instance of config_pb2.Directive.
        plugin: a string which indicates the plugin of the directive.
        stats: a dict of all the stats to record, and gets updated to
          reflect the current directive too within this function.

    Returns:
        A dict mapping field names of the master agent to the corresponding
        values. It may not include some fields if they couldn't be translated.

    Raises:
        StopIteration: An error occured while parsing d due to missing @tag.
    """
    result = dict()
    plugin_type_map = {'tail': 'file'}
    plugin_type = next(param.value for param in directive.params
                       if param.name == '@type')
    result['type'] = plugin_type_map[plugin_type]
    try:
        result['name'] = next(param.value for param in directive.params
                              if param.name == 'tag')
    except StopIteration:
        logging.error('Invalid configuration - missing tag')
        stats['error_logs'] += 1
        sys.exit()
    stats['attributes_recognized'] += 2
    if plugin == 'in_tail':
        result[f'{result["type"]}_{directive.name}_config']: dict = \
                _convert_in_tail(directive, stats)
    return result


def _convert_in_tail(directive: config_pb2.Directive, stats: dict) -> dict:
    """Returns dict of mapped fields and values for in_tail plugin.

    Parses a directive of in_tail plugin, cases on fields, and
    returns a new dict of mapped fields and their values.

    Args:
        directive: an instance of config_pb2.Directive.
        stats: a dict of all the stats to record, and gets updated to
          reflect the current directive too within this function.

    Returns:
        A dict mapping field names of the master agent to the corresponding
        values. It may not include some fields if they couldn't be translated.
    """
    fields = dict()
    # these fields may not belong to the same level, have a 1:1 mapping, etc
    # https://docs.fluentd.org/parser/multiline - shows formatN works for
    # 1 <= N <= 20
    special_fields = [
        'format', 'format_firstline', '@type', 'multiline_flush_interval',
        'expression'
    ] + [f'format{i}' for i in range(1, 21)]
    for param in directive.params:
        if param.name in {'@type', 'tag', '@log_level'}:
            continue
        if param.name == 'exclude_path':
            fields['exclude_path'] = param.value
            stats['attributes_recognized'] += 1
        elif param.name == 'path':
            fields['path'] = param.value
            stats['attributes_recognized'] += 1
        elif param.name == 'path_key':
            fields['path_field_name'] = param.value
            stats['attributes_recognized'] += 1
        elif param.name == 'pos_file':
            fields['checkpoint_file'] = param.value
            stats['attributes_recognized'] += 1
        elif param.name == 'refresh_interval':
            fields['refresh_interval'] = int(param.value)
            stats['attributes_recognized'] += 1
        elif param.name == 'rotate_wait':
            fields['rotate_wait'] = int(param.value)
            stats['attributes_recognized'] += 1
        elif param.name in special_fields:
            _convert_parse_dir(fields, param)
            stats['attributes_recognized'] += 1
        elif param.name in _UNSUPPORTED_FIELDS:
            stats['attributes_skipped'] += 1
            logging.warning(
                'Skip mapping %s due to missing functionality in master agent',
                param.name)
            stats['warning_logs'] += 1
        else:
            stats['attributes_unrecognized'] += 1
            logging.error('%s is an unknown field', param.name)
            stats['error_logs'] += 1
    for nested_directive in directive.directives:
        if nested_directive.name == 'parse':
            current_attribute_count = stats['attributes_recognized']
            for nested_param in nested_directive.params:
                if nested_param.name in special_fields:
                    _convert_parse_dir(fields, nested_param)
                    stats['attributes_recognized'] += 1
                else:
                    stats['attributes_unrecognized'] += 1
                    stats['error_logs'] += 1
            current_dir_attribute_count: int =\
                _get_aggregated_num_attributes(nested_directive)
            if (stats['attributes_recognized'] == current_attribute_count +
                    current_dir_attribute_count):
                stats['entities_recognized_success'] += 1
            elif stats['attributes_recognized'] == current_attribute_count:
                stats['entities_recognized_failure'] += 1
            else:
                stats['entities_recognized_partial'] += 1
        else:
            stats['entities_unrecognized'] += 1
            logging.error('%s is an unknown directive', nested_directive.name)
            stats['error_logs'] += 1
    return fields


def _convert_parse_dir(specific: dict, param: config_pb2.Param) -> None:
    """Create parser dir in master agent config."""
    parser_type_map = {
        'multiline': 'multiline',
        'regex': 'regex',
        'apache2': 'regex',
        'apache_error': 'regex',
        'json': 'json',
        'nginx': 'regex'
    }
    if param.name == 'format' and param.value == 'none':
        return  # special case of formatting
    specific['parser'] = specific.get('parser', dict())
    if param.name == 'expression':
        if 'regex_parser_config' not in specific['parser']:
            specific['parser']['regex_parser_config'] = dict()
        specific['parser']['regex_parser_config'][param.name] = param.value
    elif param.name == 'format' or param.name == '@type':
        if param.value not in parser_type_map:
            logging.error('Unknown parser format type %s', param.value)
        else:
            specific['parser']['type'] = parser_type_map[param.value]
    else:
        if 'multiline_parser_config' not in specific['parser']:
            specific['parser']['multiline_parser_config'] = dict()
        if param.name in [f'format{i}' for i in range(1, 21)]:
            f_num = param.name[6:]
            specific['parser']['multiline_parser_config'][f'format_{f_num}']\
                    = param.value
        elif param.name == 'multiline_flush_interval':
            specific['parser']['multiline_parser_config']['flush_interval']\
                    = int(param.value)
        else:
            specific['parser']['multiline_parser_config'][param.name]\
                    = param.value


def write_to_yaml(result: dict, path: str, name: str) -> None:
    """Writes created result dictionary to a yaml file."""
    with open(f'{path}/{name}.yaml', 'w') as f:
        yaml.dump(result, f)


def initialize_logger(level: str, path: str) -> None:
    """Sets up logger with level and filepath."""
    numeric_level = getattr(logging, level.upper(), None)
    log_directory = os.path.dirname(path)
    if not os.path.isdir(log_directory):
        os.makedirs(log_directory)
    Path(path).touch(exist_ok=True)
    logging.basicConfig(filename=path, level=numeric_level)


if __name__ == '__main__':
    agent_path, file_name, log_level = sys.argv[1], sys.argv[2], sys.argv[3]
    log_filepath, agent_log_level = sys.argv[4], sys.argv[5]
    agent_log_dirpath, config_json = sys.argv[6], sys.argv[7]
    initialize_logger(log_level, log_filepath)
    (yaml_dict, stats_output) = extract_root_dirs(
        json_format.Parse(config_json, config_pb2.Directive()))
    yaml_dict['logging_level'] = yaml_dict.get('logging_level',
                                               agent_log_level)
    yaml_dict['log_file_path'] = agent_log_dirpath
    write_to_yaml(yaml_dict, agent_path, file_name)
    print(json.dumps(stats_output, indent=2))
