FROM python:3.12.0-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . /app

ENV PYTHONPATH=/app

CMD ["python", "db_cleaner/db_cleaner.py"]