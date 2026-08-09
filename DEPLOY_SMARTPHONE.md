# Procédure smartphone — GitHub + Render

## A. Télécharger
Télécharge le ZIP fourni dans cette conversation et décompresse-le avec l'application Fichiers de ton téléphone.

## B. GitHub
1. Ouvre GitHub dans Chrome.
2. Create a new repository.
3. Nom : `deriv-ybt-monitor`.
4. Mets-le en Private.
5. Ne coche pas README / .gitignore / licence.
6. Crée le repository.
7. Dans le repository : Add file → Upload files.
8. Sélectionne le contenu du dossier du projet, pas seulement un fichier isolé.
9. Commit changes.

Si l'application GitHub ne permet pas l'upload d'un dossier complet, utilise GitHub dans Chrome en mode bureau ou importe les fichiers individuellement. Le minimum est de conserver exactement l'arborescence du ZIP.

## C. Telegram
1. Ouvre @BotFather.
2. `/newbot`.
3. Copie le token.
4. Ouvre ton bot et envoie `/start`.
5. Récupère ton `chat_id` avec une méthode Telegram fiable.
6. Ne publie jamais le token.

## D. Render
1. Ouvre Render.
2. New → Background Worker.
3. Connecte ton GitHub.
4. Sélectionne `deriv-ybt-monitor`.
5. Runtime : Docker.
6. Dockerfile : `./Dockerfile`.
7. Ajoute les variables : `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
8. Conserve `DERIV_WS_URL=wss://api.derivws.com/trading/v1/options/ws/public`.
9. Deploy.

## E. Lire les logs
Dans Render → ton Worker → Logs.
Tu dois voir une ligne du type :
`Scanning N symbols sequentially`

Puis, lorsqu'une nouvelle zone est créée :
`ZONE ALERT ...`

## F. Réglages de départ
- Pivot Left Bars = 20
- Pivot Right Bars = 2
- H1/H2/H3/H4
- 1 zone réellement créée = 1 alerte
- Fusion dans une zone existante = aucune nouvelle alerte
- Concordance = 1 à 4 étoiles

## G. Avant le 24/7 définitif
Compare quelques zones du scanner avec le YBT LH sur les mêmes instruments/timeframes. La concordance multi-TF est une règle ajoutée au projet et doit être validée sur tes exemples.
