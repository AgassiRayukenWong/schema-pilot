# SchemaPilot

SchemaPilot est un assistant en ligne de commande qui transforme des questions en langage naturel en requêtes SQL pour PostgreSQL.

Tu poses une question comme « Quel est le montant total des commandes ? ». SchemaPilot découvre la structure de la base, propose une requête SQL et te laisse la relire avant de l’exécuter. Sur la base de démonstration, le résultat attendu est **350,00 €**.

Le projet fonctionne en local, sans clé API ni abonnement. Il utilise Qwen2.5-Coder via Ollama pour générer le SQL.

## Comment ça fonctionne

1. **Python lit le schéma PostgreSQL.** Il récupère les noms des tables, les noms et types des colonnes et les clés étrangères visibles dans le schéma `public`. Une clé étrangère indique comment relier deux tables, par exemple `orders.customer_id` et `customers.id`.
2. **Ollama fait tourner le modèle sur ton PC.** Python lui transmet la question et la structure de la base. Le modèle propose du SQL ou demande une précision si la question est ambiguë.
3. **PostgreSQL exécute le SQL après ta confirmation.** SchemaPilot se connecte avec un compte de lecture dédié et affiche jusqu’à 20 lignes de résultat dans le terminal.

## Prérequis

- Windows avec PowerShell
- [Python](https://www.python.org/downloads/windows/) pour exécuter `app.py`
- [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) pour lancer la base de démonstration
- [Ollama](https://ollama.com/download/windows) pour faire tourner le modèle local

## Installation pas à pas

### 1. Ouvrir le terminal dans le dossier du projet

Ouvre le dossier `schema-pilot` dans VS Code, puis ouvre le terminal intégré.

```powershell
Get-Location
Test-Path .\init.sql -PathType Leaf
```

- `Get-Location` affiche le dossier courant. Le chemin doit se terminer par `schema-pilot`.
- `Test-Path` vérifie que `init.sql` existe à cet endroit. `-PathType Leaf` vérifie qu’il s’agit d’un fichier. Le résultat attendu est `True`.

Cette vérification compte parce que Docker utilise le dossier courant pour retrouver `init.sql`.

### 2. Installer les dépendances Python

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install "psycopg[binary]" python-dotenv
```

- `py -m venv .venv` crée un environnement Python isolé dans `.venv`. Il contient les dépendances propres à ce projet.
- `.\.venv\Scripts\python.exe -m pip install ...` installe les bibliothèques avec le Python de cet environnement. Tu peux utiliser ce chemin directement dans les commandes suivantes.
- `psycopg[binary]` permet à Python de se connecter à PostgreSQL et d’exécuter des requêtes. `python-dotenv` charge les paramètres du fichier `.env`.

### 3. Télécharger et tester le modèle local

Démarre Ollama, puis lance ces commandes.

```powershell
ollama pull qwen2.5-coder:7b
ollama run qwen2.5-coder:7b "Réponds uniquement par OK"
```

- `ollama pull` télécharge le modèle sur ton PC. Le premier téléchargement fait environ 4,7 Go.
- `ollama run` envoie une question de test au modèle. S’il répond, tu peux passer à l’étape suivante.

### 4. Démarrer PostgreSQL

Ouvre Docker Desktop, attends le démarrage du moteur, puis lance :

```powershell
docker info
```

La section `Server` confirme que PowerShell arrive à communiquer avec le moteur Docker.

Depuis le dossier `schema-pilot`, crée ensuite le conteneur de démonstration.

```powershell
docker run --name schema-pilot-db `
  -e POSTGRES_PASSWORD=demo_admin `
  -e POSTGRES_DB=shop `
  -p 127.0.0.1:55432:5432 `
  --mount "type=bind,source=$($PWD.Path)\init.sql,target=/docker-entrypoint-initdb.d/init.sql,readonly" `
  -d postgres:17
```

| Option | Ce qu’elle fait |
| --- | --- |
| `docker run` | Crée et démarre un conteneur. |
| `--name schema-pilot-db` | Donne un nom au conteneur pour pouvoir le retrouver, le démarrer ou consulter ses logs. |
| `-e POSTGRES_PASSWORD=demo_admin` | Définit le mot de passe de l’administrateur PostgreSQL pour la démo. SchemaPilot utilise le compte de lecture créé dans `init.sql`. |
| `-e POSTGRES_DB=shop` | Crée la base `shop` lors de l’initialisation. |
| `-p 127.0.0.1:55432:5432` | Relie le port `55432` de ton PC au port `5432` du conteneur. L’adresse `127.0.0.1` limite l’accès à ton PC. |
| `--mount ...` | Rend ton fichier `init.sql` accessible au conteneur en lecture seule. PostgreSQL exécute ce fichier lors de l’initialisation d’une base vide. |
| `-d` | Lance le conteneur en arrière-plan et te rend la main dans PowerShell. |
| `postgres:17` | Utilise l’image PostgreSQL version 17. |

Le caractère `` ` `` en fin de ligne permet à PowerShell de lire le bloc comme une seule commande. Il doit être le dernier caractère de la ligne.

Si le conteneur existe déjà et qu’il est arrêté, réutilise-le avec `docker start schema-pilot-db`. Le redémarrage conserve la base existante. `init.sql` est exécuté lors de sa première initialisation.

Vérifie ensuite que le compte de lecture accède aux données.

```powershell
docker exec -e PGPASSWORD=demo_reader schema-pilot-db psql -h 127.0.0.1 -U schema_pilot_reader -d shop -c "SELECT * FROM customers;"
```

- `docker exec` lance une commande dans le conteneur déjà démarré. Ici, il lance `psql`, le client en ligne de commande de PostgreSQL.
- `-e PGPASSWORD=demo_reader` fournit le mot de passe de démo à cette commande.
- `-h 127.0.0.1`, `-U schema_pilot_reader` et `-d shop` indiquent respectivement l’hôte, l’utilisateur et la base. Ici, `psql` s’exécute dans le conteneur, donc l’adresse désigne le conteneur lui-même.
- `-c "SELECT * FROM customers;"` exécute la requête puis quitte `psql`.

Tu dois voir **Alice** et **Karim**. Si PostgreSQL refuse la connexion juste après le démarrage, attends quelques secondes et relance le test.

### 5. Configurer `.env`

À côté de `app.py`, crée un fichier nommé exactement **`.env`**, avec le point initial et sans extension `.txt`.

```dotenv
DATABASE_URL=postgresql://schema_pilot_reader:demo_reader@127.0.0.1:55432/shop
OLLAMA_MODEL=qwen2.5-coder:7b
```

- `DATABASE_URL` indique à Python le compte de lecture, son mot de passe, l’adresse `127.0.0.1`, le port `55432` et la base `shop`.
- `OLLAMA_MODEL` indique quel modèle local utiliser pour générer le SQL.

Ajoute ces lignes à `.gitignore` pour garder la configuration locale, l’environnement Python et le cache hors du dépôt.

```gitignore
.env
.venv/
__pycache__/
```

Tu peux vérifier que Git ignore `.env` avec `git check-ignore .env`. Le résultat attendu est `.env`.

### 6. Lancer SchemaPilot

```powershell
.\.venv\Scripts\python.exe app.py
```

Cette commande exécute `app.py` avec le Python qui contient les dépendances installées à l’étape 2.

Attends l’invite **`SchemaPilot >`**, puis saisis cette question :

```text
Quel est le montant total des commandes ?
```

SchemaPilot devrait proposer une requête équivalente à celle-ci.

```sql
SELECT SUM(amount_eur) AS total_amount_eur
FROM public.orders;
```

`FROM public.orders` désigne la table à lire. `SUM(amount_eur)` additionne le montant de toutes les commandes et `AS total_amount_eur` donne un nom à la colonne du résultat.

Relis le SQL, puis tape `o` pour l’exécuter. Le résultat attendu est **350,00 €**. Python peut l’afficher sous la forme `Decimal('350.00')`, qui représente le montant avec une précision décimale.

Le script traite une question par lancement. Quand tu retrouves l’invite PowerShell `PS ...>`, relance `app.py` pour poser une autre question.

## Questions à tester

| Question | Résultat attendu |
| --- | --- |
| Combien y a-t-il de commandes ? | 3 |
| Quel est le montant total des commandes ? | 350,00 € |
| Quel client a dépensé le plus ? | Alice |
| Quel client a dépensé le plus et combien a-t-il dépensé ? | Alice, 200,00 € |
| Quel est le meilleur client ? | Idéalement, une demande de précision sur le critère |

Deux requêtes différentes peuvent donner le même résultat. La dernière question permet de tester si le modèle demande de choisir entre des critères comme le montant dépensé et le nombre de commandes.

## Relancer le projet plus tard

Ouvre Docker Desktop et Ollama, puis lance ces commandes depuis `schema-pilot`.

```powershell
docker start schema-pilot-db
.\.venv\Scripts\python.exe app.py
```

La première commande redémarre la base existante. La deuxième ouvre l’invite SchemaPilot. Si le conteneur tourne déjà, lance directement la deuxième commande.

## Dépannage

| Symptôme | Solution |
| --- | --- |
| `failed to connect to the docker API` ou `docker_engine` introuvable | Ouvre Docker Desktop, attends le démarrage du moteur et relance `docker info`. |
| Docker cherche `C:\WINDOWS\system32\init.sql` | Ouvre le terminal dans `schema-pilot`, puis vérifie que `Test-Path .\init.sql -PathType Leaf` affiche `True`. |
| Le nom `schema-pilot-db` est déjà utilisé | Réutilise le conteneur existant avec `docker start schema-pilot-db`. |
| PostgreSQL refuse toujours la connexion | Lance `docker logs schema-pilot-db` pour lire les messages de démarrage et vérifier si `init.sql` s’est exécuté correctement. |
| Ollama refuse la connexion | Ouvre Ollama et teste `ollama run qwen2.5-coder:7b "Réponds uniquement par OK"`. |
| Python signale une variable manquante | Vérifie que `.env` est à côté de `app.py` et contient `DATABASE_URL` et `OLLAMA_MODEL`. |
| PowerShell affiche `Le terme « Quel » n'est pas reconnu` | Relance `app.py` et saisis ta question après `SchemaPilot >`. |

## Périmètre

Cette première version prend en charge PostgreSQL et découvre le schéma `public` à l’exécution. Elle utilise un compte de lecture dédié, une transaction en lecture seule et une confirmation manuelle avant d’exécuter le SQL généré. Pour prendre en main le projet, utilise les données fictives fournies dans `init.sql`.