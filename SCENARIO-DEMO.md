# Scénario de démonstration — I2AO

Durée cible : **5 à 7 minutes**. Le but est de prouver en faits que l'outil fait gagner du temps et de l'argent à un BET pathologie qui veut s'attaquer aux marchés publics.

## Avant la démo

1. Ouvrir un terminal dans le dossier I2AO
2. Lancer l'app : double-clic sur **`scripts/lancer_app.bat`** ou `python -m streamlit run src/i2ao/app.py`
3. Le navigateur s'ouvre sur http://localhost:8501
4. Vérifier dans la barre latérale : **🤖 Connecté à `gemini-2.5-flash`**
5. Sélectionner une affaire de démo dans la sidebar (deux livrées par défaut)

## Storyboard du pitch (5 min)

### Minute 1 — Le constat business

Un BET spécialiste pathologie (consolidation, RGA, expertise structurelle, travaux sur ouvrages anciens) qui vit sur les sinistres assurance laisse souvent de côté les marchés publics — bailleurs sociaux, OPH, collectivités au patrimoine dégradé, monuments historiques. Pourtant c'est précisément un cœur de métier transposable. La raison historique : répondre à un AO public, c'est un mémoire technique de 30 pages + un BPU + un DPGF + une lettre de présentation, et ça mobilise un ingénieur senior plusieurs jours par dossier. **I2AO divise ce coût par 10.**

### Minute 2 — L'entrée du DCE (onglet 📂 DCE)

- Pointer les pièces déjà déposées (RC, CCAP, CCTP, BPU/DPGF)
- Souligner : *« C'est un DCE fictif crédible — j'en ai produit deux pour la démo, mais on peut brancher l'app sur un vrai DCE réel demain. »*

### Minute 3 — L'analyse (onglet 🔍 Analyse)

- Cliquer **« Lancer l'analyse »** ou pointer l'analyse déjà calculée
- En **30 secondes**, Gemini extrait :
  - L'identité complète du marché (objet, PA, type, montant max, durée, dates)
  - **5 à 6 points d'attention business** (créneau RGA, site occupé, 60 % valeur technique, etc.)
  - **70 à 80 exigences structurées** (pièces à fournir / critères de jugement / délais / exigences techniques / qualifications / références / moyens), classées par importance
- Démontrer le filtre par importance : *« Voici les 19 exigences bloquantes que vous ne pouvez pas vous permettre de rater. »*

### Minute 4 — Le mémoire technique (onglet 📝 Mémoire technique)

- Cliquer **« Générer le MT »** ou montrer le MT déjà produit
- Souligner :
  - **17 sections** assemblées à partir d'une bibliothèque de paragraphes types
  - Chaque paragraphe est calibré pathologie / consolidation, pas BET généraliste
  - Les variables (`{{nom_ouvrage}}`, `{{typologie_desordres}}`, etc.) sont remplies automatiquement à partir de l'analyse
  - **Téléchargement DOCX** avec page de garde + sommaire + sections numérotées, prêt à éditer dans Word
- Pointer un paragraphe métier-rich (par ex. « Approche RGA ») : ça parle micropieux, pressiomètre, limites d'Atterberg, valeur de bleu — ça n'a pas l'air généré, ça a l'air écrit par un structureur qui sait
- Après le MT : **score de couverture** (un visuel jauge + donut) : pour chaque exigence bloquante du DCE, l'outil vérifie si le MT la traite. *« L'outil ne se contente pas de générer, il vérifie sa propre conformité. »*

### Minute 5 — La DPGF (onglet 💰 DPGF)

- Cliquer **« Générer la DPGF »** ou montrer celle déjà produite
- Pointer :
  - **55 prestations au BPU** avec prix marché
  - Gemini a lu le CCTP et a identifié seul le programme indicatif à chiffrer
  - **DQE chiffré** automatiquement, avec gestion correcte des unités (`forfait`, `% travaux`, `sondage`, `mesure`…)
  - **Téléchargement XLSX** : 3 feuilles (Récapitulatif avec sous-totaux + TVA + TTC, DQE chiffré, BPU complet)

### Minute 6 — Le pack candidature (onglet 📦 Candidature)

- Cliquer **« Générer la lettre »** : Gemini rédige une lettre de présentation contextualisée (en-tête, destinataire correctement nommé, objet, 3 paragraphes corps, liste des pièces jointes, formule de politesse, signataire)
- Cliquer **« Assembler le ZIP »** : produit un fichier `pack-candidature-<slug>.zip` qui contient lettre + MT + DPGF + synthèse direction. C'est *le* fichier que le BET envoie au pouvoir adjudicateur.

### Minute 7 — La synthèse direction (onglet 📊 Go / No-go)

- Pointer le 1-pager direction : faits clés + atouts spécifiques croisés AO × profil entreprise + risques + recommandation argumentée
- *« Pour un dirigeant pressé qui doit valider l'engagement sur l'AO en 30 secondes, c'est ce document qui suffit. »*

### Conclusion business

Récap : un DCE de 30 pages déposé, environ une minute de calcul Gemini, vous avez 70 exigences listées, un mémoire technique brouillon de 17 sections en français métier, une DPGF chiffrée, une lettre de présentation, une synthèse direction et un pack ZIP prêt à envoyer. **Coût LLM : moins de 5 centimes.** Du temps senior réinvesti sur la relecture finale et la personnalisation — un AO traité en 3-4 heures au lieu de 3-4 jours.

## Si on demande à voir le code

- L'arborescence est lisible : `src/i2ao/`
- Pointer en particulier :
  - `extractor.py` — le prompt système qui extrait les exigences
  - `mt_engine.py` — le moteur d'assemblage MT
  - `dpgf_engine.py` — la lecture du programme indicatif et le chiffrage
  - `coverage.py` — l'évaluation de la couverture du MT
  - `synthese.py` + `candidature.py` — synthèse direction et lettre + pack ZIP
- 43 tests pytest couvrent les fonctions critiques (`pytest tests/`)

## Plan B si l'API LLM est inaccessible pendant la démo

Tous les artefacts sont **déjà générés et sauvegardés** dans le dossier de chaque affaire de démo. Si Gemini est inaccessible, l'app affiche directement les résultats précalculés. La démo continue.

## Pour adapter l'outil à un BET spécifique

1. Renseigner `content/bet-profile.md` avec les données réelles du BET (effectif, références anonymisables, qualifications OPQIBI, logiciels, atouts spécifiques)
2. Ajuster `content/dpgf-catalog/prestations.yaml` avec la grille tarifaire réelle du BET (les valeurs livrées sont des ratios marché 2026 indicatifs)
3. Renseigner `CANDIDAT_NOM` dans `.env` pour que les livrables portent le nom de l'entreprise
4. Optionnellement, enrichir la bibliothèque MT avec des paragraphes propres au BET (méthodologies internes spécifiques, certifications, partenariats…)
