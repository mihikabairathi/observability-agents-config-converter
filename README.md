# Observability Agents Configuration Converter

**This is not an officially supported Google product.**

A command line tool to support migrating configurations of the agents used for
observability.

## Problem

On GCE we have 2 agents for observability: logging and monitoring agents. We
are planning to have new agents. Without a tool, migration from one agent to
another would be error prone and hard to adopt.

## Why is it important?

Developing this tool will increase the confidence of migrating configurations
to new agents, and reduce the friction to adopt the new agents, since
users can will use the migration tool.

## Implementation

This flowchart demonstrates the flow of the program - from initial input to final output

![Image of implementation](https://drive.google.com/file/d/1FtwLUfmytvJdzkXbWcG7wuPuwDK9XBfN/view?usp=sharing)

Here is a document which explains the reasoning behind developing a schema to transfer
data between the two programs as shown above:

https://docs.google.com/document/d/1GDkzjwg-SaVl9VuvmwF0O8cV8SEZGkZmbuV2PfLR3IU/edit?usp=sharing

## Installation Instructions

Run these commands in the config_converter/config_parser/ directory
```
$ gem install bundler
$ bundle install
$ gem build config_parser.gemspec
$ gem install config_parser-0.0.0.gem
```

## How to run

```
$ python3 -m config_script [-h] [--log_level] [--log_filepath]
  [--master_agent_log_level level] [--master_agent_log_dirpath path]
  path/to/config/file path/to/output/directory
```
