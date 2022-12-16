# shiny

The component provides an interactive tool for viewing experiment results.

## Functionality

The component connects to both a *Nivel2* database and a usage data store. From the *Nivel2* database, experiment definitions are fetched. A list of experiments is shown to the user, and the user selects an experiment for viewing from the list. Detailed content of the selected experiment is fetched from the *Nivel2* database: the details include the control and experiment groups. In addition, results data for each group is fetched from the usage database.

The usage data pertains to *variables* and *users* in *user groups*. The variables may be data values directly produced by the instrumented components under experimentation or **simulient**, or computed based on other variables. For a more detailed description, see (Asikainen & Männistö, 2002). The app allows the user to select which user groups and variables should be displayed: the interactive chart is updated accordingnly. The interactive chart is a line chart with time as the *x* axis and variables value as the *y* axis. The chart can be zoomed interactively.

## Running the application

Given the address (host and port) where the application is running, the application can be run be setting the experiment of interest as a part of the address, eg:

http://localhost:5005/?experiment_id=<exp_id>

where `exp_id` is the *Nivel2* entity id representing the experiment of interest.

When run, the application has a login page with hard-coded username and password: `admin` and `xcese`, respectively.

## Implementation

The component is implemented using the [Shiny package](https://cran.r-project.org/web/packages/shiny/index.html), see also the [related Rstudio product](https://shiny.rstudio.com/) of the [R statistical programming language](https://www.r-project.org/).

## Dependencies

The component is intended to use  the **datapi** component of **Nivel2** to access data. Both *Nivel2* data (eg. definitions of experiments and relevant control and other groups) and *usage data* stemming from running the experiments, eg. using **simulient**.

However, the component as such is generic in that other source of data than **datapi** can be used as long as the alternative source provides an API with the same syntax and semantics (data content) as **datapi**.

## Embedding the results

The results app can be embedded in a *Nivel2* entity, eg. in the experimentation type. This enables viewing the experiment results alongside the definition. In addition, the app can be run in standalone mode, ie. outside the context of an entity. In this case, a link to the app can be emdedded to the experiment entity.

## References

Asikainen, T., & Männistö, T. (2022). Undulate: A framework for data-driven software engineering enabling soft computing. Information and Software Technology, 152, [107039]. [Link](https://doi.org/10.1016/j.infsof.2022.107039)
