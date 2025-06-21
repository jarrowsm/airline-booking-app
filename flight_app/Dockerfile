FROM python:3.13.3-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /flight_app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --no-create-home appuser && \
    chown -R appuser:appuser /flight_app
USER appuser

ENTRYPOINT ["python", "manage.py", "runserver", "0.0.0.0:8000", "--insecure"]

