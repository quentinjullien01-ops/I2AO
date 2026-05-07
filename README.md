# I2AO — Outil de réponse aux appels d'offres pour BET

[![App live](https://img.shields.io/badge/App-bei2ao.streamlit.app-1A3D6E)](https://bei2ao.streamlit.app)
[![Tests](https://img.shields.io/badge/tests-43%20pass-10b981)](tests/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)

Outil d'aide à la rédaction de réponses aux marchés publics pour bureau d'études techniques, **adaptable à toute spécialité** via un système de profils métier (pathologie / structures, structure neuve, fluides, géotech…).

À partir d'un DCE déposé en PDF (RC + CCAP + CCTP + BPU/DPGF), le pipeline produit en quelques minutes :

| Livrable | Format | Contenu |
|---|---|---|
| **Synthèse des exigences** | JSON + UI | 60 à 80 exigences classées par importance et catégorie |
| **Mémoire technique** | DOCX | Page de garde + sommaire + sections numérotées, contextualisé sur l'AO |
| **Score de couverture MT** | UI | Vérification que chaque exigence bloquante est bien traitée par le MT |
| **DPGF** | XLSX | Récap par chapitre + DQE chiffré + BPU complet, gestion des unités % travaux |
| **Synthèse direction Go/No-go** | DOCX | 1-pager exécutif avec atouts spécifiques, risques, recommandation |
| **Lettre de présentation** | DOCX | Lettre formelle rédigée à partir du contexte de l'AO |
| **Pack candidature** | ZIP | Lettre + MT + DPGF + synthèse, prêt à transmettre au pouvoir adjudicateur |

**App live publique : https://bei2ao.streamlit.app**

---

## Démarrage rapide

### Option A — Utiliser l'app en ligne (sans installation)

1. Ouvrir https://bei2ao.streamlit.app
2. Sélectionner une affaire de démo dans la sidebar
3. Cliquer onglet par onglet pour explorer le pipeline

L'app live partage la clé Gemini de son propriétaire et a un plafond de dépense.
Pour des tests intensifs ou des données confidentielles, utiliser l'option B.

### Option B — Installation locale

```bash
git clone https://github.com/quentinjullien01-ops/I2AO
cd I2AO
python -m venv .venv
.venv/Scripts/pip install -e .
```

Créer le fichier `.env` à la racine :

```dotenv
GOOGLE_API_KEY=AIza...                          # clé Gemini (gratuite, https://aistudio.google.com/apikey)
CANDIDAT_NOM=Mon BET SA                          # affiché dans les livrables
PROFIL_ACTIF=pathologie-confortement             # profil métier par défaut
```

Lancer l'app :

```bash
.venv/Scripts/python.exe -m streamlit run src/i2ao/app.py
```

Ouvrir http://localhost:8501. Deux affaires de démo sont créées automatiquement.

---

## Adapter l'outil à un autre BET

Tout BET peut adopter I2AO **sans toucher au code Python**. Trois mécanismes :

### 1. Wizard graphique dans l'app

Sidebar → Vue → **🧰 Gestion des profils** :
- **Créer un profil** depuis un template vierge ou en dupliquant un profil existant
- **Importer un profil** depuis un ZIP (échange entre BE)
- **Exporter un profil** au format ZIP (à déposer dans une fork pour persistence)

### 2. Édition manuelle des fichiers de profil

Un profil est un dossier sous [content/profiles/](content/profiles/) :

```
content/profiles/<slug>/
├── bet-profile.md              Profil entreprise (équipe, références, qualifs)
├── mt-library/                 Paragraphes MT en markdown + frontmatter
│   ├── 00-synthese-executive.md
│   └── ...
└── dpgf-catalog/
    └── prestations.yaml        Catalogue de prestations chiffrées
```

Voir [content/profiles/README.md](content/profiles/README.md) pour le guide détaillé.

### 3. Profils livrés en exemple

| Slug | Spécialité | Maturité |
|---|---|---|
| `pathologie-confortement` | Diagnostic, expertise pathologie, MOE confortement | 17 paragraphes MT, 55 prestations DPGF |
| `structure-neuve` | BET généraliste structure neuve (logements, tertiaire, ERP) | 7 paragraphes MT, 21 prestations DPGF |

---

## Stack technique

- **Python 3.12+** (testé sur 3.14)
- **Streamlit** 1.39+ pour l'UI multi-onglets avec graphiques Plotly théme-adaptatifs
- **Google Gemini** (`gemini-2.5-flash` par défaut) — sortie structurée pydantic, retry exponentiel sur 5xx, gestion thinking
- **pdfplumber** + **pymupdf** + **pytesseract** (OCR optionnel) pour ingestion PDF
- **python-docx** pour les exports DOCX (MT, lettre, synthèse)
- **openpyxl** pour la DPGF en XLSX (récap + DQE + BPU)
- **reportlab** pour la génération de DCE fictifs de démo

---

## Pipeline complet

```
PDFs DCE                                 ← entrée utilisateur
   │
   ▼ pdf_parser.parse_pdf()              pdfplumber → pymupdf → OCR Tesseract (si dispo)
   │
   ▼ extractor.extraire_analyse_ao()     ► Gemini → AnalyseAO (60-80 exigences structurées)
   │
   ├─► mt_engine.generer_mt(profil)              ► Gemini → MemoireTechniqueGenere
   │   ├─► docx_export.exporter_mt_docx()         page de garde + sommaire + sections
   │   └─► coverage.evaluer_couverture()         ► Gemini → score MT vs exigences
   │
   ├─► dpgf_engine.generer_dpgf(profil)          ► Gemini → DPGFGeneree
   │   └─► xlsx_export.exporter_dpgf_xlsx()       Récap + DQE + BPU
   │
   ├─► synthese.generer_synthese(profil)         ► Gemini → SyntheseDirection (Go/No-go)
   │   └─► synthese.exporter_synthese_docx()      1-pager DOCX dashboard
   │
   └─► candidature.generer_lettre(profil)        ► Gemini → LettrePresentation
       ├─► candidature.exporter_lettre_docx()     DOCX formel
       └─► candidature.creer_pack_zip()           ZIP MT + DPGF + lettre + synthèse
```

**Coût LLM indicatif** sur un DCE de 30 pages : ~0,03 USD pour le pipeline complet avec `gemini-2.5-flash` (largement dans le free tier).

---

## Structure du projet

```
I2AO/
├── content/profiles/<slug>/      Profils métier (mt-library, dpgf-catalog, bet-profile)
├── data/
│   ├── samples/                  DCE fictifs de démo (PDF + sources markdown)
│   ├── affaires/                 Une affaire = réponse à un AO (gitignored)
│   └── output/                   Artefacts CLI (gitignored)
├── scripts/
│   ├── lancer_app.bat            Lance Streamlit (Windows)
│   ├── generate_demo_dce.py      (Re)génère les DCE fictifs
│   └── run_pipeline.py           Pipeline CLI complet
├── src/i2ao/                     Code applicatif (~6 KLOC)
│   ├── app.py                    Application Streamlit (sidebar + 7 onglets + 3 vues)
│   ├── affaires.py               Persistance des affaires sur disque
│   ├── candidature.py            Lettre de présentation + pack ZIP
│   ├── charts.py                 Graphiques Plotly adaptatifs light/dark
│   ├── config.py                 Chemins, clé API, profil actif
│   ├── content_loader.py         Loaders pour les profils métier
│   ├── coverage.py               Score de couverture MT
│   ├── docx_export.py            Export DOCX du mémoire technique
│   ├── dpgf_engine.py            Génération DPGF (programme + chiffrage)
│   ├── extractor.py              Extraction structurée des exigences
│   ├── llm.py                    Wrapper Gemini (retry, structured output)
│   ├── mt_engine.py              Assemblage du mémoire technique
│   ├── pdf_parser.py             PDF → texte + détection type de pièce
│   ├── profiles_admin.py         Wizard de création / import / export ZIP
│   ├── synthese.py               Synthèse direction Go/No-go
│   ├── usage_tracker.py          Compteur de coût LLM session
│   └── xlsx_export.py            Export XLSX de la DPGF
├── tests/                        Suite pytest (43 tests)
└── pyproject.toml                Dépendances + métadonnées
```

---

## Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

43 tests couvrent : parser PDF, content loader, engine DPGF (gestion `% travaux`), moteur MT (variables non remplies), gestion des affaires, slugify. Les fonctions LLM-dépendantes ne sont pas testées (coût et latence) mais leurs schémas pydantic sont vérifiés.

---

## Déploiement sur Streamlit Cloud (compagnon de cette doc)

L'app live https://bei2ao.streamlit.app est déployée via [Streamlit Community Cloud](https://share.streamlit.io). Workflow :

1. Push sur `main` → redéploiement automatique en 2-5 min
2. Secrets configurés via Settings → Secrets de l'app, format TOML
3. `requirements.txt` (deps Python) et `packages.txt` (apt : `tesseract-ocr`, `tesseract-ocr-fra`) sont lus à chaque build

Pour ton propre déploiement : forke ce repo, va sur https://share.streamlit.io, "Create app from GitHub", indique le repo, branche `main`, fichier `src/i2ao/app.py`, et configure tes secrets.

---

## Pour aller plus loin

- [SCENARIO-DEMO.md](SCENARIO-DEMO.md) — scénario de démonstration commenté en 7 minutes
- [content/profiles/README.md](content/profiles/README.md) — guide d'adaptation à un nouveau profil métier
- Issues / suggestions : https://github.com/quentinjullien01-ops/I2AO/issues

---

*Outil développé en mai 2026 comme livrable de démonstration produit-IA pour le secteur BET. Code MIT-licensable, contributions bienvenues.*
