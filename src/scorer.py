# calcul du score officiel du hash code 2017
#
# formule imposee par le sujet:
#     score = floor( 1000 * somme_R Rn * (L_D - L) / somme_R Rn )
# le score est donne en microsecondes (les latences sont en ms)
#
# on a deux implementations:
# - compute_score: version lente et lisible, sert de reference
# - FastScorer:    version vectorisee avec numpy, pour les grosses instances
from __future__ import annotations

from typing import Dict, Set

import numpy as np

from .parser import Instance


CacheContents = Dict[int, Set[int]]


# ---------------------------------------------------------------------------
# version de reference: simple et lente mais on peut lui faire confiance
# ---------------------------------------------------------------------------
def compute_score(instance: Instance, cache_contents: CacheContents) -> int:
    # pour chaque requete on calcule la meilleure latence disponible
    # puis on somme le temps sauve et on divise par le total des requetes
    total_saved = 0
    total_requests = 0
    for req in instance.requests:
        ep = instance.endpoints[req.endpoint]
        L_D = ep.latency_dc
        # par defaut on sert la video depuis le data center
        best_L = L_D
        # si un cache connecte contient la video, on peut faire mieux
        for c, L_c in ep.caches.items():
            if L_c < best_L and req.video in cache_contents.get(c, ()):
                best_L = L_c
        total_saved += req.count * (L_D - best_L)
        total_requests += req.count
    if total_requests == 0:
        return 0
    # division entiere = le floor demande par le sujet
    return (total_saved * 1000) // total_requests


# ---------------------------------------------------------------------------
# verification que la solution respecte les contraintes du sujet
# ---------------------------------------------------------------------------
def validate_solution(instance: Instance, cache_contents: CacheContents) -> None:
    # leve une ValueError si une contrainte est violee
    for c, videos in cache_contents.items():
        if c < 0 or c >= instance.C:
            raise ValueError(f"cache id {c} out of range [0,{instance.C})")
        used = 0
        for v in videos:
            if v < 0 or v >= instance.V:
                raise ValueError(f"video id {v} out of range [0,{instance.V})")
            used += instance.video_sizes[v]
        if used > instance.X:
            raise ValueError(
                f"cache {c} overflows: uses {used} MB > capacity {instance.X} MB"
            )


# ---------------------------------------------------------------------------
# version rapide (numpy) pour la recherche locale
# ---------------------------------------------------------------------------
class FastScorer:
    # on precalcule des tableaux numpy une seule fois a la creation
    # ensuite chaque appel a score_matrix est tres rapide

    # constante utilisee comme "infini" pour l'operation de min
    HUGE = np.int64(10**12)

    def __init__(self, instance: Instance):
        self.instance = instance
        R = instance.R

        # on convertit les requetes en tableaux numpy
        req_v = np.empty(R, dtype=np.int32)
        req_e = np.empty(R, dtype=np.int32)
        req_n = np.empty(R, dtype=np.int64)
        for i, r in enumerate(instance.requests):
            req_v[i] = r.video
            req_e[i] = r.endpoint
            req_n[i] = r.count

        # latence data-center par endpoint puis par requete
        L_D_e = np.array(
            [ep.latency_dc for ep in instance.endpoints], dtype=np.int64
        )
        L_D_r = L_D_e[req_e]

        # on aplatit toutes les paires (requete, cache connecte a son endpoint)
        # ca permettra de faire l'operation "min" en une seule passe numpy
        flat_ridx: list[int] = []
        flat_c: list[int] = []
        flat_L: list[int] = []
        for i, r in enumerate(instance.requests):
            ep = instance.endpoints[r.endpoint]
            for c, L_c in ep.caches.items():
                flat_ridx.append(i)
                flat_c.append(c)
                flat_L.append(L_c)

        self.req_v = req_v
        self.req_n = req_n
        self.L_D_r = L_D_r
        self.total_n = int(req_n.sum())
        self.flat_ridx = np.array(flat_ridx, dtype=np.int64)
        self.flat_c = np.array(flat_c, dtype=np.int64)
        self.flat_L = np.array(flat_L, dtype=np.int64)
        # pour chaque paire on connait aussi la video demandee
        self.flat_v = req_v[self.flat_ridx].astype(np.int64)

    # ------------------------------------------------------------------
    def contents_to_matrix(self, cache_contents: CacheContents) -> np.ndarray:
        # conversion dict -> matrice booleenne (C, V) utilisee par le HC
        M = np.zeros((self.instance.C, self.instance.V), dtype=bool)
        for c, videos in cache_contents.items():
            for v in videos:
                M[c, v] = True
        return M

    def matrix_to_contents(self, M: np.ndarray) -> CacheContents:
        # conversion inverse: matrice -> dict pour ecrire le .out
        out: CacheContents = {}
        for c in range(self.instance.C):
            vids = np.flatnonzero(M[c])
            if vids.size:
                out[c] = {int(v) for v in vids}
        return out

    # ------------------------------------------------------------------
    def score_matrix(self, contents_matrix: np.ndarray) -> int:
        # coeur du scorer rapide, tout se fait en numpy
        # 1) pour chaque paire (requete, cache), la video est-elle dedans ?
        contains = contents_matrix[self.flat_c, self.flat_v]
        # 2) si oui on prend la latence du cache, sinon on prend l'infini
        eff_L = np.where(contains, self.flat_L, self.HUGE)

        # 3) pour chaque requete, on prend le min sur toutes ses paires
        best_L = np.full(self.instance.R, self.HUGE, dtype=np.int64)
        np.minimum.at(best_L, self.flat_ridx, eff_L)

        # 4) fallback: si aucun cache utile, on retombe sur L_D
        best_L = np.minimum(best_L, self.L_D_r)

        # 5) meme formule que le sujet
        saved = (self.req_n * (self.L_D_r - best_L)).sum()
        if self.total_n == 0:
            return 0
        return int((int(saved) * 1000) // self.total_n)

    def score(self, cache_contents: CacheContents) -> int:
        # variante pratique quand on a un dict et pas une matrice
        return self.score_matrix(self.contents_to_matrix(cache_contents))
