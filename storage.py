"""Persistência: SQLite por padrão; Postgres (Neon, Supabase…) se DATABASE_URL apontar para ele.

Guarda a carteira do usuário e um cache de cotações compartilhado (poupa a cota das APIs).
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from functools import lru_cache

import pandas as pd

from config import cfg
from core.carteira import COLUNAS, limpar

_DDL = (
    "CREATE TABLE IF NOT EXISTS posicoes (ticker TEXT PRIMARY KEY, tipo TEXT NOT NULL, "
    "quantidade DOUBLE PRECISION NOT NULL, preco_medio DOUBLE PRECISION NOT NULL)",
    "CREATE TABLE IF NOT EXISTS cotacoes (ticker TEXT PRIMARY KEY, payload TEXT NOT NULL, "
    "atualizado_em DOUBLE PRECISION NOT NULL)",
)


class Store:
    def __init__(self, url: str = "sqlite:///data/app.db"):
        self.pg = url.startswith(("postgres://", "postgresql://"))
        self.url = url
        if not self.pg:
            self.path = url.removeprefix("sqlite:///")
            if os.path.dirname(self.path):
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with self._conn() as con:
            for ddl in _DDL:
                self._run(con, ddl)

    @contextmanager
    def _conn(self):
        if self.pg:
            import psycopg  # instalado via requirements (psycopg[binary])

            con = psycopg.connect(self.url)
        else:
            con = sqlite3.connect(self.path)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _run(self, con, sql: str, params: tuple = ()):
        cur = con.cursor()
        cur.execute(sql.replace("?", "%s") if self.pg else sql, params)
        return cur

    # --- carteira -----------------------------------------------------------
    def load_posicoes(self) -> pd.DataFrame:
        with self._conn() as con:
            rows = self._run(con, "SELECT ticker, tipo, quantidade, preco_medio FROM posicoes ORDER BY ticker").fetchall()
        return pd.DataFrame(rows, columns=COLUNAS)

    def save_posicoes(self, df: pd.DataFrame) -> None:
        limpo = limpar(df)
        dados = [tuple(r) for r in limpo.itertuples(index=False, name=None)]
        with self._conn() as con:
            self._run(con, "DELETE FROM posicoes")
            for linha in dados:
                self._run(con, "INSERT INTO posicoes VALUES (?, ?, ?, ?)", linha)

    # --- cache de cotações --------------------------------------------------
    def cache_fresh(self, ttl: float) -> dict[str, dict]:
        with self._conn() as con:
            rows = self._run(con, "SELECT ticker, payload FROM cotacoes WHERE atualizado_em > ?", (time.time() - ttl,)).fetchall()
        return {t: json.loads(p) for t, p in rows}

    def cache_put(self, ticker: str, payload: dict) -> None:
        with self._conn() as con:
            self._run(con, "DELETE FROM cotacoes WHERE ticker = ?", (ticker,))
            self._run(con, "INSERT INTO cotacoes VALUES (?, ?, ?)", (ticker, json.dumps(payload), time.time()))


@lru_cache(maxsize=1)
def get_store() -> Store:
    return Store(cfg("DATABASE_URL") or "sqlite:///data/app.db")
