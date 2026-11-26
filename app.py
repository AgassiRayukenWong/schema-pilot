import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def read_schema(connection):
    columns = connection.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """).fetchall()

    foreign_keys = connection.execute("""
        SELECT
            conrelid::regclass::text AS table_name,
            pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE contype = 'f'
          AND connamespace = 'public'::regnamespace
          AND has_table_privilege(conrelid, 'SELECT')
          AND has_table_privilege(confrelid, 'SELECT')
        ORDER BY conrelid::regclass::text, conname
    """).fetchall()

    return {"columns": columns, "foreign_keys": foreign_keys}


def ask_ollama(question, schema):
    instructions = (
        "Génère une seule requête SELECT compatible avec PostgreSQL. "
        "Utilise les tables, colonnes et relations fournies. "
        "Préfixe les tables par public. "
        "Si la question est ambiguë ou si le schéma est insuffisant, "
        "pose une question en français commençant par CLARIFICATION:. "
        "Renvoie uniquement le SQL brut ou la question, sans Markdown."
    )

    payload = {
        "model": os.environ["OLLAMA_MODEL"],
        "stream": False,
        "messages": [
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": json.dumps(
                    {"question": question, "schema": schema},
                    ensure_ascii=False,
                ),
            },
        ],
    }

    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        result = json.load(response)

    return result["message"]["content"].strip()


def main():
    question = input("SchemaPilot > ").strip()
    if not question:
        raise SystemExit("Saisis une question pour continuer.")

    try:
        with psycopg.connect(
            os.environ["DATABASE_URL"],
            autocommit=True,
            row_factory=dict_row,
        ) as connection:
            schema = read_schema(connection)
            if not schema["columns"]:
                raise SystemExit("Aucune colonne visible dans le schéma public.")

            query = ask_ollama(question, schema)
            if not query:
                raise SystemExit("Ollama n'a renvoyé aucun texte.")
            if query.startswith("CLARIFICATION:"):
                print(query.removeprefix("CLARIFICATION:").strip())
                return

            print(f"\nSQL proposé\n{query}\n")
            if input("Exécuter cette requête ? [o/N] ").strip().lower() != "o":
                return

            with connection.transaction():
                connection.execute("SET TRANSACTION READ ONLY")
                connection.execute("SET LOCAL statement_timeout = '3s'")

                with connection.cursor(name="schema_pilot_results") as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchmany(20)

            if not rows:
                print("Aucun résultat.")
            for row in rows:
                print(row)

    except (URLError, TimeoutError) as error:
        raise SystemExit(f"Erreur Ollama : {error}") from error
    except psycopg.Error as error:
        raise SystemExit(f"Erreur PostgreSQL : {error}") from error
    except KeyError as error:
        raise SystemExit(f"Valeur manquante : {error}. Vérifie le fichier .env.") from error


if __name__ == "__main__":
    main()