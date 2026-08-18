# Music Tracker — Chrétien vs Mondain

Petite app perso qui se connecte à ton Spotify, regarde ton historique
d'écoute récent, et classe chaque titre en "chrétien" ou "mondain" selon
le genre de l'artiste.

## 1. Installer les dépendances

Ouvre un terminal dans ce dossier et lance :

```
pip install -r requirements.txt --break-system-packages
```

(enlève `--break-system-packages` si tu es dans un environnement virtuel)

## 2. Configurer tes clés Spotify

1. Copie `.env.example` en `.env` :
   ```
   cp .env.example .env
   ```
2. Ouvre `.env` et remplace :
   - `SPOTIFY_CLIENT_ID` par ton Client ID (dashboard Spotify)
   - `SPOTIFY_CLIENT_SECRET` par ton Client Secret
   - `FLASK_SECRET_KEY` par n'importe quelle phrase aléatoire

## 3. Ajouter tes 25 testeurs

Sur https://developer.spotify.com/dashboard → ton app → Settings →
"User Management", ajoute l'email Spotify de chaque personne qui doit
pouvoir se connecter (25 maximum en mode développement).

## 4. Lancer l'app

```
python app.py
```

Puis ouvre http://127.0.0.1:3000 dans ton navigateur.

## 5. Utilisation

- Chaque personne va sur le lien, clique "Se connecter avec Spotify"
- Elle autorise l'accès à son historique d'écoute
- Elle voit direct son ratio chrétien/mondain
- Le bouton "Rafraîchir mes données" resync les 50 derniers titres écoutés

## Notes importantes

- La base de données `tracker.db` se crée automatiquement au premier
  lancement, dans ce même dossier.
- Spotify ne donne accès qu'aux **50 derniers titres écoutés** via cette
  API (pas d'historique complet illimité) — chaque `sync` ajoute les
  nouveaux titres sans dupliquer les anciens.
- La classification se fait sur le **genre déclaré de l'artiste** sur
  Spotify (christian, gospel, worship, etc.). Certains artistes chrétiens
  mal catégorisés par Spotify peuvent passer en "mondain" — tu peux
  enrichir la liste de mots-clés dans `app.py` (variable
  `CHRISTIAN_KEYWORDS`) si tu remarques des erreurs fréquentes.
- Pour que ça marche pour les 25 personnes en même temps, il faut que
  ce serveur tourne quelque part d'accessible (ton ordi allumé, ou un
  hébergement type Railway/Render) — pas juste sur `127.0.0.1` si les
  autres ne sont pas sur le même réseau que toi.
