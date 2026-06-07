# Offizielles, schlankes Python-Image als Basis
FROM python:3.9-slim

# Arbeitsverzeichnis im Container erstellen
WORKDIR /app

# System-Abhängigkeiten installieren (wichtig für einige Mathe-Bibliotheken)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Requirements kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den restlichen Code in den Container kopieren
COPY . .