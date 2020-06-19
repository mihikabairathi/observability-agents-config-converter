# frozen_string_literal: true

require 'test/unit'
require 'config_parser'
require 'config_pb'
require 'fluent/config/v1_parser'

# tests for config tool
class TestConfigParser < Test::Unit::TestCase
  # helper function to create object of message Param
  def get_param(name, value)
    Config::Param.new(name: name, value: value)
  end

  # test to ensure comments are not parsed
  def test_comments
    dir1 = Config::Directive.new(name: 'system', params: [get_param('rpc', '0.0.0:2')])
    dir2 = Config::Directive.new(name: 'source', params: [get_param('@type', 'forward')])
    comment = Config::Directive.new(name: 'ROOT', directives: [dir1, dir2])
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/comments.conf')) == comment)
  end

  # test to check special characters are parsed correctly
  def test_special
    p1 = get_param('@type', 'tail')
    p2 = get_param('source_host_key', 'host')
    p3 = get_param('tag', 'test')
    p4 = get_param('bind', '0.0.0.0')
    p5 = get_param('dummy2', '{"message":"again"}')
    p6 = get_param('dummy', '[{"message":"hello"},{"message":"bye"}]')
    special = Config::Directive.new(name: 'ROOT')
    special.directives.push(Config::Directive.new(name: 'source', params: [p1, p2, p3, p4, p6, p5]))
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/special.conf')) == special)
  end

  # helper function to create Directive object match
  def create_match_multiple
    stdout = get_param('@type', 'stdout')
    store = Config::Directive.new(name: 'store', params: [stdout, get_param('output', 'json')])
    store2 = Config::Directive.new(name: 'store', params: [stdout, get_param('output', 'ltsv')])
    buffer = Config::Directive.new(name: 'buffer', args: 'time,tag,memory', params: [get_param('@type', 'memory')])
    match = Config::Directive.new(name: 'match', args: 'test.copy', directives: [store, store2, buffer])
    match.params.push(Config::Param.new(name: '@type', value: 'copy'))
    match
  end

  # test to check nested directives are parsed correctly
  def test_multiple
    source = Config::Directive.new(name: 'source', params: [get_param('@type', 'dummy'), get_param('tag', 'test.rr')])
    match = create_match_multiple
    label = Config::Directive.new(name: 'label', args: '@test', directives: [match])
    multiple = Config::Directive.new(name: 'ROOT', directives: [source, label])
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/multiple.conf')) == multiple)
  end

  # helper function to make Directive object secondary
  def create_secondary
    basename = get_param('basename', '${tag}_%Y%m%d%L_${message}')
    Config::Directive.new(name: 'secondary', params: [get_param('@type', 'secondary_file'), basename])
  end

  # helper function to make Directive object match
  def create_match_emb
    comm = get_param('command', "ruby -e 'STDOUT.sync = true; proc = ->(){line = STDIN.readline.chomp;}'")
    match = Config::Directive.new(name: 'match', args: 'test', params: [get_param('@type', 'forward'), comm])
    match.directives.push(create_secondary)
    match
  end

  # test to make sure embedded ruby is not parsed
  def test_emb
    source = Config::Directive.new(name: 'source', params: [get_param('@type', 'tail'), get_param('@label', '@raw')])
    emb = Config::Directive.new(name: 'ROOT', directives: [source, create_match_emb])
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/emb_ruby.conf')) == emb)
  end
end
