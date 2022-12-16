FROM python:latest

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY simulient.py /
COPY user.py /
COPY user_factory.py /
COPY timer.py /
COPY server.py /
COPY project_demo.json /
COPY formula_solver.py /
COPY shellog.py /
COPY api.py /

COPY run.sh /
RUN chmod +x run.sh

ENTRYPOINT [ "./run.sh" ]
