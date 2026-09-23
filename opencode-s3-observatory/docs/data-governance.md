# Gouvernance des donnees et garanties ACID

## Couches de donnees

Le projet utilise trois couches explicites. Elles ont des roles differents et
ne doivent pas etre confondues.

- Bronze, zone d'atterrissage : JSON et Parquet ecrits sous
  `opencode-observatory/`. Ces fichiers sont utiles pour l'archive et la reprise
  d'un export, mais ne constituent pas une table transactionnelle.
- Silver, source analytique : table Iceberg `opencode.events`. Le dashboard et
  Spark SQL lisent cette table.
- Gold, donnees derivees : tables Iceberg `opencode.session_summary` et
  `opencode.tool_summary`, produites par le job Spark batch.

Un consommateur analytique ne doit pas lire la couche Bronze directement. Il
doit lire une table Iceberg Silver ou Gold.

## Garanties ACID

Les garanties suivantes s'appliquent a chaque ecriture dans une table Iceberg :

- Atomicite : un commit publie entierement un nouveau snapshot ou ne publie rien.
  Une erreur pendant un export ou un batch laisse le snapshot precedent lisible.
- Coherence : Iceberg verifie le schema et les invariants de metadonnees avant le
  commit. `opencode.events` contient une copie active par session.
- Isolation : chaque lecture consulte un snapshot coherent de table. Une requete
  Spark ne voit pas une table partiellement modifiee.
- Durabilite : les fichiers de donnees et metadonnees sont stockes dans S3, et le
  catalogue REST conserve les references aux snapshots valides.

Ces garanties ne signifient pas que tout le systeme est une transaction globale.
L'envoi du JSON Bronze, du Parquet Bronze et le commit Iceberg sont des etapes
distinctes. La table Iceberg est la source de verite pour les consommateurs.

## Frontieres transactionnelles

- L'export d'une session committe atomiquement sa mise a jour dans
  `opencode.events`.
- Le job Spark batch remplace atomiquement chaque table Gold complete avec
  `createOrReplace`. Les lecteurs voient soit la synthese precedente, soit la
  nouvelle synthese complete.
- Il n'existe pas de transaction atomique entre `opencode.events` et les deux
  tables Gold. Une synthese peut donc etre en retard sur les evenements jusqu'au
  prochain batch. Cette fraicheur doit etre affichee ou documentee si les tables
  Gold sont exposees dans le dashboard.

## Contrat de donnees

Le schema des evenements est defini par
`scripts/opencode-export-to-parquet.py`. Toute modification de ce schema doit :

1. Preserver les champs utilises par le dashboard et les jobs Spark, ou migrer
   tous les consommateurs dans la meme modification.
2. Etre compatible avec le schema Iceberg existant, ou etre accompagnee d'une
   migration versionnee.
3. Etre testee avec un export, une lecture Iceberg et une requete Spark SQL.
4. Etre documentee dans `architecture.md` et, si la decision est durable, dans
   un ADR.

Les champs `reasoning` restent interdits dans tous les exports. Les prompts et
sorties visibles peuvent contenir des secrets : aucun bucket, endpoint ou log de
production ne doit etre rendu public sans une politique de masquage.

## Exploitation et evolution

- Les ecritures sont effectuees par les scripts d'export et le job batch, jamais
  par le dashboard ni par le service Spark SQL.
- Le service Spark SQL accepte seulement des requetes de lecture et limite les
  resultats a 500 lignes.
- Avant une modification structurelle, ajouter un ADR dans `docs/adr/` avec le
  contexte, la decision, les consequences et le plan de migration.
- Apres une evolution, verifier `docker compose config --quiet`, lancer les
  tests pertinents et mettre a jour les commandes de reprise si necessaire.
