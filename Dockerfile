# Small official Python image
FROM python:3.12-slim

# I stop Python writing .pyc files and make logs appear immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_VERSION=v1 \
    PORT=5000

WORKDIR /app

# I install dependencies first, so Docker can reuse this layer when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# I copy only what the API needs: cleaning code, API code and the trained models
COPY src/ src/
COPY app/ app/
COPY models/ models/

# I run the app as a normal user, not as root (safer)
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# Docker checks every 30 s that the API still answers
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# gunicorn is a production web server; 2 workers handle requests in parallel
CMD ["sh", "-c", "gunicorn --workers 2 --bind 0.0.0.0:${PORT} --access-logfile - app.app:app"]
