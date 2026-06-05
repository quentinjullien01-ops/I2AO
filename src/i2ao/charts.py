"""Graphiques Plotly réutilisables — palette cohérente avec le thème Mission Control.

Charts adaptatifs au thème Streamlit (light / dark) :
- Backgrounds transparents pour s'intégrer au fond Streamlit
- Couleurs de texte et grilles ajustées selon le thème
"""

from __future__ import annotations

import math
from collections import Counter

import plotly.graph_objects as go

# Palette projet — alignée sur le thème "Mission Control" (#38bdf8 primary)
COULEUR_PRIMAIRE = "#38bdf8"
COULEUR_PRIMAIRE_CLAIR = "#7dd3fc"
COULEUR_SECONDAIRE = "#818cf8"
COULEUR_VERT = "#10b981"
COULEUR_ORANGE = "#f59e0b"
COULEUR_ROUGE = "#ef4444"
COULEUR_GRIS = "#64748b"

# Palette catégories — couleurs vives, visibles sur fond sombre
PALETTE_CATEGORIES = [
    "#38bdf8",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#818cf8",
    "#06b6d4",
    "#f472b6",
    "#a3e635",
    "#fb923c",
    "#c084fc",
    "#2dd4bf",
]


def _is_dark_theme() -> bool:
    """Toujours True — l'app utilise le thème Mission Control (fond sombre forcé)."""
    return True


def _theme_colors() -> dict:
    """Couleurs adaptatives selon thème détecté."""
    dark = _is_dark_theme()
    if dark:
        return {
            "text": "#e5e7eb",
            "text_secondaire": "#9ca3af",
            "grid": "rgba(255,255,255,0.12)",
            "annotation_centre": "#dbeafe",  # bleu très clair pour score au centre
            "annotation_secondaire": "#9ca3af",
            "donut_border": "#0e1117",       # bord donut = fond Streamlit dark
        }
    return {
        "text": "#374151",
        "text_secondaire": "#6b7280",
        "grid": "rgba(0,0,0,0.08)",
        "annotation_centre": "#1a3d6e",
        "annotation_secondaire": "#6b7280",
        "donut_border": "#ffffff",
    }


def _layout_base() -> dict:
    colors = _theme_colors()
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Calibri, sans-serif", size=12, color=colors["text"]),
        margin=dict(l=10, r=10, t=40, b=10),
    )


# ---------------------------------------------------------------------------
# Donut couverture MT
# ---------------------------------------------------------------------------

def donut_couverture(
    nb_couvertes: int,
    nb_partielles: int,
    nb_non_couvertes: int,
    nb_non_applicables: int,
    score_pct: float,
) -> go.Figure:
    theme = _theme_colors()
    labels = ["Couvertes", "Partielles", "Non couvertes", "N/A (hors MT)"]
    values = [nb_couvertes, nb_partielles, nb_non_couvertes, nb_non_applicables]
    colors = [COULEUR_VERT, COULEUR_ORANGE, COULEUR_ROUGE, COULEUR_GRIS]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=colors, line=dict(color=theme["donut_border"], width=2)),
            textinfo="value",
            textfont=dict(size=14, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value} exigences<br>%{percent}<extra></extra>",
        )
    )
    fig.add_annotation(
        text=f"<b>{score_pct:.0f}%</b>",
        x=0.5,
        y=0.55,
        font=dict(size=36, color=theme["annotation_centre"]),
        showarrow=False,
    )
    fig.add_annotation(
        text="couverture",
        x=0.5,
        y=0.42,
        font=dict(size=11, color=theme["annotation_secondaire"]),
        showarrow=False,
    )
    fig.update_layout(
        **_layout_base(),
        showlegend=True,
        legend=dict(
            orientation="h",
            y=-0.05,
            x=0.5,
            xanchor="center",
            font=dict(color=theme["text"]),
        ),
        height=320,
    )
    return fig


# ---------------------------------------------------------------------------
# Bar horizontal — exigences par catégorie
# ---------------------------------------------------------------------------

