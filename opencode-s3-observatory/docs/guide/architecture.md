# Architecture generale

## Objectif

OpenCode S3 Observatory conserve les traces visibles de sessions OpenCode,
propose une consultation interactive et permet des traitements analytiques avec
Spark. Le projet separe volontairement les donnees brutes, les tables
transactionnelles et les syntheses analytiques.

## Carte du systeme

```text
OpenCode
  -> export automatique systemd
  -> JSON visible et Parquet Bronze dans SeaweedFS/S3
  -> PyIceberg committe opencode.events
  -> table Iceberg Silver transactionnelle

Dashboard Streamlit
  -> PyIceberg lit un snapshot Silver
  -> DuckDB execute les analyses interactives
  -> navigateur :8501

Spark SQL et batch
  -> catalogue Iceberg REST
  -> lit le snapshot opencode.events
  -> cree les tables Gold de synthese
```

Le detail du parcours d'une donnee est decrit dans
[Flux de donnees](data-flow.md). Les formats echanges entre les briques sont
decrits dans [Formats et transformations](../data/formats.md).

## Services Docker

| Service | Role | Port hote |
| --- | --- | --- |
| `s3` | SeaweedFS, stockage objet compatible S3 | 8333 |
| `iceberg` | catalogue REST Apache Iceberg | 8181 |
| `dashboard` | interface Streamlit | 8501 |
| `spark-query` | service Spark SQL interne | aucun |
| `spark-batch` | job Spark ponctuel, profil `spark` | aucun |
| `documentation` | site Docsify servi par Nginx | 8502 |

## Couches de donnees

- Bronze : JSON et Parquet sous `opencode-observatory/`. C'est la zone
  d'atterrissage et d'archivage, pas une source transactionnelle.
- Silver : table Iceberg `opencode.events`. C'est la source de verite pour le
  dashboard et Spark SQL.
- Gold : tables Iceberg `opencode.session_summary` et
  `opencode.tool_summary`, construites par Spark batch.

Les garanties ACID s'appliquent aux tables Iceberg Silver et Gold, pas a une
transaction globale entre les fichiers Bronze et plusieurs tables. Consulter
[Gouvernance et garanties ACID](data-governance.md) pour le detail.

## Role de chaque brique

| Brique | Responsabilite principale | Documentation detaillee |
| --- | --- | --- |
| OpenCode et export | produit, nettoie et publie les sessions | [Export](../components/export.md) |
| SeaweedFS/S3 | conserve durablement les objets | [S3](../components/seaweedfs-s3.md) |
| Iceberg | publie des snapshots transactionnels | [Iceberg](../components/iceberg.md) |
| Spark | execute SQL et calculs batch | [Spark](../components/spark.md) |
| DuckDB | analyse les donnees en memoire du dashboard | [DuckDB](../components/duckdb.md) |
| Streamlit | presente les donnees dans le navigateur | [Streamlit](../components/streamlit.md) |

## Regle d'architecture

Un consommateur analytique lit une table Iceberg, jamais le dossier Bronze
directement. Une ecriture analytique durable est publiee dans Iceberg. Cette
regle maintient une lecture par snapshots coherents lorsque le projet evolue.
