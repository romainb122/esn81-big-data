# Documentation du projet

Cette documentation est maintenue avec le code. Toute evolution de stockage,
schema, service Docker ou flux de donnees doit mettre a jour au moins un des
documents ci-dessous dans la meme modification.

- [Architecture](architecture.md) : composants, flux et roles des services.
- [Gouvernance et garanties ACID](data-governance.md) : couches de donnees,
  contrats, transactions et regles d'evolution.
- [Sauvegardes OpenCode dans S3](opencode-s3.md) : installation et exploitation
  de l'export automatique.
- [ADR 0001](adr/0001-iceberg-transaction-boundary.md) : pourquoi Iceberg est
  la frontiere transactionnelle des donnees analytiques.

## Regle de mise a jour

Avant de valider une evolution, verifier le schema concerne, la compatibilite
des lecteurs, les donnees deja stockees, les tests ou commandes de verification,
et mettre a jour la documentation correspondante.
