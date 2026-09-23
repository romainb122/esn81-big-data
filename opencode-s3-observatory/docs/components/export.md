# OpenCode et export

## Role

OpenCode est la source des conversations et traces visibles. Le pipeline
d'export transforme ces donnees applicatives en artefacts exploitables par S3,
Iceberg, DuckDB et Spark.

## Lancement

Le timer utilisateur `opencode-s3-export.timer` declenche l'export au demarrage
et toutes les cinq minutes. Un export manuel est possible :

```bash
./scripts/export-opencode-conversations.sh --force
```

## Entree et sortie

| Etape | Recoit | Produit |
| --- | --- | --- |
| `opencode export` | identifiant de session | JSON de session source |
| `opencode-export-to-parquet.py` | JSON source | JSON visible et Parquet |
| upload S3 | fichiers locaux temporaires | objets Bronze S3 |
| `sync-opencode-iceberg.py` | Parquet local | snapshot `opencode.events` |

Le script exclut les parties de type `reasoning`. Les prompts, reponses et
sorties visibles restent en clair : les donnees doivent rester locales et
privees.

## Observation

```bash
systemctl --user status opencode-s3-export.timer
journalctl --user -u opencode-s3-export.service -n 50 --no-pager
```

La procedure complete d'installation et de reprise est dans
[Sauvegardes OpenCode](../operations/opencode-s3.md).
