FROM rocker/shiny:latest


## install debian packages
RUN apt-get update -qq && apt-get -y --no-install-recommends install \
    libxml2-dev \
    libcairo2-dev \
    libsqlite3-dev \
    libmariadbd-dev \
    libpq-dev \
    libssh2-1-dev \
    unixodbc-dev \
    libcurl4-openssl-dev \
    libssl-dev

## update system libraries
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean

# copy necessary files
## app folder
# Use a mount instead, so that it is possible to update the app
# without rebuilding the image (slow)
# COPY /example-app ./app

## renv.lock file

# install renv & restore packages
RUN Rscript -e 'install.packages("renv")'
RUN Rscript -e 'install.packages("httr")'
RUN Rscript -e 'install.packages("ggplot2")'
RUN Rscript -e 'install.packages("plotly")'
RUN Rscript -e 'install.packages("RColorBrewer")'
RUN Rscript -e 'renv::restore()'

# expose port
# EXPOSE 3838

# run app on container start
# CMD ["R", "-e", "shiny::runApp('/app', host = '0.0.0.0', port = 5005)"]
CMD shiny-server
