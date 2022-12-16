# undulate

This repository contains files that are needed to run *Undulate* experiments.

## Components

- **builder**, includes **shellog**
- **cluster_control**, includes **shellog**
- **simulient**
- **shiny** (undulate_app)

In addition, for demonstration purposes an app consisting of two components is included as repositories of their own:

- **test_app**
- **test_app_parameters**

The **test_app** consists of two parts: the main component, named **test_app** similarly to the application, provides a frontend. When a user request arrives, **test_app** sends a HTTP request to the **test_app_parameters** component. In case of an ongoing experiment, the request may be routed to an experimental variant of **test_app_parameters**. The **test_app** component consequently returns the value returned by **test_app_parameters** to the original caller.

All data recieved and returned by the components is in JSON format.

The end user, in the demonstration a simulated used in **simulient**, is unaware of the inner workings of **test_app**. Instead, the simulated user reacts to the value returned by **test_app** and changes its state and behaviour accordingly. Both the inner state and behaviour are reported to the usage database. Hence, the effect of experimental software can be observed, monitored and reasoned about in the experimentation engine.

## Dependencies

### Nivel2

The *Undulate* framework depends on the *Nivel2* multilevel modelling framework. The Nivel2 project can be found as open source software here:

- [https://version.helsinki.fi/xcese_public/nivel2](https://version.helsinki.fi/xcese_public/nivel2)

The dependencies to *Nivel2* include:

1. The data required by *Undulate* is defined as *Nivel2* entities. This includes the concept of *experiment*. An experiment has an identifier, a name and a description of the experiment in common language. In addition, the experiment defines a number of hypotheses. In addition, the experiment includes the defintion of the control and experimental groups. For futher details on the content of experiment data, see paper under **References**. 
2. Various functions related to running the experiments are implemented as *Nivel2* functions
3. Tasks related to updating experiments, eg. adding new experimental groups based on the results from the experiment run so far, are implemented as *Nivel* observation targets
4. Records of running the functions in the point above are stored as *Nivel2* entities

### Cluster

An experiment is run in a cluster. More specifically, the implementation is based on a [Kubernetes](https://kubernetes.io/) with the [Istio](https://istio.io/) service mesh. There are multiple providers for clusters: one can be purchased as a cloud service. During the development of Undulate, a Kubernetes cluster in Microsoft Azure was used.

As part of **Undulate**, managing the cluster is encapsulated in a component called **cluster_control**. In short, the address and credentials needed to manage the cluster are stored in a instance (container) of **cluster_control**. For additional details on installing the cluster, please refer to the documentation of the **cluster_control** controller in the folder by the same name.

### Simulient

In the absence of actual users that could be used in experiment, the **simulient** project can be used to simulate user behaviour interacting against. Please refer to **simulient** documentation for additional details on how to define configurations that can be used in conjunction with experiments.

### Usage data

The term *usage data* is used to refer to any data that is systematically collected on the usage of the software under experimentation. Usage data may stem from the client application or from some server component, or both. In a production setting, details of how usage data is accrued and its format will envitably vary and no specific schema can imposed on the data.

However, for the purpose of demonstration, the **Undulate** software is based on the **simulient** data schema that is decsribed in more detail under **simulient**.

## Generic modules

The project utilises generic Python files with slight modifications. In more detail, the files are `api.py` and `shellog.py`.

The `api.py` file is a Python file that provides a HTTP API for accessing the component. In its endpoints, the server uses the other generic file, `shellog.py`, to start the actual payload process. The latter file reports to an external endpoint, the **log_data_api** service, the address of which is provided to the component at startup as environment variable. The `shellog.py` process receives the command for the actual payload process as a parameter: the process is started, the output (both `stdout` and `stderr`) from the process is recorded and sent to **log_data_api**. The **shellog** process monitors payload process and observes when it is completed, records its status and sends the all information from the process to **log_data_api**.

The **log_data_api** component writes the data it receives to a centralised database, which enable monitoring and joining data from multiple components.

In this project, the generic files are utilised in the **cluster_control** and **builder** components.

## Setup
### Environment variables and other configuration data
The project components depend on a number of environment variables. These variables are in part shared with other projects, in particular the **nivel2** project. As the environment variables are different for each installation of the projects, these are not included in version control. The assumption is that the variables can be found in `config` folder at the same level with this folder, ie. the root folder of the project. This folder includes the folder `config_template` with templates of the necessary files: the folder can be moved up one level and renamed to config, and the files modified with installation specific data in order to run the software.

### Building the components
In the `script` folder, there is a script `build-images.sh` that simply runs a Docker build for each component in their respective directories.

### Starting the components
In the `script` folder, there is a script `stop-and-start-images.sh` that stops the currently running container (if any) and runs container specific script (`run-<component>.sh`) thereafter.

## Run-time architecture

The components use the following ports:

- **builder**: 5001
- **cluster_control**: 5002
- **ui/nivel-ui**: 5003
- **shiny**: 5005

## Implementation

The application logic of the experimentation is embodied in the following T-SQL (the variant of SQL programming supported by the Microsoft SQL Server) procedures.

### Procedures

- `**xcese.sp_experiment_init** @experiment int, @function int = null`: This procedure is used to initialise the experiment descripbe by the entity `@experiment`. PKTN Must add what does initialisation mean.
- `**xcese.sp_step_experiment_round** @experiment int`: This procedure is run periodically while the experiment runs to check if some experiment groupss or the experiment as a whole can be concluded. The procedure is currently hard coded for the purposes of the sample experiment, but can be extended to support different experimentation strategies. Alternatively, different procedures can be defined for experiment with different strategies.
- `**xcese.sp_experiments_active_get** @format = 'lines'`: This procedure returns a list of active experiments, ie. experiments that currently have at least one experiment group running. This procedure is used for updating the implementation required by various experiment groups to cluster (eg. a Kubernets cluster) running the software under experimentation.
- `**xcese.sp_routings_active_get** @experiment int = null, @service varchar(63) = null`: Returns the rountings (group x service/version) that are currently active ie. used for some active experiment group
- `**xcese.sp_function_history_clear** @function int:` This procedure can be used to claer the run history of an experiment. Clearing the history will save space and speed processing of the experiment entity.

## References

Asikainen, T., & Männistö, T. (2022). Undulate: A framework for data-driven software engineering enabling soft computing. Information and Software Technology, 152, [107039]. [Link](https://doi.org/10.1016/j.infsof.2022.107039)