def bar_exigences_par_categorie(exigences: list) -> go.Figure:
    theme = _theme_colors()
    cats = Counter(e.categorie for e in exigences)
    cats_sorted = sorted(cats.items(), key=lambda x: x[1], reverse=True)
    labels = [c for c, _ in cats_sorted]
    valeurs = [v for _, v in cats_sorted]

    couleurs = [PALETTE_CATEGORIES[i % len(PALETTE_CATEGORIES)] for i in range(len(labels))]

    fig = go.Figure(
        go.Bar(
            y=labels,
            x=valeurs,
            orientation="h",
            marker=dict(color=couleurs),
            text=valeurs,
            textposition="outside",
            textfont=dict(size=12, color=theme["text"]),
            hovertemplate="<b>%{y}</b><br>%{x} exigences<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout_base(),
        height=max(280, 30 * len(labels) + 80),
        xaxis=dict(showgrid=True, gridcolor=theme["grid"], title=None, color=theme["text"]),
        yaxis=dict(autorange="reversed", title=None, color=theme["text"]),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Bar empilé — exigences par importance
# ---------------------------------------------------------------------------

def bar_exigences_par_importance(exigences: list) -> go.Figure:
    theme = _theme_colors()
    importances = Counter(e.importance for e in exigences)
    ordre = ["bloquant", "important", "mineur"]
    couleurs_imp = {
        "bloquant": COULEUR_ROUGE,
        "important": COULEUR_ORANGE,
        "mineur": COULEUR_SECONDAIRE,
    }
    libelles = {
        "bloquant": "Bloquantes",
        "important": "Importantes",
        "mineur": "Mineures",
    }

    fig = go.Figure()
    for imp in ordre:
        nb = importances.get(imp, 0)
        if nb > 0:
            fig.add_trace(
                go.Bar(
                    name=libelles[imp],
                    x=[nb],
                    y=["Exigences"],
                    orientation="h",
                    marker=dict(color=couleurs_imp[imp]),
                    text=[f"{nb}"],
                    textposition="inside",
                    insidetextanchor="middle",
                    textfont=dict(size=14, color="white", family="Inter"),
                    hovertemplate=f"<b>{libelles[imp]}</b><br>%{{x}} exigences<extra></extra>",
                )
            )
    fig.update_layout(
        **_layout_base(),
        height=140,
        barmode="stack",
        xaxis=dict(showgrid=False, showticklabels=False, title=None),
        yaxis=dict(showgrid=False, showticklabels=False, title=None),
        legend=dict(
            orientation="h",
            y=-0.4,
            x=0.5,
            xanchor="center",
            font=dict(color=theme["text"]),
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Bar — DQE par chapitre
# ---------------------------------------------------------------------------

def bar_dqe_par_categorie(dqe_lignes: list) -> go.Figure:
    theme = _theme_colors()
    par_cat: dict[str, float] = {}
    for ligne in dqe_lignes:
        par_cat[ligne.categorie] = par_cat.get(ligne.categorie, 0.0) + ligne.montant

    items = sorted(par_cat.items(), key=lambda x: x[1], reverse=True)
    labels = [c for c, _ in items]
    valeurs = [v for _, v in items]
    total = sum(valeurs)
    couleurs = [PALETTE_CATEGORIES[i % len(PALETTE_CATEGORIES)] for i in range(len(labels))]

    text_in = [f"{(v / total * 100):.0f}%" if total else "" for v in valeurs]
    text_out = [f"{v:,.0f} €".replace(",", " ") for v in valeurs]

    fig = go.Figure(
        go.Bar(
            y=labels,
            x=valeurs,
            orientation="h",
            marker=dict(color=couleurs),
            text=text_out,
            textposition="outside",
            textfont=dict(size=11, color=theme["text"]),
            customdata=text_in,
            hovertemplate="<b>%{y}</b><br>%{x:,.2f} € HT<br>(%{customdata} du DQE)<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout_base(),
        height=max(280, 30 * len(labels) + 80),
        xaxis=dict(
            showgrid=True,
            gridcolor=theme["grid"],
            title="Montant HT (€)",
            color=theme["text"],
        ),
        yaxis=dict(autorange="reversed", title=None, color=theme["text"]),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Donut — répartition DQE par chapitre
# ---------------------------------------------------------------------------

def donut_repartition_dqe(dqe_lignes: list, total_he: float) -> go.Figure:
    theme = _theme_colors()
    par_cat: dict[str, float] = {}
    for ligne in dqe_lignes:
        par_cat[ligne.categorie] = par_cat.get(ligne.categorie, 0.0) + ligne.montant

    items = sorted(par_cat.items(), key=lambda x: x[1], reverse=True)
    labels = [c for c, _ in items]
    valeurs = [v for _, v in items]
    couleurs = [PALETTE_CATEGORIES[i % len(PALETTE_CATEGORIES)] for i in range(len(labels))]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=valeurs,
            hole=0.55,
            marker=dict(colors=couleurs, line=dict(color=theme["donut_border"], width=2)),
            textinfo="percent",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value:,.2f} € HT<br>%{percent}<extra></extra>",
        )
    )
    fig.add_annotation(
        text=f"<b>{total_he:,.0f} €</b>".replace(",", " "),
        x=0.5,
        y=0.55,
        font=dict(size=22, color=theme["annotation_centre"]),
        showarrow=False,
    )
    fig.add_annotation(
        text="DQE HT",
        x=0.5,
        y=0.42,
        font=dict(size=11, color=theme["annotation_secondaire"]),
        showarrow=False,
    )
    fig.update_layout(
        **_layout_base(),
        height=380,
        showlegend=True,
        legend=dict(orientation="v", y=0.5, x=1.05, font=dict(color=theme["text"])),
    )
    return fig


# ---------------------------------------------------------------------------
# Gauge — score de couverture
# ---------------------------------------------------------------------------

def gauge_score(score_pct: float, titre: str = "Score de couverture") -> go.Figure:
    theme = _theme_colors()
    dark = _is_dark_theme()
    if score_pct >= 85:
        couleur_barre = COULEUR_VERT
    elif score_pct >= 70:
        couleur_barre = COULEUR_ORANGE
    else:
        couleur_barre = COULEUR_ROUGE

    # Zones de fond du gauge : plus sombres en thème dark, claires en light
    if dark:
        zone_rouge = "rgba(239, 68, 68, 0.18)"
        zone_orange = "rgba(245, 158, 11, 0.18)"
        zone_verte = "rgba(16, 185, 129, 0.18)"
        bg_gauge = "rgba(255,255,255,0.04)"
        border_gauge = "rgba(255,255,255,0.15)"
    else:
        zone_rouge = "#fef2f2"
        zone_orange = "#fffbeb"
        zone_verte = "#f0fdf4"
        bg_gauge = "white"
        border_gauge = "#e5e7eb"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score_pct,
            domain={"x": [0, 1], "y": [0, 1]},
            number={
                "suffix": " %",
                "font": {"size": 36, "color": theme["annotation_centre"]},
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": theme["text_secondaire"],
                    "tickfont": {"color": theme["text"]},
                },
                "bar": {"color": couleur_barre, "thickness": 0.8},
                "bgcolor": bg_gauge,
                "borderwidth": 1,
                "bordercolor": border_gauge,
                "steps": [
                    {"range": [0, 70], "color": zone_rouge},
                    {"range": [70, 85], "color": zone_orange},
                    {"range": [85, 100], "color": zone_verte},
                ],
                "threshold": {
                    "line": {"color": theme["annotation_centre"], "width": 3},
                    "thickness": 0.7,
                    "value": score_pct,
                },
            },
            title={"text": titre, "font": {"size": 14, "color": theme["text"]}},
        )
    )
    fig.update_layout(**_layout_base(), height=280)
    return fig


