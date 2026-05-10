# Python-Image
FROM python:3.11-slim

# Setzen das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopieren den Code in den Container
COPY . /app/

# Port 8000 nach draußen geöffnet werden soll
EXPOSE 8000

# Starten den Webserver
CMD ["python", "-m", "http.server", "8000"]