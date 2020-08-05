"""Converts fields of a fluentd config file to a master agent config file.

Usage: To run just this file:
    python3 -m config_converter.config_mapper.config_mapper
    <master path> <file name> <log level> <log filepath>
    <unified agent log level> <unified agent log dirpath> <config json>
Where:
    master path: directory to store master agent config file in
    file name: what you want to name the master agent file
    config json: string of fluentd config parsed into a json format
To do:
    1. Update stats dict with log fields
"""

import json
import logging
import os
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


def _initialize_stats(d: config_pb2.Directive) -> dict:
    """Initializes the stats dict to print out."""
    stats = {
        'attributes_num': _get_aggregated_num_attributes(d),
        'attributes_recognized': 0,
        'attributes_unrecognized': 0,
        'attributes_skipped': 0,
        'entities_num': _get_num_sub_entities(d),
        'entities_skipped': 0,
        'entities_unrecognized': 0,
        'entities_recognized_success': 0,
        'entities_recognized_partial': 0,
        'entities_recognized_failure': 0
    }
    return stats


def _get_aggregated_num_attributes(d: config_pb2.Directive) -> int:
    """Takes a directive, returns total number of attributes in all sub
    directives and at the current level."""
    num_attrs = len(list(d.params))
    for nd in d.directives:
        num_attrs += _get_aggregated_num_attributes(nd)
    return num_attrs


def _get_num_sub_entities(d: config_pb2.Directive) -> int:
    """Takes a directive, returns total number of sub directives
    (excluding itself)."""
    num_ents = len(list(d.directives))
    for nd in d.directives:
        num_ents += _get_num_sub_entities(nd)
    return num_ents


def extract_root_dirs(config_obj: config_pb2.Directive) -> tuple:
    """Checks all dirs, maps with corresponding params if supported."""
    logs_module = dict()
    result = {'logs_module': logs_module}
    stats = _initialize_stats(config_obj)
    plugin_prefix_map = {'source': 'in_'}
    dir_name_map = {'source': 'sources'}
    # these dicts can be updated when more plugins are supported
    for d in config_obj.directives:
        if d.name not in plugin_prefix_map:
            stats['entities_skipped'] += 1
            stats['attributes_skipped'] += _get_aggregated_num_attributes(d)
            logging.warning('Currently we don\'t support plugins of %s',
                            d.name)
            continue
        try:
            plugin_type = next(p.value for p in d.params if p.name == '@type')
        except StopIteration:
            logging.error('Invalid configuration - missing @type param')
            sys.exit()
        plugin_name = plugin_prefix_map[d.name] + plugin_type
        if plugin_name not in _SUPPORTED_PLUGINS:
            stats['entities_unrecognized'] += 1
            stats['attributes_unrecognized'] += _get_aggregated_num_attributes(
                d)
            logging.error('We do not know plugin %s', plugin_name)
        else:
            plugin_dir = dir_name_map[d.name]
            if plugin_dir not in logs_module:
                logs_module[plugin_dir] = []
            current_attribute_count = stats['attributes_recognized']
            logs_module[plugin_dir].append(
                _convert_plugin(d, plugin_name, stats))  # stats are updated
            current_dir_attribute_count: int = _get_aggregated_num_attributes(
                d)
            if (stats['attributes_recognized'] == current_attribute_count +
                    current_dir_attribute_count):
                stats['entities_recognized_success'] += 1
            elif stats['attributes_recognized'] == current_attribute_count:
                stats['entities_recognized_failure'] += 1
            else:
                stats['entities_recognized_partial'] += 1
            try:
                result['logging_level'] = next(p.value for p in d.params
                                               if p.name == '@log_level')
                stats['attributes_recognized'] += 1
            except StopIteration:
                continue
    return (result, stats)


def _convert_plugin(d: config_pb2.Directive, plugin: str, stats: dict) -> dict:
    """Returns dict of mapped fields and values.

    Cases on type of plugin, calls corresponding mapping function, which
    returns a new dict of unified agent fields and their values.

    Args:
        d: an instance of config_pb2.Directive.
        plugin: a string which indicates the plugin of the directive.
        stats: a dict of all the stats to record, and gets updated to
          reflect the current directive too within this function.

    Returns:
        A dict mapping field names of the unified agent to the corresponding
        values. It may not include some fields if they couldn't be translated.

    Raises:
        StopIteration: An error occured while parsing d due to missing @tag.
    """
    result = dict()
    plugin_type_map = {'tail': 'file'}
    plugin_type = next(p.value for p in d.params if p.name == '@type')
    result['type'] = plugin_type_map[plugin_type]
    try:
        result['name'] = next(p.value for p in d.params if p.name == 'tag')
    except StopIteration:
        logging.error('Invalid configuration - missing tag')
        sys.exit()
    stats['attributes_recognized'] += 2
    if plugin == 'in_tail':
        result[f'{result["type"]}_{d.name}_config']: dict = \
                _convert_in_tail(d, stats)
    return result


