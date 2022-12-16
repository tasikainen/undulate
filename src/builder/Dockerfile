FROM python:3.7-alpine3.11

# Install git and bash
RUN apk update && apk upgrade && \
  apk add --no-cache bash git docker-cli

WORKDIR /app

COPY builder.py ./
COPY requirements.txt ./
COPY run.sh ./
COPY shellog.py ./
COPY api.py ./
RUN mkdir temp

RUN chmod +x run.sh

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT [ "./run.sh" ]
