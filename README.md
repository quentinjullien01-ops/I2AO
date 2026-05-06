# I2AO — Outil de réponse aux appels d'offres

Outil d'aide à la rédaction de réponses aux marchés publics pour bureau d'études structures, calibré sur le créneau **pathologie / diagnostic / confortement**.

## Cible business

**Repair Ingénierie** — spécialiste expertise structurelle et travaux de consolidation (béton, métal, bois). Filiale travaux : Syma Consolidation. Aujourd'hui positionné sur les sinistres assurance privés, ce projet vise à ouvrir le canal des **marchés publics** (bailleurs sociaux, OPH, collectivités, MH).

Voir [SCENARIO-DEMO.md](SCENARIO-DEMO.md) pour le storyboard du pitch d'entretien.

## Périmètre fonctionnel

À partir d'un DCE déposé (PDFs), l'outil produit :

1. **Synthèse des exigences** — pièces à fournir, critères de jugement, délais, exigences techniques par lot, classées par importance (bloquant / important / mineur)
2. **Mémoire technique pré-rédigé** (.docx) — assemblage contextualisé de paragraphes types calibrés métier pathologie
3. **DPGF type** (.xlsx) — BPU complet aux prix marché + DQE chiffré sur le programme indicatif extrait du CCTP

## Stack

- **Python 3.14** + **Streamlit** (UI)
- **Google Gemini** (`gemini-2.5-flash` par défaut) avec sortie structurée pydantic + retry exponentiel
- **pdfplumber** + **pymupdf** (parsing DCE multi-pièces)
- **pytesseract** + **Tesseract OCR** (fallback pour PDF scannés — binaire à installer séparément)
- **python-docx** (export mémoire technique avec page de garde et sommaire)
- **openpyxl** (export DPGF avec feuille Récapitulatif)
- **reportlab** (génération du DCE fictif de démo)
- **pytest** (suite de tests, 41+ tests)
- **SQLite** (base locale, optionnelle pour les affaires multiples)

## Lancement

### Première fois

```bash
cd I2AO
python -m venv .venv
.venv/Scripts/pip install -e .
```

Puis créer le fichier `.env` à la racine avec votre clé Gemini :

```
GOOGLE_API_KEY=AIza...
```

(clé gratuite récupérable sur https://aistudio.google.com/apikey)

### Lancer l'app

Double-clic sur `scripts/lancer_app.bat` ou en CLI :

```bash
.venv/Scripts/python.exe -m streamlit run src/i2ao/app.py
```

Puis ouvrir http://localhost:8501

Deux affaires de démo (OPH des Vallées de l'Isère et Commune de Saint-Marcellin) sont créées automatiquement la première fois.

### Pipeline en CLI

Pour exécuter le pipeline complet sur une affaire (utile en debug) :

```bash
.venv/Scripts/python.exe scripts/run_pipeline.py demo-oph-vallees-isere
```

Sans argument, le script liste les affaires disponibles avec leur état d'avancement.

### Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -v
```

41 tests couvrent le parser PDF, le content loader, les engines DPGF/MT et la gestion des affaires. Les tests qui dépendent du LLM ne sont pas inclus (coût et lenteur).

### OCR pour PDF scannés (optionnel)

Si tu reçois des DCE scannés (PDF sans couche texte), installe Tesseract OCR pour que l'app les traite automatiquement :

- **Windows** : https://github.com/UB-Mannheim/tesseract/wiki — choisir la version 64 bits, cocher le pack de langue **français** lors de l'installation
- **macOS** : `brew install tesseract tesseract-lang`
- **Linux** : `apt install tesseract-ocr tesseract-ocr-fra`

L'app détecte automatiquement la disponibilité de Tesseract — si absent, un avertissement explicite est affiché à l'upload du PDF, mais l'app continue de fonctionner sur les autres documents.

## Structure du projet

```
I2AO/
├── content/
│   ├── mt-library/         14 paragraphes MT calibrés pathologie/consolidation
│   ├── dpgf-catalog/       55 prestations DPGF avec prix marché 2026
│   └── repair-profile.md   Profil entreprise (Repair Ingénierie)
├── data/
│   ├── samples/source/     Sources markdown des DCE fictifs de démo
│   ├── samples/            DCE fictifs de démo (PDF générés)
│   ├── affaires/           Une affaire = une réponse à un AO (créées dynamiquement)
│   └── output/             Artefacts produits par les scripts CLI
├── scripts/
│   ├── lancer_app.bat              Lance Streamlit (Windows)
│   ├── generate_demo_dce.py        (Re)génère les DCE fictifs depuis les sources markdown
│   ├── run_pipeline.py             Pipeline CLI complet sur une affaire (DCE → tout)
│   ├── generer_mt_demo.py          Pipeline CLI partiel : extraction + MT + DOCX
│   └── generer_dpgf_demo.py        Pipeline CLI partiel : extraction + DPGF + XLSX
├── src/i2ao/                       Code applicatif
│   ├── app.py                      Application Streamlit principale (5 onglets)
│   ├── affaires.py                 Gestion des affaires sur disque
│   ├── config.py                   Chemins projet, clé API, modèle LLM
│   ├── content_loader.py           Charge mt-library + dpgf-catalog
│   ├── coverage.py                 Score de couverture du MT vs exigences
│   ├── db.py                       Schéma SQLite (optionnel, non utilisé par l'app)
│   ├── docx_export.py              Export DOCX du MT (cover + sommaire + sections)
│   ├── dpgf_engine.py              Génération DPGF (programme + chiffrage % travaux)
│   ├── extractor.py                Extraction structurée des exigences via Gemini
│   ├── llm.py                      Wrapper Gemini : retry, thinking, structured output
│   ├── mt_engine.py                Assemblage du mémoire technique via Gemini
│   ├── pdf_parser.py               PDF → texte (pdfplumber → pymupdf → OCR) + détection pièce
│   ├── synthese.py                 Synthèse direction Go/No-go (1-pager DOCX)
│   └── xlsx_export.py              Export XLSX (Récap + DQE + BPU)
├── tests/                          Suite pytest (41 tests)
└── pyproject.toml                  Dépendances et build
```

## Pipeline complet

```
PDFs DCE                                 (input)
   │
   ▼ pdf_parser.parse_pdf()              pdfplumber → pymupdf → OCR
   │
   ▼ extractor.extraire_analyse_ao()     ► Gemini → AnalyseAO (~70 exigences)
   │
   ├─► mt_engine.generer_mt()            ► Gemini → MemoireTechniqueGenere (14 sections)
   │   ├─► docx_export.exporter_mt_docx()       Word, cover + sommaire + sections numérotées
   │   └─► coverage.evaluer_couverture()        ► Gemini → score MT vs exigences
   │
   ├─► dpgf_engine.generer_dpgf()        ► Gemini → DPGFGeneree (BPU complet + DQE chiffré)
   │   └─► xlsx_export.exporter_dpgf_xlsx()     Excel : Récap + DQE + BPU
   │
   └─► synthese.generer_synthese()       ► Gemini → SyntheseDirection (1-pager Go/No-go)
       └─► synthese.exporter_synthese_docx()    Word, 1 page direction
```

Coût indicatif sur le DCE de démo : **~0,03 USD** pour le pipeline complet (toutes étapes incluant couverture et synthèse) avec Gemini 2.5 Flash. Largement dans le free tier.
