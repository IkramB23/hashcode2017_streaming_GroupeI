# recherche locale (hill climbing) pour le hash code 2017
#
# idee (donnee présente dans le sujet):
# on part d'une solution qui est deja construite (par un glouton par exemple)
# on essaie des petites modifications aleatoires
# on garde uniquement celles qui ameliorent strictement le score
#
# la solution est stockee comme une matrice booleenne (C, V) pour que
# le FastScorer NUMPY puisse evaluer chaque mouvement rapidement
#
# mouvements consideres, tous cites dans le sujet:
# - add    : ajouter une video a un cache (si ca rentre)
# - remove : retirer une video d'un cache
# - swap   : remplacer une video du cache par une autre pas dedans
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from .parser import Instance
from .scorer import FastScorer, CacheContents


@dataclass
class HCResult:
    # petit conteneur avec le resultat + des stats pour l'affichage
    solution: CacheContents
    best_score: int
    initial_score: int
    iterations: int
    improvements: int
    # historique (temps, meilleur score) pour tracer une courbe si on veut
    history: List[Tuple[float, int]] = field(default_factory=list)


def hill_climbing(
    instance: Instance,
    initial: CacheContents,
    time_limit: float = 10.0,
    seed: int = 42,
    verbose: bool = True,
    scorer: FastScorer | None = None,
) -> HCResult:
    # boucle principale: tourne pendant time_limit secondes
    # renvoie la meilleure solution rencontree
    rng = random.Random(seed)
    scorer = scorer or FastScorer(instance)

    # etat courant en matrice booleenne pour aller vite
    matrix = scorer.contents_to_matrix(initial)
    sizes = np.array(instance.video_sizes, dtype=np.int64)
    # capacite utilisee par cache (MB)
    used = (matrix * sizes).sum(axis=1)

    current_score = scorer.score_matrix(matrix)
    initial_score = current_score
    best_score = current_score
    best_matrix = matrix.copy()

    history: List[Tuple[float, int]] = [(0.0, current_score)]
    iterations = 0
    improvements = 0

    start = time.time()
    while time.time() - start < time_limit:
        iterations += 1
        # on tire un cache et une video au hasard
        c = rng.randrange(instance.C)
        v = rng.randrange(instance.V)
        s = int(sizes[v])
        capacity_left = instance.X - int(used[c])

        if matrix[c, v]:
            # cas 1: la video est deja dans le cache -> on tente de la retirer
            matrix[c, v] = False
            new_score = scorer.score_matrix(matrix)
            if new_score > current_score:
                # amelioration acceptee
                current_score = new_score
                used[c] -= s
                if new_score > best_score:
                    best_score = new_score
                    best_matrix = matrix.copy()
                    improvements += 1
                    history.append((time.time() - start, best_score))
            else:
                # on annule le mouvement
                matrix[c, v] = True
            continue

        if capacity_left >= s:
            # cas 2: la video n'est pas dedans et ca rentre -> add
            matrix[c, v] = True
            new_score = scorer.score_matrix(matrix)
            if new_score > current_score:
                current_score = new_score
                used[c] += s
                if new_score > best_score:
                    best_score = new_score
                    best_matrix = matrix.copy()
                    improvements += 1
                    history.append((time.time() - start, best_score))
            else:
                matrix[c, v] = False
        else:
            # cas 3: ca ne rentre pas -> swap
            # on cherche une video dans le cache assez grosse pour laisser la place
            in_cache = np.flatnonzero(matrix[c])
            if in_cache.size == 0:
                continue
            need_to_free = s - capacity_left
            candidates = in_cache[sizes[in_cache] >= need_to_free]
            if candidates.size == 0:
                continue
            victim = int(rng.choice(candidates.tolist()))
            v_size = int(sizes[victim])
            # on effectue le swap
            matrix[c, victim] = False
            matrix[c, v] = True
            new_score = scorer.score_matrix(matrix)
            if new_score > current_score:
                current_score = new_score
                used[c] += s - v_size
                if new_score > best_score:
                    best_score = new_score
                    best_matrix = matrix.copy()
                    improvements += 1
                    history.append((time.time() - start, best_score))
            else:
                # rollback
                matrix[c, victim] = True
                matrix[c, v] = False

    if verbose:
        print(
            f"[hill_climbing] iters={iterations} improvements={improvements} "
            f"initial={initial_score} best={best_score}"
        )

    return HCResult(
        solution=scorer.matrix_to_contents(best_matrix),
        best_score=best_score,
        initial_score=initial_score,
        iterations=iterations,
        improvements=improvements,
        history=history,
    )
