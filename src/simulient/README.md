# simulient

This is **simulient**, a tool for simulating user behaviour that may involve randomness and depend on external systems. Due to the possibility for external dependency, simulient may be used in conjunction with experimentation, in which case the external system is a software running in a cluster that behaves differently for different users (ie. users in experiment groups).

## Synopsis

### Usage

Command line:

```
python simulient.py <configuration.json or endpoint url> <log_new_line(round/entry)> <OPTIONAL time_scale)
                  <OPTIONAL output(file/stdout/database)> <OPTIONAL function_instance_id> <OPTIONAL starting_time (YYYY-mm-dd HH:MM:SS)>
```
On docker:
```
docker build -t simulient .
docker run simulient <configuration.json or endpoint url> <log_new_line(round/entry)> <OPTIONAL time_scale)
                     <OPTIONAL output(file/stdout/database)> <OPTIONAL function_instance_id> <OPTIONAL starting_time (YYYY-mm-dd HH:MM:SS)>
```

## Overview

The purpose of the _simulient_ component is to generate data representing the actions of human users. Using simulation enables generating large amounts of data with known statistical properties. Increasingly complex statistical models can be implemented using by creating many user groups and users, each with their own parameters.

## Setup
### Environment variables
The project components depend on a number of environment variables. These variables are in part shared with other projects and are place in `config` folder at the same level as the project folder (`nivel2` and `undulate`).

## Run-time environment

Simulient runs by default in port **5006**. Simulient provides an API that can be used to start a simulient run with the given parameters or to stop a running instance.

The main output of **simulient** are the simulation results that are sent to the **log_data_api** component.

In addition, simulient is run using `shellog` (implemented in `shellog.py` included in this project), a component that captures the `stdout` and `stderr` streams of the **simulient** process.
