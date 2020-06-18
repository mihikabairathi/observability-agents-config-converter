# frozen_string_literal: true

require 'fluent/config/v1_parser'
require 'optparse'
require_relative 'config_pb'

# Accepts a file path and prints out parsed version
class ConfigParser
  def initialize(argv = ARGV)
    @argv = argv
    prepare_input_parser
    input_validation
    @file_parse = parse_config
    @proto_obj = proto_config(@file_parse)
    File.write(@argv[1].to_s + '/config.json',
               Config::Directive.encode_json(@proto_obj))
  end

  # builds the parser to accept file path
  def prepare_input_parser
    @input_parser = OptionParser.new
    @input_parser.banner = "\nConfig Migration Tool\nUsage: #{$PROGRAM_NAME} " \
      "path/to/config/file path/to/output/directory\nOutput: Parsed version " \
      'of config file in a json file'
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
    raise 'Must specify path of config file and output directory' if @argv.size < 2
    raise 'Only two arguments are needed' if @argv.size > 2
    raise 'Enter a valid file path' unless File.exist?(@argv[0])
    raise 'Enter a valid directory' unless Dir.exist?(@argv[1])
  rescue StandardError => e
    usage(e)
    exit(false)
  end

  # extracts required information and parses the config file
  def parse_config
    file_str = File.read(@argv[0])
    file_name = File.basename(@argv[0])
    file_dir = File.dirname(@argv[0])
    eval_context = Kernel.binding
    # overriding function so embedded ruby is not parsed
    def eval_context.instance_eval(code)
      code
    end
    Fluent::Config::V1Parser.parse(file_str, file_name, file_dir, eval_context)
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