# ---------------------------------------------------------------------------
# Bar comparatif — métriques entre affaires
# ---------------------------------------------------------------------------

def bar_comparatif(
    labels_affaires: list[str],
    metriques: dict[str, list[float]],
) -> go.Figure:
    """metriques : { "Exigences": [12, 9], "Couverture %": [95, 91], ... }"""
    theme = _theme_colors()
    fig = go.Figure()
    couleurs = PALETTE_CATEGORIES
    for i, (nom, valeurs) in enumerate(metriques.items()):
        fig.add_trace(
            go.Bar(
                name=nom,
                x=labels_affaires,
                y=valeurs,
                marker=dict(color=couleurs[i % len(couleurs)]),
                text=[f"{v:.0f}" for v in valeurs],
                textposition="outside",
                textfont=dict(color=theme["text"]),
                hovertemplate=f"<b>{nom}</b><br>%{{x}}<br>%{{y}}<extra></extra>",
            )
        )
    fig.update_layout(
        **_layout_base(),
        height=320,
        barmode="group",
        xaxis=dict(title=None, color=theme["text"]),
        yaxis=dict(showgrid=True, gridcolor=theme["grid"], title=None, color=theme["text"]),
        legend=dict(
            orientation="h",
            y=-0.15,
            x=0.5,
            xanchor="center",
            font=dict(color=theme["text"]),
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Scatter 3D — exigences dans l'espace catégorie × importance × rang
# ---------------------------------------------------------------------------

def scatter3d_exigences(exigences: list) -> go.Figure:
    """Nuage de points 3D WebGL : chaque exigence est un point dans l'espace
    catégorie (X) × importance (Y) × rang (Z). Interactif — rotatable à la souris.
    """
    if not exigences:
        return go.Figure()

    importance_map = {"bloquant": 3, "important": 2, "mineur": 1}
    categories = sorted({e.categorie for e in exigences})
    cat_map = {c: i for i, c in enumerate(categories)}

    couleurs_imp = {"bloquant": "#ef4444", "important": "#f59e0b", "mineur": "#38bdf8"}
    taille_imp   = {"bloquant": 10,        "important": 7,         "mineur": 5}

    rang_counter: dict = {}
    xs, ys, zs, colors, sizes, texts = [], [], [], [], [], []

    for e in exigences:
        key = (e.categorie, e.importance)
        rang_counter[key] = rang_counter.get(key, 0) + 1
        xs.append(cat_map[e.categorie] + (rang_counter[key] % 3) * 0.25)
        ys.append(importance_map.get(e.importance, 1) + (rang_counter[key] // 3) * 0.15)
        zs.append(rang_counter[key])
        colors.append(couleurs_imp.get(e.importance, "#38bdf8"))
        sizes.append(taille_imp.get(e.importance, 6))
        texts.append(
            f"<b>{e.libelle[:60]}</b><br>"
            f"Catégorie : {e.categorie}<br>"
            f"Importance : {e.importance}<br>"
            f"Source : {e.source_piece}"
        )

    fig = go.Figure(
        go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="markers",
            marker=dict(size=sizes, color=colors, opacity=0.85, line=dict(width=0)),
            text=texts,
            hovertemplate="%{text}<extra></extra>",
        )
    )

    # axis_style sans titlefont (déprécié) — on passe title comme string
    def _axis3d(title_text, **extra):
        return dict(
            backgroundcolor="rgba(3,13,31,0.8)",
            gridcolor="rgba(56,189,248,0.15)",
            showbackground=True,
            tickfont=dict(color="#94a3b8", size=9),
            zerolinecolor="rgba(56,189,248,0.2)",
            title=title_text,
            **extra,
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=500,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(color="#e2e8f0", size=11),
        scene=dict(
            xaxis=_axis3d(
                "Catégorie",
                tickvals=list(cat_map.values()),
                ticktext=[c.replace("-", "‑") for c in categories],
            ),
            yaxis=_axis3d(
                "Importance",
                tickvals=[1, 2, 3],
                ticktext=["Mineur", "Important", "Bloquant"],
            ),
            zaxis=_axis3d("Rang"),
            bgcolor="rgba(3,13,31,0.6)",
            camera=dict(eye=dict(x=1.6, y=-1.6, z=1.2)),
        ),
        legend=dict(font=dict(color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# ---------------------------------------------------------------------------
# Surface 3D — DQE par chapitre (paysage financier)
# ---------------------------------------------------------------------------

def surface3d_dqe(dqe_lignes: list) -> go.Figure:
    """Surface 3D WebGL : chaque chapitre DQE = une montagne gaussienne
    dont la hauteur est proportionnelle au montant HT.
    """
    if not dqe_lignes:
        return go.Figure()

    par_cat: dict[str, float] = {}
    for ligne in dqe_lignes:
        par_cat[ligne.categorie] = par_cat.get(ligne.categorie, 0.0) + ligne.montant

    items = sorted(par_cat.items(), key=lambda x: x[1], reverse=True)
    labels = [c for c, _ in items]
    valeurs = [v for _, v in items]
    n = len(labels)

    # Grille Z : superposition de gaussiennes
    grid_size = 50
    Z = [[0.0] * grid_size for _ in range(grid_size)]
    sigma = max(grid_size / (n * 1.8), 3.0)
    for i, (_, val) in enumerate(zip(labels, valeurs)):
        cx = (i + 0.5) / n * grid_size
        cy = grid_size / 2
        for row in range(grid_size):
            for col in range(grid_size):
                d2 = (col - cx) ** 2 / sigma ** 2 + (row - cy) ** 2 / (sigma * 1.5) ** 2
                Z[row][col] += val * math.exp(-d2)

    colorscale = [
        [0.0,  "#030d1f"],
        [0.3,  "#0c2247"],
        [0.6,  "#0ea5e9"],
        [0.85, "#38bdf8"],
        [1.0,  "#f0f9ff"],
    ]

    fig = go.Figure(
        go.Surface(
            z=Z,
            colorscale=colorscale,
            showscale=False,
            opacity=0.90,
            contours=dict(z=dict(show=True, usecolormap=True, project=dict(z=True))),
            hovertemplate="Montant relatif : %{z:.0f}<extra></extra>",
        )
    )

    def _axis3d_s(title_text, **extra):
        return dict(
            backgroundcolor="rgba(3,13,31,0.8)",
            gridcolor="rgba(56,189,248,0.12)",
            showbackground=True,
            tickfont=dict(color="#94a3b8", size=9),
            zerolinecolor="rgba(56,189,248,0.2)",
            title=title_text,
            **extra,
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=460,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(color="#e2e8f0", size=11),
        scene=dict(
            xaxis=_axis3d_s("Chapitres →", showticklabels=False),
            yaxis=_axis3d_s("", showticklabels=False),
            zaxis=_axis3d_s("Montant HT (€)"),
            bgcolor="rgba(3,13,31,0.6)",
            camera=dict(eye=dict(x=1.8, y=-1.8, z=1.4)),
        ),
    )
    return fig
