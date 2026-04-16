# Étape de Développement
FROM node:20-alpine

WORKDIR /app

# Installation des dépendances avec cache optimal
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps


COPY . .

# Exposition du port Vite (3003 configuré dans vite.config.ts)
EXPOSE 3003

# Lancement en mode hôte pour permettre l'accès externe via Docker
CMD ["npm", "run", "dev", "--", "--host", "--port", "3003"]