def _convert_in_tail(d: config_pb2.Directive, stats: dict) -> dict:
    """Returns dict of mapped fields and values for in_tail plugin.

    Parses a directive of in_tail plugin, cases on fields, and
    returns a new dict of mapped fields and their values.

    Args:
        d: an instance of config_pb2.Directive.
        stats: a dict of all the stats to record, and gets updated to
          reflect the current directive too within this function.

    Returns:
        A dict mapping field names of the unified agent to the corresponding
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
    for p in d.params:
        if p.name in {'@type', 'tag', '@log_level'}:
            continue
        if p.name == 'exclude_path':
            fields['exclude_path'] = p.value
            stats['attributes_recognized'] += 1
        elif p.name == 'path':
            fields['path'] = p.value
            stats['attributes_recognized'] += 1
        elif p.name == 'path_key':
            fields['path_field_name'] = p.value
            stats['attributes_recognized'] += 1
        elif p.name == 'pos_file':
            fields['checkpoint_file'] = p.value
            stats['attributes_recognized'] += 1
        elif p.name == 'refresh_interval':
            fields['refresh_interval'] = int(p.value)
            stats['attributes_recognized'] += 1
        elif p.name == 'rotate_wait':
            fields['rotate_wait'] = int(p.value)
            stats['attributes_recognized'] += 1
        elif p.name in special_fields:
            _convert_parse_dir(fields, p)
            stats['attributes_recognized'] += 1
        elif p.name in _UNSUPPORTED_FIELDS:
            stats['attributes_skipped'] += 1
            logging.warning(
                '%s cannot be mapped into master agent config file', p.name)
        else:
            stats['attributes_unrecognized'] += 1
            logging.error('%s is an unknown field', p.name)
    for nd in d.directives:
        if nd.name == 'parse':
            current_attribute_count = stats['attributes_recognized']
            for np in nd.params:
                if np.name in special_fields:
                    _convert_parse_dir(fields, np)
                    stats['attributes_recognized'] += 1
                else:
                    stats['attributes_unrecognized'] += 1
            current_dir_attribute_count: int =\
                _get_aggregated_num_attributes(nd)
            if (stats['attributes_recognized'] == current_attribute_count +
                    current_dir_attribute_count):
                stats['entities_recognized_success'] += 1
            elif stats['attributes_recognized'] == current_attribute_count:
                stats['entities_recognized_failure'] += 1
            else:
                stats['entities_recognized_partial'] += 1
        else:
            stats['entities_unrecognized'] += 1
            logging.error('%s is an unknown directive', nd.name)
    return fields


def _convert_parse_dir(specific: dict, p: config_pb2.Param) -> None:
    """Create parser dir in master config."""
    parser_type_map = {
        'multiline': 'multiline',
        'regex': 'regex',
        'apache2': 'regex',
        'apache_error': 'regex',
        'json': 'json',
        'nginx': 'regex'
    }
    if p.name == 'format' and p.value == 'none':
        return  # special case of formatting
    specific['parser'] = specific.get('parser', dict())
    if p.name == 'expression':
        if 'regex_parser_config' not in specific['parser']:
            specific['parser']['regex_parser_config'] = dict()
        specific['parser']['regex_parser_config'][p.name] = p.value
    elif p.name == 'format' or p.name == '@type':
        if p.value not in parser_type_map:
            logging.error('Unknown parser format type %s', p.value)
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
                    = int(p.value)
        else:
            specific['parser']['multiline_parser_config'][p.name] = p.value


def write_to_yaml(result: dict, path: str, name: str) -> None:
    """Writes created result dictionary to a yaml file."""
    with open(f'{path}/{name}.yaml', 'w') as f:
        yaml.dump(result, f)


def initialize_logger(level: str, path: str) -> None:
    """Sets up logger with correct level and filepath."""
    numeric_level = getattr(logging, level.upper(), None)
    log_directory = os.path.dirname(path)
    if not os.path.isdir(log_directory):
        os.makedirs(log_directory)
    if not os.path.isfile(path):
        os.mknod(path)
    logging.basicConfig(filename=path, level=numeric_level)


if __name__ == '__main__':
    master_path, file_name, config_json = sys.argv[1], sys.argv[2], sys.argv[7]
    agent_log_level, agent_log_dirpath = sys.argv[5], sys.argv[6]
    log_level, log_filepath = sys.argv[3], sys.argv[4]
    initialize_logger(log_level, log_filepath)
    (yaml_dict, stats_output) = extract_root_dirs(
        json_format.Parse(config_json, config_pb2.Directive()))
    yaml_dict['logging_level'] = yaml_dict.get('logging_level',
                                               agent_log_level)
    yaml_dict['log_file_path'] = agent_log_dirpath
    write_to_yaml(yaml_dict, master_path, file_name)
    print(json.dumps(stats_output, indent=2))
