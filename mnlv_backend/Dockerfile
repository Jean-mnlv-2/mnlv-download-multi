FROM python:3.12-slim

# Configuration Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système essentielles (FFmpeg pour l'audio, libpq pour PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    curl \
    build-essential \
    libpq-dev \
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

# Port par défaut (sera surchargé par docker-compose si nécessaire)
EXPOSE 8000

# Commande par défaut (utilisée si aucune commande n'est spécifiée dans docker-compose)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]
