FROM python:3.8

ADD requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN chmod 777 -R /app

WORKDIR /app
ENTRYPOINT ["python", "run.py"]
