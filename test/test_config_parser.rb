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
      directives: [
        Config::Directive.new(
          name: 'source',
          params: [
            get_param('@type', 'tail'),
            get_param('source_host_key', 'host'),
            get_param('tag', 'test'),
            get_param('bind', '0.0.0.0'),
            get_param('dummy', '[{"message":"hello"},{"message":"bye"}]'),
            get_param('dummy2', '{"message":"again"}')
          ]
        )
      ]
    )
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/special.conf')) == expected)
  end

  def test_multiple_directories_parsed_correctly
    expected = Config::Directive.new(
      name: 'ROOT',
      directives: [
        Config::Directive.new(name: 'source', params: [get_param('@type', 'dummy'), get_param('tag', 'test.rr')]),
        Config::Directive.new(
          name: 'label',
          args: '@test',
          directives: [
            Config::Directive.new(
              name: 'match',
              args: 'test.copy',
              params: [get_param('@type', 'copy')],
              directives: [
                Config::Directive.new(
                  name: 'store',
                  params: [get_param('@type', 'stdout'), get_param('output', 'json')]
                ),
                Config::Directive.new(
                  name: 'store',
                  params: [get_param('@type', 'stdout'), get_param('output', 'ltsv')]
                ),
                Config::Directive.new(
                  name: 'buffer',
                  args: 'time,tag,memory',
                  params: [get_param('@type', 'memory')]
                )
              ]
            )
          ]
        )
      ]
    )
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/multiple.conf')) == expected)
  end

  def test_embedded_ruby_does_not_get_parsed
    expected = Config::Directive.new(
      name: 'ROOT',
      directives: [
        Config::Directive.new(name: 'source', params: [get_param('@type', 'tail'), get_param('@label', '@raw')]),
        Config::Directive.new(
          name: 'match',
          args: 'test',
          directives: [
            Config::Directive.new(
              name: 'secondary',
              params: [get_param('@type', 'secondary_file'), get_param('basename', '${tag}_%Y%m%d%L_${message}')]
            )
          ],
          params: [
            get_param('@type', 'forward'),
            get_param('command', "ruby -e 'STDOUT.sync = true; proc = ->(){line = STDIN.readline.chomp;}'")
          ]
        )
      ]
    )
    assert(ConfigParser.proto_config(ConfigParser.parse_config('test/data/emb_ruby.conf')) == expected)
  end

  private

  # helper function to create object of message Param
  def get_param(name, value)
    Config::Param.new(name: name, value: value)
  end
end
