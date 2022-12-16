# This is not working
# TODO find a way to authorize kubectl inside the container
FROM python:3.7-alpine3.11

WORKDIR /app

COPY --from=lachlanevenson/k8s-kubectl:latest /usr/local/bin/kubectl /usr/local/bin/kubectl
COPY cluster_control.py ./
COPY requirements.txt ./
COPY run.sh ./
COPY shellog.py ./
COPY api.py ./

# 2022-11-21 This needs to come from the config file, mapped at startup
# COPY k8s-cc5-default-conf ./

RUN pip install -r requirements.txt
RUN mkdir temp
RUN chmod +x run.sh

EXPOSE 5000

ENTRYPOINT [ "./run.sh" ]
