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
  [--unified_agent_log_level level] [--unified_agent_log_dirpath path]
  path/to/config/file path/to/output/directory
```
