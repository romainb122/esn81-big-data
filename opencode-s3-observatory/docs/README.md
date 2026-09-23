# Documentation OpenCode S3 Observatory

Le site de documentation est disponible localement sur
`http://localhost:8502`. Il est servi par Docsify et les fichiers Markdown de
ce dossier : aucune etape de compilation n'est necessaire.

## Parcours recommande

1. [Architecture](guide/architecture.md) pour comprendre les composants et les
   flux de donnees.
2. [Gouvernance et garanties ACID](guide/data-governance.md) pour identifier la
   source de verite, les couches Bronze/Silver/Gold et les contrats de donnees.
3. [Sauvegardes OpenCode](operations/opencode-s3.md) pour installer et exploiter
   l'export automatique.
4. [ADR 0001](decisions/0001-iceberg-transaction-boundary.md) pour comprendre
   la decision de faire d'Iceberg la frontiere transactionnelle.

## Regle de mise a jour

Toute evolution de stockage, schema, service Docker ou flux de donnees doit
mettre a jour au moins une page dans la meme modification. Avant de valider une
evolution, verifier le schema concerne, la compatibilite
des lecteurs, les donnees deja stockees, les tests ou commandes de verification,
et mettre a jour la documentation correspondante.
