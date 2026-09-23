# Formats et transformations de donnees

## Pourquoi plusieurs formats

Chaque brique travaille avec le format le plus adapte a son role. Le JSON est
pratique pour archiver et relire une session. Le Parquet est efficace pour les
analyses colonne par colonne. Arrow et les DataFrames servent aux echanges en
memoire. Iceberg ajoute une couche de metadonnees transactionnelles aux fichiers
de donnees.

## Formats du projet

| Format | Utilisation | Producteur | Consommateur |
| --- | --- | --- | --- |
| JSON OpenCode | resultat source temporaire | OpenCode CLI | script export |
| JSON visible | archive Bronze lisible | export Python | utilisateur, S3 |
| Parquet Bronze | une ligne par evenement | PyArrow | PyIceberg, reprise |
| Arrow Table | donnees colonne en memoire | PyIceberg | DuckDB, Streamlit |
| Spark DataFrame | plan de calcul distribue | Spark | Spark SQL, batch |
| DataFrame Pandas | resultat interactif local | DuckDB | Streamlit |
| JSON HTTP | requete et resultat Spark SQL | Streamlit, spark-query | Streamlit |
| Parquet Iceberg | fichiers de donnees Silver et Gold | PyIceberg, Spark | Iceberg |
| Avro et JSON Iceberg | manifests et metadonnees de snapshot | Iceberg | catalogue et moteurs |

## Transformation complete

```text
JSON OpenCode source
  -> JSON visible archive
  -> Parquet Bronze
  -> Arrow Table
  -> snapshot Iceberg et Parquet Silver
  -> Spark DataFrame ou Arrow/DuckDB
  -> DataFrame Pandas ou JSON HTTP
  -> navigateur
```

## JSON

Le JSON visible conserve la structure d'une session pour une lecture humaine :
messages, parties de texte, appels d'outils et sorties visibles. Il n'est pas la
source utilisee pour les analyses SQL. Les parties `reasoning` sont retirees
avant son ecriture.

## Parquet

Le Parquet Bronze contient une ligne par evenement et des colonnes comme
`session_id`, `message_id`, `event_type`, `content`, `tool_name`, tokens et
couts. Son format colonnaire permet de ne lire que les colonnes utiles pour une
requete.

Iceberg ecrit aussi des Parquet, mais ces fichiers font partie d'une table et
doivent etre lus via Iceberg. Lire des fichiers individuels dans le dossier
Iceberg contournerait les snapshots et les garanties de coherence.

## Arrow, Pandas et Spark DataFrame

Arrow est un format colonne en memoire sans copie inutile entre PyIceberg et
DuckDB. DuckDB transforme ses resultats en DataFrames Pandas, adaptes aux
composants Streamlit.

Un Spark DataFrame represente un calcul distribue paresseux : Spark ne lit pas
les fichiers au moment de la declaration, mais lors d'une action comme
`collect()` ou une ecriture Iceberg.

## SQL et HTTP JSON

Le SQL est le langage fourni par l'utilisateur dans l'onglet Spark. Streamlit
l'envoie dans un objet JSON HTTP au service `spark-query`. Le service retourne
les colonnes et lignes du resultat dans un JSON, avec une limite de 500 lignes.
