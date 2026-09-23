# ADR 0001 : Iceberg comme frontiere transactionnelle

## Statut

Accepte.

## Contexte

Les exports OpenCode arrivent sous forme de JSON et Parquet dans un stockage S3
local. Des fichiers objets seuls ne fournissent pas une vue atomique de plusieurs
ecritures et ne doivent pas servir directement aux requetes analytiques.

## Decision

Les consommateurs analytiques utilisent les tables Iceberg du catalogue REST :

- `opencode.events` pour les evenements actifs.
- `opencode.session_summary` et `opencode.tool_summary` pour les agregats Spark.

Spark SQL et le dashboard utilisent ces tables comme source de verite. Les
fichiers JSON et Parquet sous `opencode-observatory/` restent la couche Bronze.

## Consequences

Les lecteurs beneficient de snapshots coherents et les ecritures invalidees ne
remplacent pas la derniere version valide. En contrepartie, toute nouvelle table
analytique doit etre creee dans Iceberg, et les changements de schema doivent
etre controles et documentes.
