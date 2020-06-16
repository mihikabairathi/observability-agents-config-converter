# frozen_string_literal: true

require 'fluent/config/v1_parser'
require 'optparse'
require_relative 'config_pb'

# Accepts a file path and prints out parsed version
class ConfigParser
  def initialize(argv = ARGV)
    @argv = argv
    @ruby_parse = nil # default - won't parse ruby code in a config file
    prepare_input_parser
    input_validation
    @file_parse = parse_config
    @proto_obj = proto_config(@file_parse)
    File.write('../json/config.json', Config::Directive.encode_json(@proto_obj))
  end

  # builds the parser to accept file path
  def prepare_input_parser
    @input_parser = OptionParser.new
    @input_parser.banner = "\nConfig Migration Tool\nUsage: #{$PROGRAM_NAME} " \
      "path/to/file\nOutput: Parsed version of config file\nArguments:"
    @input_parser.on('-r', '--ruby', 'Parse Ruby Code') do
      @ruby_parse = Kernel.binding
    end
    @input_parser.parse!(@argv)
  rescue StandardError => e
    usage(e)
    exit(false)
  end

  # explains how to run the file
  def usage(message = nil)
    puts @input_parser.to_s
    puts "\nError: #{message}" if message
  end

  # parses the arguments, quits program if arguments are invalid
  def input_validation
    raise 'Must specify path of file' if @argv.empty?
    raise 'Only one argument is needed' if @argv.size > 1
    raise 'Enter a valid file path' unless File.exist?(@argv[0])
  rescue StandardError => e
    usage(e)
    exit(false)
  end

  # extracts required information and parses the config file
  def parse_config
    file_str = File.read(@argv[0])
    file_name = File.basename(@argv[0])
    file_dir = File.dirname(@argv[0])
    Fluent::Config::V1Parser.parse(file_str, file_name, file_dir, @ruby_parse)
  rescue StandardError => e
    puts 'An error occured while parsing.\n'
    usage(e)
    exit(false)
  end

  # stores name, attributes, elements of each element of config with proto
  def proto_config(ele_obj)
    ele_dir = Config::Directive.new
    ele_dir.name = ele_obj.name
    ele_dir.args = ele_obj.arg
    ele_obj.each do |n, v|
      ele_dir.params.push(Config::Param.new(name: n, value: v))
    end
    ele_obj.elements.each do |d|
      ele_dir.directives.push(proto_config(d))
    end
    ele_dir
  end
end

ConfigParser.new
