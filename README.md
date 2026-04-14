# MNLVdownload — Version 2.0

Plateforme SaaS de Téléchargement Multi-Provider hautement optimisée, migrée depuis l'application desktop historique.

##  Vision
Transformer l'expérience de téléchargement de musique en une interface web fluide supportant 6 plateformes majeures via un moteur asynchrone ultra-performant.

##  Architecture Technique
- **Frontend** : React.js (Vite) + Zustand (State Management) + Tailwind CSS.
- **Backend API** : Django REST Framework + PostgreSQL.
- **Asynchrone** : Celery + Redis (Gestion de files d'attente prioritaires).
- **Moteur DL** : API Native `yt-dlp` + FFmpeg + Mutagen (Tagging ID3).
- **Infrastructure** : Docker & Docker Compose (Orchestration multi-services).

##  Concepts Clés & Innovations

### 1. Pattern Multi-Provider (Blueprint Spotify)
Spotify sert de référence architecturale. Tous les autres providers (Deezer, Apple Music, Tidal, etc.) héritent de la même logique métier via une classe abstraite `MusicProvider`.
- **Validation** : Détection automatique de la plateforme via Regex.
- **Extraction** : Récupération unifiée des métadonnées (Titre, Artiste, Album, ISRC, Cover).

### 2. Matching Intelligent (ISRC Priority)
Inspiré de `spotDL`, notre module `matcher.py` utilise une stratégie en 3 étapes :
1. **ISRC Match** : Recherche directe sur YouTube Music via le code ISRC (Précision 100%).
2. **Metadata Match** : Comparaison texte + durée du morceau.
3. **Fallback** : Recherche textuelle optimisée via `yt-dlp`.

### 3. Industrialisation Celery
Séparation des flux pour une réactivité maximale :
- **Queue `high_priority`** : Traitement immédiat des morceaux unitaires.
- **Queue `low_priority`** : Traitement en arrière-plan des playlists et albums.
- **Retry Policy** : Relance automatique avec délai exponentiel en cas d'erreur réseau.

### 4. Tagging & Pochettes (Embedded)
Contrairement aux outils basiques, MNLVdownload injecte :
- Les tags ID3 complets (Titre, Artiste, Album, Année).
- La **pochette d'album haute résolution** directement dans le binaire du fichier MP3 (Tag APIC).

##  Structure du Projet
- `mnlv_backend/` : Cœur du système (Django, Engine, Providers, Tasks).
- `mnlv_frontend/` : Interface utilisateur React moderne.
- `infra/` : Configurations spécifiques au déploiement.
- `docker-compose.yml` : Orchestration de l'écosystème (DB, Redis, API, Workers, Frontend).

##  Installation & Lancement

1. **Prérequis** : Docker & Docker Compose installés.
2. **Configuration** :
   ```bash
   cp .env.example .env
   # Remplissez vos clés API (Spotify, etc.) dans le .env
   ```
3. **Démarrage** :
   ```bash
   docker-compose up --build
   ```
4. **Accès** :
   - Frontend : `http://localhost:5173`
   - API Backend : `http://localhost:8000`

---
© 2026 MNLVdownload Team — Confidentiel & Performance-Driven
