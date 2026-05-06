"""Base SQLite locale : affaires, pièces DCE, exigences extraites, livrables générés."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS affaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_operation TEXT NOT NULL,
    pouvoir_adjudicateur TEXT,
    date_remise TEXT,
    type_marche TEXT,
    materiau_dominant TEXT,
    montant_estime REAL,
    statut TEXT DEFAULT 'en-cours',
    cree_le TEXT DEFAULT (datetime('now')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS pieces_dce (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    affaire_id INTEGER NOT NULL,
    type_piece TEXT,
    nom_fichier TEXT,
    chemin_fichier TEXT,
    texte_brut TEXT,
    nb_pages INTEGER,
    cree_le TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (affaire_id) REFERENCES affaires(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exigences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    affaire_id INTEGER NOT NULL,
    categorie TEXT,
    libelle TEXT NOT NULL,
    detail TEXT,
    source_piece TEXT,
    importance TEXT,
    statut TEXT DEFAULT 'a-traiter',
    cree_le TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (affaire_id) REFERENCES affaires(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memoires_generes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    affaire_id INTEGER NOT NULL,
    chemin_docx TEXT,
    contenu_markdown TEXT,
    cree_le TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (affaire_id) REFERENCES affaires(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dpgf_generees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    affaire_id INTEGER NOT NULL,
    chemin_xlsx TEXT,
    montant_total REAL,
    cree_le TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (affaire_id) REFERENCES affaires(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pieces_affaire ON pieces_dce(affaire_id);
CREATE INDEX IF NOT EXISTS idx_exigences_affaire ON exigences(affaire_id);
"""


def _connect(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)


def list_affaires() -> list[sqlite3.Row]:
    with connection() as conn:
        return list(
            conn.execute(
                "SELECT * FROM affaires ORDER BY datetime(cree_le) DESC"
            )
        )


def get_affaire(affaire_id: int) -> sqlite3.Row | None:
    with connection() as conn:
        return conn.execute(
            "SELECT * FROM affaires WHERE id = ?", (affaire_id,)
        ).fetchone()


def create_affaire(nom_operation: str, **fields) -> int:
    cols = ["nom_operation"] + list(fields.keys())
    placeholders = ", ".join("?" for _ in cols)
    values = [nom_operation] + list(fields.values())
    with connection() as conn:
        cur = conn.execute(
            f"INSERT INTO affaires ({', '.join(cols)}) VALUES ({placeholders})",
            values,
        )
        return int(cur.lastrowid or 0)


def update_affaire(affaire_id: int, **fields) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [affaire_id]
    with connection() as conn:
        conn.execute(
            f"UPDATE affaires SET {assignments} WHERE id = ?", values
        )


def add_piece_dce(
    affaire_id: int,
    type_piece: str,
    nom_fichier: str,
    chemin_fichier: str,
    texte_brut: str,
    nb_pages: int,
) -> int:
    with connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO pieces_dce
                (affaire_id, type_piece, nom_fichier, chemin_fichier, texte_brut, nb_pages)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (affaire_id, type_piece, nom_fichier, chemin_fichier, texte_brut, nb_pages),
        )
        return int(cur.lastrowid or 0)


def list_pieces(affaire_id: int) -> list[sqlite3.Row]:
    with connection() as conn:
        return list(
            conn.execute(
                "SELECT * FROM pieces_dce WHERE affaire_id = ? ORDER BY id",
                (affaire_id,),
            )
        )


def add_exigences(affaire_id: int, exigences: list[dict]) -> int:
    if not exigences:
        return 0
    with connection() as conn:
        conn.executemany(
            """
            INSERT INTO exigences
                (affaire_id, categorie, libelle, detail, source_piece, importance)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    affaire_id,
                    e.get("categorie"),
                    e["libelle"],
                    e.get("detail"),
                    e.get("source_piece"),
                    e.get("importance"),
                )
                for e in exigences
            ],
        )
        return len(exigences)


def list_exigences(affaire_id: int) -> list[sqlite3.Row]:
    with connection() as conn:
        return list(
            conn.execute(
                "SELECT * FROM exigences WHERE affaire_id = ? ORDER BY id",
                (affaire_id,),
            )
        )


def clear_exigences(affaire_id: int) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM exigences WHERE affaire_id = ?", (affaire_id,))


def save_memoire(affaire_id: int, chemin_docx: str, contenu_markdown: str) -> int:
    with connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO memoires_generes (affaire_id, chemin_docx, contenu_markdown)
            VALUES (?, ?, ?)
            """,
            (affaire_id, chemin_docx, contenu_markdown),
        )
        return int(cur.lastrowid or 0)


def save_dpgf(affaire_id: int, chemin_xlsx: str, montant_total: float) -> int:
    with connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO dpgf_generees (affaire_id, chemin_xlsx, montant_total)
            VALUES (?, ?, ?)
            """,
            (affaire_id, chemin_xlsx, montant_total),
        )
        return int(cur.lastrowid or 0)
