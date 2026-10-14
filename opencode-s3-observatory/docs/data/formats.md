# Formats et transformations de donnees

## Formats du projet

| Format | Utilisation | Producteur | Consommateur |
| --- | --- | --- | --- |
| JSONL de session pi | journal local source | Pi | extension ou outil de rejeu |
| JSON REST | publication d'un evenement | extension pi | Redpanda |
| Arrow Table | donnees en memoire | PyIceberg | DuckDB, Streamlit |
| Spark DataFrame | calcul analytique | Spark | Spark SQL, batch |
| DataFrame Pandas | resultat interactif local | DuckDB | Streamlit |
| JSON HTTP | requete et resultat Spark SQL | Streamlit, spark-query | Streamlit |
| Parquet Iceberg | donnees Bronze, Silver et Gold | PyIceberg, Spark | Iceberg |
| Avro et JSON Iceberg | manifests et snapshots | Iceberg | catalogue et moteurs |

## Transformation complete

```text
Pi hook message_end
  -> evenement JSON visible
  -> topic Redpanda
  -> Arrow Table
  -> snapshot Iceberg Bronze
  -> Spark : Silver puis Gold
  -> Arrow/DuckDB ou Spark SQL
  -> navigateur
```

## Evenements JSON

Chaque evenement porte notamment `session_id`, `message_id`, `event_id`,
`event_type`, `role`, `content`, `tool_name`, les tokens et le cout. Les appels
et sorties d'outils sont conserves afin de reconstruire le flux d'execution.
Les blocs `thinking` et les messages systeme sont exclus par l'extension.

Le JSON est transporte par l'API REST Redpanda. Il n'est pas lu directement par
le dashboard.

## Parquet et Iceberg

Iceberg utilise Parquet pour les fichiers physiques. Ces fichiers font partie
d'une table versionnee et doivent etre lus via Iceberg, jamais directement dans
le warehouse S3 : sinon les snapshots et la coherence seraient contournes.

Bronze conserve les lots recus. Spark produit ensuite la table Silver active et
les tables Gold de synthese.

## Donnees en memoire et SQL

PyIceberg charge les colonnes necessaires en Arrow. DuckDB les analyse en
memoire et renvoie des DataFrames Pandas a Streamlit.

Pour les requetes Spark, Streamlit envoie du SQL dans un objet JSON HTTP a
`spark-query`. Le service accepte uniquement les requetes de lecture et limite
les resultats a 500 lignes.
