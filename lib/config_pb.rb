# frozen_string_literal: true

# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: config.proto

require 'google/protobuf'

Google::Protobuf::DescriptorPool.generated_pool.build do
  add_file('config.proto', syntax: :proto3) do
    add_message 'Config.Directive' do
      optional :name, :string, 1
      optional :args, :string, 2
      repeated :directives, :message, 3, 'Config.Directive'
      repeated :params, :message, 4, 'Config.Param'
    end
    add_message 'Config.Param' do
      optional :name, :string, 1
      optional :value, :string, 2
    end
  end
end

module Config
  Directive = ::Google::Protobuf::DescriptorPool.generated_pool.lookup('Config.Directive').msgclass
  Param = ::Google::Protobuf::DescriptorPool.generated_pool.lookup('Config.Param').msgclass
end
