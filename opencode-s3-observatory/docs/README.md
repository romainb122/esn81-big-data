# Documentation OpenCode S3 Observatory

Le site de documentation est disponible localement sur
`http://localhost:8502`. Il est servi par Docsify et les fichiers Markdown de
ce dossier : aucune etape de compilation n'est necessaire.

## Parcours recommande

1. [Architecture](guide/architecture.md) pour comprendre les composants et les
   responsabilites de chaque couche.
2. [Flux de donnees](guide/data-flow.md) puis
   [Formats et transformations](data/formats.md) pour suivre une session de la
   source au navigateur.
3. Les pages de la section `Composants` pour le fonctionnement detaille de S3,
   Iceberg, Spark, DuckDB, Streamlit et de l'export.
4. [Gouvernance et garanties ACID](guide/data-governance.md) pour les regles
   d'evolution et les frontieres transactionnelles.

## Regle de mise a jour

Toute evolution de stockage, schema, service Docker ou flux de donnees doit
mettre a jour au moins une page dans la meme modification. Avant de valider une
evolution, verifier le schema concerne, la compatibilite
des lecteurs, les donnees deja stockees, les tests ou commandes de verification,
et mettre a jour la documentation correspondante.
