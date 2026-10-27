FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY config ./config
COPY apps ./apps
COPY engines ./engines
COPY tests ./tests
COPY manage.py ./
EXPOSE 8000
