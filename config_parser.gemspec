# frozen_string_literal: true

Gem::Specification.new do |s|
  s.name = 'config_parser'
  s.version = '0.0.0'
  s.date = '2020-06-14'
  s.summary = 'Parser for fluentd configuration files'
  s.description =
    'Parser for fluentd configuration files, which
  will take a path to a config file and parse it, and output the parsed
  information as a .json file to a specified directory'
  s.authors = ['Mihika Bairathi']
  s.email = ['mihikab@google.com']
  s.homepage =
    'https://github.com/googleinterns/observability-agents-config-converter'
  s.license = 'Apache-2.0'
  s.executables << 'config_parser'
  s.files = ['lib/config_parser.rb', 'lib/config_pb.rb']
  s.add_runtime_dependency 'fluentd', '1.11.0'
  s.add_development_dependency 'rake', '13.0.1'
  s.add_development_dependency 'rubocop', '0.85.0'
  s.add_runtime_dependency 'google-protobuf', '3.12.2'
  s.add_runtime_dependency 'OptionParser', '0.5.1'
  s.add_development_dependency 'test-unit', '3.3.6'
end
