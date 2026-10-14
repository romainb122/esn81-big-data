# ADR 0001 : Iceberg comme frontiere transactionnelle

## Statut

Accepte.

## Contexte

Les evenements pi sont publies dans Redpanda, puis ingeres dans Iceberg. Un
topic et des fichiers objets seuls ne fournissent pas une vue atomique destinee
aux requetes analytiques.

## Decision

Les consommateurs analytiques utilisent les tables Iceberg du catalogue REST :

- `opencode.events` pour les evenements actifs.
- `opencode.events_bronze` pour le journal append-only d'ingestion.
- `opencode.session_summary` et `opencode.tool_summary` pour les agregats Spark.

Spark SQL et le dashboard lisent Silver et Gold. Bronze est conserve dans
`opencode.events_bronze` et Redpanda conserve le journal rejouable en amont.

## Consequences

Les lecteurs beneficient de snapshots coherents et les ecritures invalidees ne
remplacent pas la derniere version valide. En contrepartie, toute nouvelle table
analytique doit etre creee dans Iceberg, et les changements de schema doivent
etre controles et documentes.
