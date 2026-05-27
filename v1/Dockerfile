FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user first
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"

RUN pip install --user --no-cache-dir --upgrade pip
COPY --chown=appuser:appuser pyproject.toml .
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser app/ ./app/
RUN pip install --user --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
