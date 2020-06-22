# frozen_string_literal: true

require 'test/unit'
require 'config_parser'
require 'config_pb'
require 'fluent/config/v1_parser'

# tests for config tool
class TestConfigParser < Test::Unit::TestCase
  def test_comments_not_parsed
    expected = Config::Directive.new(
      name: 'ROOT',
      directives: [
        Config::Directive.new(name: 'system', params: [get_param('rpc', '0.0.0:2')]),
        Config::Directive.new(name: 'source', params: [get_param('@type', 'forward')])
      ]
    )
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/comments.conf')) == expected)
  end

  def test_special_characters_parsed_correctly
    expected = Config::Directive.new(
      name: 'ROOT',
      directives: [Config::Directive.new(name: 'source', params: create_params_special)]
    )
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/special.conf')) == expected)
  end

  def test_multiple_directories_parsed_correctly
    expected = Config::Directive.new(
      name: 'ROOT',
      directives: [
        Config::Directive.new(name: 'source', params: [get_param('@type', 'dummy'), get_param('tag', 'test.rr')]),
        Config::Directive.new(name: 'label', args: '@test', directives: [create_match_multiple])
      ]
    )
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/multiple.conf')) == expected)
  end

  def test_embedded_ruby_does_not_get_parsed
    expected = Config::Directive.new(
      name: 'ROOT',
      directives: [
        Config::Directive.new(name: 'source', params: [get_param('@type', 'tail'), get_param('@label', '@raw')]),
        create_match_emb
      ]
    )
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/emb_ruby.conf')) == expected)
  end

  private

  # helper function to create object of message Param
  def get_param(name, value)
    Config::Param.new(name: name, value: value)
  end

  # helper function to create all the params of object source
  def create_params_special
    p1 = get_param('@type', 'tail')
    p2 = get_param('source_host_key', 'host')
    p3 = get_param('tag', 'test')
    p4 = get_param('bind', '0.0.0.0')
    p5 = get_param('dummy', '[{"message":"hello"},{"message":"bye"}]')
    p6 = get_param('dummy2', '{"message":"again"}')
    [p1, p2, p3, p4, p5, p6]
  end

  # helper function to make Directive object secondary
  def create_secondary_emb
    Config::Directive.new(
      name: 'secondary',
      params: [
        get_param('@type', 'secondary_file'),
        get_param('basename', '${tag}_%Y%m%d%L_${message}')
      ]
    )
  end

  # helper function to make Directive object match
  def create_match_emb
    Config::Directive.new(
      name: 'match',
      args: 'test',
      directives: [create_secondary_emb],
      params: [
        get_param('@type', 'forward'),
        get_param('command', "ruby -e 'STDOUT.sync = true; proc = ->(){line = STDIN.readline.chomp;}'")
      ]
    )
  end

  # helper function to create Directive object match
  def create_match_multiple
    Config::Directive.new(
      name: 'match',
      args: 'test.copy',
      params: [get_param('@type', 'copy')],
      directives: [
        Config::Directive.new(name: 'store', params: [get_param('@type', 'stdout'), get_param('output', 'json')]),
        Config::Directive.new(name: 'store', params: [get_param('@type', 'stdout'), get_param('output', 'ltsv')]),
        Config::Directive.new(name: 'buffer', args: 'time,tag,memory', params: [get_param('@type', 'memory')])
      ]
    )
  end
end
