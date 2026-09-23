# Sauvegardes OpenCode dans S3

Les conversations OpenCode sont exportees automatiquement au demarrage, puis
toutes les cinq minutes. Seules les sessions modifiees sont envoyees. Chaque
session produit deux fichiers lisibles dans le S3 local, puis ses evenements
sont ajoutes a une table Apache Iceberg :

- `opencode-observatory/sessions/ses_xxx.json` : prompts, reponses, commandes
  et sorties d'outils.
- `opencode-observatory/parquet/sessions/ses_xxx.parquet` : une ligne par
  evenement pour DuckDB et Iceberg.

Les fichiers sont lisibles en clair dans le S3 local, a l'exception des parties
de raisonnement qui ne sont pas conservees. Des secrets presents dans les
prompts, sorties de commande ou fichiers peuvent donc etre enregistres : ne
pas exposer ce S3 local sur un reseau non fiable.

## Installation unique

Ouvrir un terminal Linux/WSL, puis executer :

```bash
cd /home/romain/bigdata/esn81-big-data/opencode-s3-observatory
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-opencode-export.txt
chmod +x scripts/export-opencode-conversations.sh scripts/install-opencode-export-timer.sh
./scripts/install-opencode-export-timer.sh
```

Le dernier message confirme l'activation. Lancer une sauvegarde sans attendre
cinq minutes :

```bash
./scripts/export-opencode-conversations.sh --force
```

## Verifier l'automatisation

```bash
systemctl --user status opencode-s3-export.timer
journalctl --user -u opencode-s3-export.service -n 20 --no-pager
```

Pour conserver l'automatisation apres fermeture de la session Linux/WSL :

```bash
loginctl enable-linger "$USER"
```

## Voir les fichiers dans S3

```bash
curl --fail-with-body --aws-sigv4 "aws:amz:us-east-1:s3" \
  --user "admin:bigdata-local-secret" \
  "http://localhost:8333/bigdata/?list-type=2&prefix=opencode-observatory/"
```

Chaque ligne `<Key>` indique le chemin d'un fichier JSON ou Parquet. Copier
un de ces chemins dans les commandes suivantes.

## Lire un JSON

```bash
curl --fail-with-body --aws-sigv4 "aws:amz:us-east-1:s3" \
  --user "admin:bigdata-local-secret" \
  --output session.json \
  "http://localhost:8333/bigdata/opencode-observatory/sessions/ses_xxx.json"
python3 -m json.tool session.json | less
```

## Lire un Parquet

```bash
curl --fail-with-body --aws-sigv4 "aws:amz:us-east-1:s3" \
  --user "admin:bigdata-local-secret" \
  --output session.parquet \
  "http://localhost:8333/bigdata/opencode-observatory/parquet/sessions/ses_xxx.parquet"
.venv/bin/python scripts/inspect-opencode-parquet.py session.parquet
```

Quitter `less` avec la touche `q`.

## Arreter l'automatisation

```bash
systemctl --user disable --now opencode-s3-export.timer
```
