"""Program that converts a fluentd config file to a master agent config file.

Usage: Run the exec file in the bin folder with 2 arguments - the
path to the config file to migrate, and a directory to store the output
master agent config file in.

To do:
1. Improve the cli. Include a --help option. Allow optional args like
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
import os
import subprocess
import yaml
from google.protobuf import json_format
import config_converter.config_pb2 as config_pb2


def read_file(path):
    """Returns content of file at path."""
    with open(path, 'rt') as f:
        return f.read()


def get_object():
    """Run ruby exec file and get message object."""
    try:
        subprocess.run(
            ['config_converter/config_parser_ruby/bin/' + 'config_parser'] +
            sys.argv[1:],
            check=True)
    except:
        sys.exit()
    return json_format.Parse(read_file(sys.argv[-1] + '/config.json'),
                             config_pb2.Directive())
 

def write_to_yaml(result):
    """Writes created result dictionary to a yaml file."""
    file_name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    with open(f'{sys.argv[-1]}/{file_name}.yaml', 'w') as f:
        yaml.dump(result, f)


class ConfigConverter():
    """Class containing tools to map fluentd fields to master agent fields."""
    def __init__(self):
        self.result = {'logs_module': {}}
        self.create_mapping_info()
        self.config_obj = get_object()
        self.extract_root_dirs()
        write_to_yaml(self.result)
        subprocess.run(['rm', f'{sys.argv[-1]}/config.json'], check=True)

    def extract_root_dirs(self):
        """Checks root dirs, maps with corresponding params if supported."""
        plugin_prefix_map = {'source': 'in_', 'match': 'out_'}
        dir_name_map = {
            'source': 'sources',
            'match': 'output'
        }  # these dicts can be updated when more plugins supported
        for d in self.config_obj.directives:
            for p in d.params:
                if p.name == '@type':
                    if d.name not in plugin_prefix_map:
                        print("currently don't support plugins of " + d.name)
                        break
                    plugin = plugin_prefix_map[d.name] + p.value
                    if plugin in self.supported_plugins:
                        self.result['logs_module'][dir_name_map[d.name]] = \
                                self.result['logs_module'].get(
                                    dir_name_map[d.name], [])
                        cur = self.plugin_convert(d, plugin)
                        self.result['logs_module'][dir_name_map[d.name]]\
                                .append(cur)
                    elif plugin in self.unsupported_plugins:
                        print("we dont support plugin " + plugin)
                    else:
                        print("we dont know plugin " + plugin)

    def plugin_convert(self, d, plugin):
        """Uses mapping rules passed to function to map all fields."""
        cur = {}
        outer_map = self.outer_map[d.name]
        main_map = self.main_map[plugin]
        special_params = self.special_map[plugin]
        supported_dirs = self.supported_dirs[plugin]
        plugin_type_map = {'tail': 'file'}
        outer_map_copy = copy.copy(outer_map)
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
                if p.name in self.unsupported_fields:
                    print(f'parameter {p.name} cant be converted')
                elif p.name in special_params:
                    self.map_special_fields(specific, p, plugin)
                elif p.name not in main_map:
                    print(f'parameter {p.name} is unknown')
                else:
                    specific[main_map[p.name]] = p.value
        for nd in d.directives:
            if nd.name not in supported_dirs:
                print(f'directive {nd.name} is not supported')
            else:
                for np in nd.params:
                    self.map_special_fields(specific, np, plugin)
        cur[f'{cur["type"]}_{d.name}_config'] = specific
        return cur

    def map_special_fields(self, specific, p, plugin):
        """Cases on p with all special_map dict, calls a map function."""
        if p.name in self.special_map[plugin]:
            if plugin == 'in_tail':
                parser_dir(specific, p)

    def create_mapping_info(self):
        """Initializes all the mapping rules."""
        # each sub dict contains fields that stay in the current level only
        self.main_map = {
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
        self.special_map = {
            'in_tail': [
                'format', 'format_firstline', '@type',
                'multiline_flush_interval', 'expression'
            ] + [f'format{i}' for i in range(1, 21)]
        }
        # dictionary of dictionaries - one per main plugin type (source, match)
        # each dict contains fields that go in the upper level
        self.outer_map = {'source': {'tag': 'name', '@type': 'type'}}
        # each sub list contains known and allowed sub directives
        self.supported_dirs = {'in_tail': ['parse']}
        self.unsupported_fields = [
            'emit_unmatched_lines', 'enable_stat_watcher',
            'enable_watch_timer', 'encoding', 'from_encoding',
            'ignore_repeated_permission_error', 'limit_recently_modified',
            'open_on_every_update', 'path_timezone',
            'pos_file_compaction_interval', 'read_from_head',
            'read_lines_limit', 'skip_refresh_on_startup'
        ]
        self.supported_plugins = ['in_tail']
        self.unsupported_plugins = ['in_forward', 'in_syslog']


def parser_dir(specific, p):
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
        if p.name[-1].isdigit():
            specific['parser']['multiline_parser_config']\
                    ['format_' + p.name[6:]] = p.value
        elif p.name == 'multiline_flush_interval':
            specific['parser']['multiline_parser_config'][p.name[10:]] = \
                    p.value
        else:
            specific['parser']['multiline_parser_config'][p.name] = p.value
