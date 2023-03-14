FROM python:3.9.5-slim-buster

WORKDIR /app

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt


COPY . .

EXPOSE 5000 5005 5555

CMD [ "python3", "-u", "app.py"]