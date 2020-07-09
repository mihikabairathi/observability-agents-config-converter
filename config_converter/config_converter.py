import config_converter.config_pb2 as config_pb2
import copy
import yaml
import sys
from google.protobuf import json_format
import subprocess


def read_file(path):
    with open(path, 'rt') as f:
        return f.read()


class ConfigConverter():
    def __init__(self):
        self.result = {'logs_module': {}}
        self.create_mapping_info()
        self.config_obj = self.get_object()
        self.extract_root_dirs()
        self.write_to_yaml()
        subprocess.run(['rm', f'{sys.argv[-1]}/config.json'])

    def write_to_yaml(self):
        with open(sys.argv[-1] + '/config.yaml', 'w') as f:
            yaml.dump(self.result, f)

    def extract_root_dirs(self):
        # checks root dirs, maps with corresponding params if supported
        plugin_prefix_map = {
            'source': 'in_',
            'match': 'out_'
        }  # can be updated when more plugins supported
        directive_name_map = {
            'source': 'sources',
            'match': 'output'
        }  # can be updated when more plugins supported
        for d in self.config_obj.directives:
            for p in d.params:
                if p.name == '@type':
                    if d.name not in plugin_prefix_map:
                        print("currently don't support plugins of " + d.name)
                        break
                    plugin = plugin_prefix_map[d.name] + p.value
                    if plugin in self.supported_plugins:
                        self.result['logs_module'][directive_name_map[d.name]]\
                                = self.result['logs_module'].get(
                                        directive_name_map[d.name], [])
                        cur = self.plugin_convert(d, self.outer_map[d.name],
                                                  p.value,
                                                  self.main_map[plugin],
                                                  self.special_map[plugin],
                                                  self.supported_dirs[plugin])
                        self.result['logs_module'][directive_name_map[d.name]]\
                                .append(cur)
                    elif plugin in self.unsupported_plugins:
                        print("we dont support plugin " + plugin)
                    else:
                        print("we dont know plugin " + plugin)

    def plugin_convert(self, d, outer_map, plugin_type, main_map,
                       special_params, supported_dirs):
        cur = {}
        plugin_type_map = {'tail': 'file'}
        outer_map_copy = copy.copy(outer_map)
        for p in d.params:
            if p.name in outer_map:
                if p.name == '@type':
                    cur[outer_map[p.name]] = plugin_type_map[p.value]
                else:
                    cur[outer_map[p.name]] = p.value
                outer_map.pop(p.name)
        if outer_map != {}:
            print('invalid configuration')
            exit()
        specific = {}
        for p in d.params:
            if p.name not in outer_map_copy:
                if p.name in self.unsupported_fields:
                    print(f'parameter {p.name} cant be converted')
                elif p.name in special_params:
                    self.map_special_fields(specific, p)
                elif p.name not in main_map:
                    print(f'parameter {p.name} is unknown')
                else:
                    specific[main_map[p.name]] = p.value
        for nd in d.directives:
            if nd.name not in supported_dirs:
                print(f'directive {nd.name} is not supported')
            else:
                for np in nd.params:
                    self.map_special_fields(specific, np)
        cur[f'{cur["type"]}_{d.name}_config'] = specific
        return cur

    def map_special_fields(self, specific, p):
        # case on p with all special_map dicts
        # call corresponding function to map
        if p.name in self.special_map['in_tail']:
            self.parser_dir(specific, p)

    def parser_dir(self, specific, p):
        # create parser dir in master config
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
                    specifiv['parser'].get('regex_parser_config', {})
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

    def get_object(self):
        # run ruby exec file and get message object
        return_arg = \
            subprocess.run(
                ['config_converter/config_parser_ruby/bin/' +
                 'config_parser'] + sys.argv[1:])
        if return_arg.returncode != 0:
            exit()
        return json_format.Parse(read_file(sys.argv[-1] + '/config.json'),
                                 config_pb2.Directive())

    def create_mapping_info(self):
        # dictionary of dictionaries - one per plugin
        # each dict contains fields that stay in the current level only
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
        # dictionary of lists - one per plugin
        # each list contains fields that need to be treated differently
        self.special_map = {
            'in_tail': [
                'format', 'format_firstline', '@type',
                'multiline_flush_interval', 'expresssion'
            ] + [f'format{i}' for i in range(1, 21)]
        }
        # dictionary of dictionaries - one per main plugin type (source, match)
        # each dict contains fields that go in the upper level
        self.outer_map = {'source': {'tag': 'name', '@type': 'type'}}
        # dictionary of lists - one per plugin
        # each list contains known and allowed sub directives
        self.supported_dirs = {'in_tail': ['parse']}
        # list of fields that we know we cannot convert
        self.unsupported_fields = [
            'emit_unmatched_lines', 'enable_stat_watcher',
            'enable_watch_timer', 'encoding', 'from_encoding',
            'ignore_repeated_permission_error', 'limit_recently_modified',
            'open_on_every_update', 'path_timezone',
            'pos_file_compaction_interval', 'read_from_head',
            'read_lines_limit', 'skip_refresh_on_startup'
        ]
        # plugins that we know how to convert
        self.supported_plugins = ['in_tail']
        # plugins we know exist but cannot support at the time
        self.unsupported_plugins = ['in_forward', 'in_syslog']
