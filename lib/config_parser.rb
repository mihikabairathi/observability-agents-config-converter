# frozen_string_literal: true

require 'fluent/config/v1_parser'
require 'optparse'

# Accepts a file path and prints out parsed version
class ConfigParser
  def initialize(argv = ARGV)
    @argv = argv
    prepare_input_parser
    input_validation
    @file_parse = parse_configuration
    print_configuration(@file_parse)
  end

  def prepare_input_parser
    # builds the parser to accept file path
    @input_parser = OptionParser.new
    @input_parser.banner = "\nPrint-Config-File Tool\nUsage: #{$PROGRAM_NAME} " \
      "path/to/file\nOutput: Parsed version of config file"
    @input_parser.parse!(@argv)
  end

  def usage(message = nil)
    # explains how to run the file
    puts @input_parser.to_s
    puts "\nError: #{message}" if message
  end

  def input_validation
    # parses the arguments, quits program if arguments are invalid
    raise 'Must specify path of file' if @argv.empty?
    raise 'Only one argument is needed' if @argv.size > 1
    raise 'Enter a valid file path' unless File.exist?(@argv[0])
  rescue StandardError => e
    usage(e)
    exit(false)
  end

  def parse_configuration
    # extracts required information and parses the config file
    file_str = File.read(@argv[0])
    file_name = File.basename(@argv[0])
    file_dir = File.dirname(@argv[0])
    Fluent::Config::V1Parser.parse(file_str, file_name,
                                   file_dir, Kernel.binding)
  rescue StandardError => e
    usage(e)
    exit(false)
  end

  def print_configuration(ele_obj, depth = 0)
    # displays name, attributes, elements of each element in config file
    blank = ' ' * depth
    # name
    puts "#{blank}name : #{ele_obj.name}"
    # attributes
    ele_obj.each do |a|
      puts "#{blank}attr #{a[0]} : #{a[1]}"
    end
    puts "#{blank}(no attributes)" if ele_obj.empty?
    # elements
    ele_obj.elements.each do |e|
      puts "#{blank}element :"
      # recursive call to display nested elements
      print_configuration(e, depth + 4)
    end
  end
end

ConfigParser.new
