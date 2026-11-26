# SchemaPilot

SchemaPilot est un assistant en ligne de commande qui transforme des questions en langage naturel en requêtes SQL pour PostgreSQL.

Il découvre les tables, les colonnes et les clés étrangères du schéma `public`, puis transmet ces métadonnées et ta question à un modèle local via Ollama. Tu peux relire le SQL proposé avant de l’exécuter. Si la question est ambiguë, le modèle peut demander une précision.

**Exemple** — Tu demandes « Quel est le montant total des commandes ? » et SchemaPilot propose une requête qui retourne **350,00 €** sur la base de démonstration.

Le projet fonctionne en local, sans clé API ni abonnement. La version actuelle utilise Qwen2.5-Coder pour générer le SQL et un compte PostgreSQL dédié pour lire les données de démo.

## Prérequis

- Windows avec PowerShell
- [Python](https://www.python.org/downloads/windows/)
- [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) démarré
- [Ollama](https://ollama.com/download/windows) démarré

## Installation pas à pas

### 1. Ouvrir le terminal dans le dossier du projet

Ouvre le dossier `schema-pilot` dans VS Code, puis ouvre le terminal intégré. Vérifie que tu es bien à la racine du projet et que `init.sql` est présent.

```powershell
Get-Location
Test-Path .\init.sql -PathType Leaf
```

Le chemin doit se terminer par `schema-pilot` et le test doit afficher `True`.

### 2. Installer les dépendances Python

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install "psycopg[binary]" python-dotenv
```

Les commandes utilisent directement l’interpréteur de `.venv`.

### 3. Télécharger et tester le modèle local

```powershell
ollama pull qwen2.5-coder:7b
ollama run qwen2.5-coder:7b "Réponds uniquement par OK"
```

Le premier téléchargement fait environ 4,7 Go. Une réponse du modèle confirme qu’Ollama fonctionne.

### 4. Démarrer PostgreSQL

Vérifie d’abord que Docker Desktop est prêt.

```powershell
docker info
```

La sortie doit inclure une section `Server`. Depuis le dossier `schema-pilot`, crée ensuite le conteneur de démonstration.

```powershell
docker run --name schema-pilot-db `
  -e POSTGRES_PASSWORD=demo_admin `
  -e POSTGRES_DB=shop `
  -p 127.0.0.1:55432:5432 `
  --mount "type=bind,source=$($PWD.Path)\init.sql,target=/docker-entrypoint-initdb.d/init.sql,readonly" `
  -d postgres:17
```

La commande crée la base `shop`, charge les données de `init.sql` au premier démarrage et rend PostgreSQL accessible depuis ton PC sur le port `55432`.

**Si le conteneur existe déjà**, démarre-le avec `docker start schema-pilot-db` s’il est arrêté.

Vérifie que le compte de lecture peut accéder aux données.

```powershell
docker exec -e PGPASSWORD=demo_reader schema-pilot-db psql -h 127.0.0.1 -U schema_pilot_reader -d shop -c "SELECT * FROM customers;"
```

Tu dois voir **Alice** et **Karim**. Si la connexion est refusée juste après le démarrage, attends quelques secondes et relance le test.

### 5. Configurer `.env`

À la racine du projet, crée un fichier nommé exactement **`.env`**, avec le point initial et sans extension `.txt`.

```dotenv
DATABASE_URL=postgresql://schema_pilot_reader:demo_reader@127.0.0.1:55432/shop
OLLAMA_MODEL=qwen2.5-coder:7b
```

Ces identifiants sont destinés à la base de démonstration locale. Crée ou complète aussi `.gitignore` avant de faire ton commit.

```gitignore
.env
.venv/
__pycache__/
```

### 6. Lancer SchemaPilot

```powershell
.\.venv\Scripts\python.exe app.py
```

Attends l’invite `SchemaPilot >`, puis saisis :

```text
Quel est le montant total des commandes ?
```

SchemaPilot devrait proposer une requête équivalente à celle-ci.

```sql
SELECT SUM(amount_eur) AS total_amount_eur
FROM public.orders;
```

Relis le SQL, puis tape `o` à l’invite de confirmation. Le résultat attendu est `350.00` euros, affiché sous la forme `Decimal('350.00')`.

Le script traite une question par lancement. Relance `app.py` pour chaque nouvelle question.

## Questions à tester

| Question | Résultat attendu |
| --- | --- |
| Combien y a-t-il de commandes ? | 3 |
| Quel est le montant total des commandes ? | 350,00 € |
| Quel client a dépensé le plus ? | Alice |
| Quel client a dépensé le plus et combien a-t-il dépensé ? | Alice, 200,00 € |
| Quel est le meilleur client ? | Une demande de précision sur le critère |

Deux requêtes différentes peuvent donner le même résultat. Le dernier exemple vérifie si le modèle sait reconnaître une ambiguïté.

## Relancer le projet plus tard

Ouvre Docker Desktop et Ollama, puis lance ces commandes depuis `schema-pilot`.

```powershell
docker start schema-pilot-db
.\.venv\Scripts\python.exe app.py
```

Si le conteneur tourne déjà, lance directement `app.py`.

## Dépannage

| Symptôme | Solution |
| --- | --- |
| `failed to connect to the docker API` ou `docker_engine` introuvable | Ouvre Docker Desktop, attends le démarrage du moteur et relance `docker info`. |
| Docker cherche `C:\WINDOWS\system32\init.sql` | Ouvre le terminal dans `schema-pilot`, puis vérifie `Test-Path .\init.sql -PathType Leaf` avant de relancer la commande. |
| Le nom `schema-pilot-db` est déjà utilisé | Réutilise le conteneur existant avec `docker start schema-pilot-db`. |
| Ollama refuse la connexion | Ouvre Ollama et teste `ollama run qwen2.5-coder:7b "Réponds uniquement par OK"`. |
| Python signale une variable manquante | Vérifie que `.env` est à côté de `app.py` et contient `DATABASE_URL` et `OLLAMA_MODEL`. |
| PowerShell affiche `Le terme « Quel » n'est pas reconnu` | Relance `app.py` et saisis la question après `SchemaPilot >`. |

## Périmètre

Cette première version prend en charge PostgreSQL et découvre le schéma `public` à l’exécution. Elle utilise un compte de lecture dédié, une transaction en lecture seule et une confirmation manuelle avant d’exécuter le SQL généré. Commence avec les données fictives fournies dans `init.sql`.