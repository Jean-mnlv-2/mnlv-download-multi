# Étape 1 : Build (facultatif si on utilise npm run dev, mais utile pour vérifier la compilation)
FROM node:20-alpine as builder

WORKDIR /app

# Installation des dépendances avec cache optimal
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Copie du code source
COPY . .

# Construction de l'application
RUN npm run build

# Étape 2 : Runtime (Développement optimisé pour Docker)
FROM node:20-alpine

WORKDIR /app

# On récupère tout de l'étape de build (node_modules + code)
COPY --from=builder /app ./

# Exposition du port Vite (3003 configuré dans vite.config.ts)
EXPOSE 3003

# Lancement en mode hôte pour permettre l'accès externe via Docker
CMD ["npm", "run", "dev", "--", "--host"]
