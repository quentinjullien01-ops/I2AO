# Profils métier I2AO

Chaque dossier ici représente un **profil métier** : la combinaison d'une bibliothèque de paragraphes MT, d'un catalogue de prestations DPGF et d'un profil entreprise, calibrés pour un type de BET particulier.

Cette architecture permet à un BET d'utiliser I2AO sans toucher au code Python — il suffit de copier un profil existant et d'éditer les fichiers markdown / YAML.

## Profils livrés

| Slug | Spécialité | Maturité |
|---|---|---|
| `pathologie-confortement` | Diagnostic structurel, expertise pathologie, MOE confortement | 17 paragraphes MT, 55 prestations DPGF — production |
| `structure-neuve` | BET généraliste structure neuve (logements, tertiaire, ERP) | 6 paragraphes MT, 20 prestations DPGF — exemple/démarrage |

## Structure d'un profil

```
content/profiles/<slug>/
├── bet-profile.md              Profil entreprise (équipe, références, qualifs)
├── mt-library/                 Bibliothèque de paragraphes MT en markdown + frontmatter
│   ├── 00-synthese-executive.md
│   ├── 01-presentation-candidat.md
│   └── ...
└── dpgf-catalog/
    └── prestations.yaml        Catalogue de prestations chiffrées
```

## Sélection du profil actif

Trois mécanismes :

1. **Sidebar de l'application Streamlit** : sélecteur "🧰 Profil métier" en haut de la sidebar. Choix au runtime, persisté dans `session_state`.
2. **Variable d'environnement** `PROFIL_ACTIF` : surclasse le défaut (`pathologie-confortement`) au démarrage de l'app. À mettre dans `.env` ou dans les secrets Streamlit Cloud.
3. **Argument `profil`** sur les fonctions d'engine (`generer_mt`, `generer_dpgf`, `generer_synthese`, `generer_lettre`) si vous appelez les engines directement en CLI / scripts.

## Comment ajouter un nouveau profil

1. Choisis un **slug** descriptif et stable (ex. `fluides-thermique`, `geotechnique-g2`, `genie-civil-vrd`).

2. Crée le dossier :
   ```
   mkdir -p content/profiles/<ton-slug>/mt-library
   mkdir -p content/profiles/<ton-slug>/dpgf-catalog
   ```

3. **`bet-profile.md`** — copie le profil le plus proche et adapte. Ce fichier est utilisé par le moteur MT pour contextualiser les paragraphes (références entreprise, équipe, atouts spécifiques).

4. **`mt-library/*.md`** — chaque fichier markdown est un paragraphe type avec frontmatter YAML :

   ```markdown
   ---
   id: mt-xx-<slug-paragraphe>
   section: Titre de section
   sous_section: null            # ou un titre court
   ordre: 1                       # détermine l'ordre dans le MT généré
   tags: [tag1, tag2]
   adapte_a: [tous]               # ou un sous-ensemble (ex. ["expertise", "moe-confortement"])
   variables:                     # variables {{...}} que Gemini remplira depuis l'analyse AO + bet-profile
     - nom_candidat
     - pouvoir_adjudicateur
   duree_estimee_lecture: "1 min"
   ---

   ## Titre du paragraphe

   Contenu en markdown. Utiliser des `{{variables}}` aux endroits où le contenu
   doit être contextualisé pour l'AO traité.
   ```

5. **`dpgf-catalog/prestations.yaml`** — liste de prestations avec leurs prix unitaires :

   ```yaml
   prestations:
     - code: "1.01"
       libelle: "Description courte de la prestation"
       unite: "forfait"           # ou "jour", "% travaux", "sondage", "mesure"…
       prix_unitaire: 1500
       categorie: "Chapitre du BPU"
       tags: [tag1]
       note: "Commentaire interne (optionnel, non exporté)"
   ```

   Pour les missions MOE en pourcentage du montant travaux, utiliser `unite: "% travaux"` et la quantité passée par Gemini sera le montant des travaux concernés (le moteur applique le pourcentage automatiquement).

6. **Tester** : relancer Streamlit, le sélecteur de profil affiche maintenant ton slug. Lancer un pipeline complet sur une affaire de démo pour vérifier la cohérence du MT et de la DPGF générés.

## Conseils de calibrage

- **Bibliothèque MT** : viser 12 à 18 paragraphes pour un MT complet. En dessous de 8, le MT manquera de chair ; au-dessus de 20, il deviendra redondant.
- **Catalogue DPGF** : 30 à 80 prestations selon la profondeur du métier. Inclure systématiquement un chapitre "Vacations" pour les prestations non listées.
- **`bet-profile.md`** : 1 à 2 pages. Trop court = Gemini généralise. Trop long = le contexte LLM gonfle inutilement.
- **Variables MT** : 3 à 6 par paragraphe. Au-delà, la contextualisation devient hasardeuse.

## Profil actuellement actif

Lire `i2ao.config.PROFIL_ACTIF_DEFAUT` (Python) ou voir le sélecteur en sidebar de l'app.
