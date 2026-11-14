FROM python:3.12-slim

# Eigener Benutzer im Container, kein root
RUN useradd --create-home --uid 10001 werkzeug

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/

RUN mkdir -p /daten && chown werkzeug /daten
USER werkzeug

EXPOSE 8090
CMD ["python", "server/app.py"]
