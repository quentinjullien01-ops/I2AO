# Scénario de démo — Pitch Repair Ingénierie

Durée cible : **5 à 7 minutes**. Le but n'est pas de montrer le code, c'est de prouver
en faits que l'outil fait gagner du temps et de l'argent à un BET pathologie qui
voudrait s'attaquer aux marchés publics.

## Avant l'entretien

1. Ouvrir un terminal dans le dossier `I2AO/`
2. Lancer l'app : double-cliquer sur **`scripts/lancer_app.bat`** ou exécuter
   `.venv/Scripts/python.exe -m streamlit run src/i2ao/app.py`
3. Le navigateur s'ouvre sur **http://localhost:8501**
4. Vérifier dans la barre latérale : **🤖 Connecté à `gemini-2.5-flash`**
5. Sélectionner l'affaire **« OPH des Vallées de l'Isère — diag + MOE confortement »**
   (créée automatiquement la première fois)

## Storyboard du pitch (5 min)

### Minute 1 — Le constat business

> *« Repair Ingénierie est un spécialiste pathologie/consolidation reconnu sur les
> sinistres assurance. Mais sur le marché public — bailleurs sociaux, OPH, collectivités
> au patrimoine dégradé, monuments historiques — vous n'êtes pas présents. Pourtant
> c'est exactement votre cœur de métier. La raison historique : répondre à un AO public,
> c'est un mémoire technique de 30 pages + un BPU + un DPGF, et ça mobilise un ingénieur
> senior plusieurs jours par dossier. J'ai construit un outil qui divise ce coût par 10. »*

### Minute 2 — L'entrée du DCE (onglet 📂 DCE)

- Pointer les 4 PDF déjà déposés (RC, CCAP, CCTP, BPU = **27 pages, 53 000 caractères**)
- Souligner : *« C'est un vrai DCE OPH plausible — j'en ai produit un fictif pour la démo
  parce que je n'allais pas embêter un acheteur public en récupérant un vrai DCE confidentiel,
  mais on peut le brancher demain sur un PLACE réel. »*

### Minute 3 — L'analyse (onglet 🔍 Analyse)

- Cliquer **« Lancer l'analyse »** ou pointer l'analyse déjà calculée
- En **30 secondes**, Gemini extrait :
  - L'identité complète du marché (objet, PA, type, montant max, durée, dates)
  - **5 à 6 points d'attention business** (créneau RGA, site occupé, 60% valeur technique, etc.)
  - **70 à 80 exigences structurées** (pièces à fournir / critères de jugement / délais /
    exigences techniques / qualifications / références / moyens) classées par importance
- Démontrer le filtre par importance : *« Voici les 19 exigences bloquantes que vous ne
  pouvez pas vous permettre de rater. »*

### Minute 4 — Le mémoire technique (onglet 📝 Mémoire technique)

- Cliquer **« Générer le MT »** ou montrer le MT déjà produit
- Souligner :
  - **10 sections** assemblées à partir de la bibliothèque de paragraphes type
  - Chaque paragraphe est calibré pathologie/consolidation, pas BET généraliste
  - Les variables (`{{nom_ouvrage}}`, `{{typologie_desordres}}`, etc.) sont remplies
    automatiquement à partir de l'analyse
  - **Téléchargement DOCX** prêt à éditer dans Word, signature et envoi
- Afficher le paragraphe « Approche RGA » : *« Regardez : ça parle micropieux, pressiomètre,
  limites d'Atterberg, valeur de bleu. Ça n'a pas l'air généré, ça a l'air écrit par un
  structureur qui sait. »*

### Minute 5 — La DPGF (onglet 💰 DPGF)

- Cliquer **« Générer la DPGF »** ou montrer celle déjà produite
- Pointer :
  - **55 prestations au BPU** (le catalogue de prix unitaires de Repair)
  - Gemini a lu l'**article 9 du CCTP** et a identifié seul le programme indicatif
    (6 diagnostics + 2 MOE 250k€ + 1 MOE 600k€ + 8 expertises + 4 études)
  - **DQE chiffré : 181 200 € HT** — dont les missions MOE calculées en %
    travaux automatiquement
  - **Téléchargement XLSX** propre, deux feuilles BPU + DQE

### Minute 6 — Le pitch business

> *« Récap : un DCE de 30 pages déposé, 90 secondes de calcul Gemini, vous avez
> 70 exigences listées, un mémoire technique brouillon de 10 sections en français
> métier, et une DPGF chiffrée à 181 k€. Coût LLM : moins d'un centime.
> Du temps junior réinvesti sur la relecture finale et la personnalisation —
> un AO traité en 3-4 heures au lieu de 3-4 jours. »*

> *« Ce n'est pas un produit fini, c'est une démo. Mon job de responsable
> développement commercial chez vous, c'est de qualifier les vrais AO du créneau,
> mais aussi de transformer cet outil en avantage concurrentiel reproductible. »*

### Si on vous pose des questions

- **« Vous avez utilisé quel LLM ? »** Google Gemini 2.5 Flash. Free tier de Google AI Studio.
  Pourrait basculer sur Claude Sonnet ou Gemini Pro si on veut plus de qualité brute.
- **« Combien ça coûte ? »** Aujourd'hui zéro grâce au free tier. À l'usage intensif,
  comptez quelques centimes par AO — négligeable face à l'économie de temps.
- **« Et la confidentialité ? »** Les DCE publics sont publiés. Aucun risque sur les marchés
  publics. Pour des AO privés (très rare en pathologie), il y a Gemini sur Vertex AI ou
  Anthropic en mode privé / on-premise.
- **« On peut le faire évoluer ? »** Bibliothèque de paragraphes en markdown, catalogue
  DPGF en YAML — modifiable sans toucher au code. La maintenance est à la portée d'un
  ingénieur junior.

## Si on demande à voir le code

- L'arborescence est lisible : `src/i2ao/`
- Pointer en particulier :
  - `extractor.py` — le prompt système qui extrait les exigences
  - `mt_engine.py` — le moteur d'assemblage MT
  - `dpgf_engine.py` — la lecture du programme indicatif et le chiffrage
- Total : ~1 500 lignes de Python. Lisible, testable.

## Plan B si le wifi tombe / Gemini est down

Tous les artefacts sont **déjà générés et sauvegardés** dans le dossier de l'affaire de démo.
Si l'API Gemini est inaccessible, l'app affiche **directement** le résultat précalculé.
La démo continue sans rien.
