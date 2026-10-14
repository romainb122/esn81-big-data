# Export pi vers Redpanda

L'export est fait **en direct par une extension pi**, et non par un timer. Le
hook `message_end` publie chaque message finalise dans le topic existant
`opencode.events` : prompts, texte visible, appels d'outils et resultats.

Les blocs `thinking` et les messages systeme ne sont jamais publies. Si
Redpanda est indisponible, pi continue sa conversation et signale l'erreur dans
sa sortie standard ; une strategie de rejeu pourra ensuite etre ajoutee sans
modifier l'infrastructure aval.

## Activation

L'extension est versionnee dans le projet :

```text
.pi/extensions/observatory-export.ts
```

Depuis la racine du depot, lancer pi normalement :

```bash
cd /home/romain/bigdata/esn81-big-data
pi
```

Si le projet demande une confirmation de confiance, accepter le chargement des
extensions du projet. Pour un test explicite :

```bash
pi --extension ./opencode-s3-observatory/pi/extensions/observatory-export.ts
```

## Verification en direct

Dans un autre terminal :

```bash
cd opencode-s3-observatory
docker compose logs -f iceberg-sink
```

Puis envoyer un message dans pi. Le sink doit afficher un nouvel ajout Bronze
immediatement, sans attendre cinq minutes. Pour publier la Silver et les
agregats :

```bash
docker compose --profile spark run --rm spark-batch
```

Les endpoints locaux sont : dashboard `http://localhost:8501`, documentation
`http://localhost:8502`, Redpanda REST `http://localhost:18082`.

Les prompts et sorties peuvent contenir des secrets : toute l'infrastructure
reste locale et privee.
