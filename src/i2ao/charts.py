"""Graphiques Plotly réutilisables — palette cohérente avec les exports DOCX/XLSX.

Charts adaptatifs au thème Streamlit (light / dark) :
- Backgrounds transparents pour s'intégrer au fond Streamlit
- Couleurs de texte et grilles ajustées selon le thème
"""

from __future__ import annotations

from collections import Counter

import plotly.graph_objects as go

# Palette projet (alignée DOCX/XLSX/CSS)
COULEUR_PRIMAIRE = "#1a3d6e"
COULEUR_PRIMAIRE_CLAIR = "#8baed6"  # version pour fond sombre
COULEUR_SECONDAIRE = "#5b85b8"
COULEUR_VERT = "#10b981"            # vert plus vif (visible light + dark)
COULEUR_ORANGE = "#f59e0b"          # orange plus vif
COULEUR_ROUGE = "#ef4444"           # rouge plus vif
COULEUR_GRIS = "#9ca3af"

# Palette catégories — couleurs vives lisibles sur fond clair ET sombre
PALETTE_CATEGORIES = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#06b6d4",
    "#ec4899",
    "#84cc16",
    "#f97316",
    "#6366f1",
    "#14b8a6",
]


def _is_dark_theme() -> bool:
    """Détecte si Streamlit est en thème sombre (avec fallback gracieux)."""
    try:
        import streamlit as st

        # Streamlit 1.40+ : runtime theme
        if hasattr(st, "context") and hasattr(st.context, "theme"):
            theme_type = getattr(st.context.theme, "type", None)
            if theme_type:
                return theme_type == "dark"
        # Fallback config
        base = st.get_option("theme.base")
        if base:
            return base == "dark"
    except Exception:
        pass
    return False


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
