FROM python:3.12-slim

# Configuration Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système essentielles (FFmpeg pour l'audio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création des dossiers pour les fichiers statiques et média
RUN mkdir -p /app/media/downloads /app/staticfiles

# Port par défaut
EXPOSE 8000

# Commande par défaut
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]
