"""
Item-item kNN (Pearson) — движок рекомендаций.

Перенос референс-реализации из item_item_knn_handoff.md (ROC-AUC 0.7673
на временном сплите MovieLens latest-small). Критичные детали, зафиксированные
экспериментально:
  * соседи фильма ищутся ТОЛЬКО среди фильмов, оценённых целевым юзером;
  * похожесть — cosine по центрированным векторах (= корреляция Пирсона);
  * скор возвращает уровень юзера: mean_u + Σ w·(r − mean_u) / Σ|w|;
  * K = 40, минимальная история юзера — 2 оценки;
  * веса соседей могут быть отрицательными — это нормально.

В отличие от референса, скоринг топ-N векторизован одним вызовом kneighbors
по пакету кандидатов — математика идентична предсказанию по одной паре.
"""

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.neighbors import NearestNeighbors

K = 40              # число соседей (больше — шум, меньше — недобор сигнала)
MIN_HISTORY = 2     # минимальная история юзера, иначе — холодный старт
POPULAR_PRIOR = 5.0 # байесовская поправка популярного фолбэка


class ItemItemKNN:
    """Модель обучается на ВСЕХ оценках (сервинг, без сплита)."""

    def __init__(self, ratings: pd.DataFrame):
        """
        ratings: DataFrame с колонками user_id, series_id, rating.
        rating — целая шкала приложения (1..10), внутри сохраняется как есть;
        порядок рекомендаций от масштаба не зависит.
        """
        if ratings.empty:
            raise ValueError("Нет оценок для обучения модели")

        users = np.sort(ratings["user_id"].unique())
        items = np.sort(ratings["series_id"].unique())
        self._user_codes = {u: i for i, u in enumerate(users)}
        self._series_codes = {m: i for i, m in enumerate(items)}
        self._code_to_series = {i: m for m, i in self._series_codes.items()}

        u = ratings["user_id"].map(self._user_codes).to_numpy()
        m = ratings["series_id"].map(self._series_codes).to_numpy()
        r = ratings["rating"].to_numpy(dtype=float)
        nu, nm = len(users), len(items)

        self.u_mean = ratings.assign(_u=u).groupby("_u")["rating"] \
            .mean().reindex(range(nu)).to_numpy()
        self.G = float(ratings["rating"].mean())

        self.R_raw = sparse.csr_matrix((r, (u, m)), shape=(nu, nm))
        self.R_cen = sparse.csr_matrix(
            (r - self.u_mean[u], (u, m)), shape=(nu, nm))
        self.RT_cen = self.R_cen.T.tocsr()  # строки = фильмы

        # Свой NearestNeighbors на юзера: соседи ищутся только по его пулу
        self.nns: dict[int, NearestNeighbors] = {}
        self.pools: dict[int, np.ndarray] = {}
        for uc in range(nu):
            rated_items = self.R_raw[uc].indices
            if len(rated_items) >= MIN_HISTORY:
                self.nns[uc] = NearestNeighbors(
                    n_neighbors=min(K, len(rated_items)), metric="cosine"
                ).fit(self.RT_cen[rated_items])
                self.pools[uc] = rated_items

        # Популярное (байесовское среднее) — фолбэк для холодных юзеров
        item_sum = np.asarray(self.R_raw.sum(axis=0)).ravel()
        item_cnt = np.bincount(self.R_raw.indices, minlength=nm)
        bayes = (item_sum + POPULAR_PRIOR * self.G) / (item_cnt + POPULAR_PRIOR)
        self._popular_codes = np.argsort(-bayes)

    # ── Скоринг ────────────────────────────────────────────────────────────

    def predict(self, user_id: int, series_id: int) -> float:
        """Скор одной пары (юзер БД, фильм БД). Чем выше, тем вероятнее позитив."""
        uc = self._user_codes.get(user_id)
        mc = self._series_codes.get(series_id)
        if uc is None or mc is None:
            return self.G
        return self._predict_codes(uc, np.array([mc]))[0]

    def _predict_codes(self, uc: int, m_candidates: np.ndarray) -> np.ndarray:
        """Скор пакета фильмов для юзера. Только юзеры с историей ≥ MIN_HISTORY."""
        if uc not in self.nns:
            return np.full(len(m_candidates), self.G)

        scorable = self.RT_cen[m_candidates].getnnz(axis=1) > 0
        scores = np.full(len(m_candidates), self.u_mean[uc])

        if scorable.any():
            D, idx = self.nns[uc].kneighbors(self.RT_cen[m_candidates[scorable]])
            w = 1.0 - D                                   # cos близость
            items = self.pools[uc][idx]                   # (nq, K)
            r = self.R_raw[uc].toarray().ravel()[items]   # оценки юзера по соседям
            mean_u = self.u_mean[uc]
            denom = np.abs(w).sum(axis=1) + 1e-9
            pred = mean_u + (w * (r - mean_u)).sum(axis=1) / denom
            pred[denom < 1e-9 + 1e-9] = mean_u  # строки с нулевой суммой весов
            scores[scorable] = pred
        return scores

    def recommend(self, user_id: int, n: int = 10) -> list[int]:
        """Топ-N series_id для юзера. Холодный юзер/фильм — популярное."""
        uc = self._user_codes.get(user_id)

        if uc is None or uc not in self.nns:
            return [self._code_to_series[c] for c in self._popular_codes[:n]]

        rated = set(self.R_raw[uc].indices)
        candidates = np.array(
            [c for c in range(self.R_raw.shape[1]) if c not in rated])
        if len(candidates) == 0:
            return []

        scores = self._predict_codes(uc, candidates)
        top = candidates[np.argsort(-scores)[:n]]
        return [self._code_to_series[c] for c in top]
