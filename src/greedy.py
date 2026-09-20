# algorithmes gloutons pour le hash code 2017 "streaming videos"
#
# principe general (donne dans le sujet):
# a chaque etape on fait le choix qui parait le meilleur maintenant
# c'est rapide, mais pas garanti optimal
#
# on implemente 3 variantes pour pouvoir les comparer:
# - greedy_gain : trie les couples (video, cache) par densite de gain
# - greedy_requests : trie les requetes par nombre decroissant
# - greedy_regret : trie par "regret" (voir plus bas)
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from .parser import Instance


CacheContents = Dict[int, Set[int]]


# ---------------------------------------------------------------------------
def _empty_solution(instance: Instance) -> CacheContents:
    # solution de depart: tous les caches sont vides
    return {c: set() for c in range(instance.C)}


# ---------------------------------------------------------------------------
def greedy_by_gain_density(instance: Instance) -> CacheContents:
    # pour chaque paire (video v, cache c) on calcule le gain total possible
    # gain(v, c) = somme sur les requetes (v, e, n) telles que c est connecte a e
    #              de n * (L_D(e) - L(e, c))
    # ensuite on trie par gain / taille(v) decroissant et on remplit
    # gain / taille = densite du gain, ca prefere les petites videos rentables
    gain: Dict[Tuple[int, int], int] = defaultdict(int)
    for req in instance.requests:
        ep = instance.endpoints[req.endpoint]
        L_D = ep.latency_dc
        for c, L_c in ep.caches.items():
            g = req.count * (L_D - L_c)
            if g > 0:
                gain[(req.video, c)] += g

    # on prepare une liste (densite, gain, v, c, taille) puis on la trie
    candidates: List[Tuple[float, int, int, int, int]] = []
    for (v, c), g in gain.items():
        s = instance.video_sizes[v]
        if s <= 0:
            continue
        candidates.append((g / s, g, v, c, s))
    # tri par densite decroissante, en cas d'egalite on prend le gain le plus gros
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)

    # remplissage classique de type sac a dos
    solution = _empty_solution(instance)
    remaining = {c: instance.X for c in range(instance.C)}

    for _density, _g, v, c, s in candidates:
        # deja place ? on saute
        if v in solution[c]:
            continue
        # ca rentre ? on ajoute
        if remaining[c] >= s:
            solution[c].add(v)
            remaining[c] -= s

    return solution


# ---------------------------------------------------------------------------
def greedy_by_requests(instance: Instance) -> CacheContents:
    # variante suggeree dans le sujet:
    # on trie les requetes par nombre décroissant
    # pour chaque requete on tente de placer la video dans le cache le plus proche
    solution = _empty_solution(instance)
    remaining = {c: instance.X for c in range(instance.C)}

    sorted_reqs = sorted(instance.requests, key=lambda r: r.count, reverse=True)

    for req in sorted_reqs:
        v = req.video
        s = instance.video_sizes[v]
        ep = instance.endpoints[req.endpoint]
        # on essaie les caches connectes du plus proche au plus loin
        for c, _L_c in sorted(ep.caches.items(), key=lambda kv: kv[1]):
            if v in solution[c]:
                # deja dispo sur un cache au moins aussi bon, pas besoin de refaire
                break
            if remaining[c] >= s:
                solution[c].add(v)
                remaining[c] -= s
                break
    return solution


# ---------------------------------------------------------------------------
def greedy_by_regret(instance: Instance) -> CacheContents:
    # variante "regret" cite dans le sujet:
    # regret = ecart entre les deux plus petites latences accessibles
    # multiplie par le nombre de requetes concernees
    # un gros regret = rater le meilleur cache coute cher, donc on le traite en premier

    # d'abord on agrege les requetes par (video, endpoint)
    agg: Dict[Tuple[int, int], int] = defaultdict(int)
    for req in instance.requests:
        agg[(req.video, req.endpoint)] += req.count

    # calcul du regret pour chaque paire agrégée
    scored: List[Tuple[int, int, int, int]] = []
    for (v, e), n in agg.items():
        ep = instance.endpoints[e]
        L_D = ep.latency_dc
        # on inclut L_D pour gerer les endpoints avec peu de caches
        latencies = sorted(list(ep.caches.values()) + [L_D])
        best = latencies[0]
        second = latencies[1] if len(latencies) > 1 else L_D
        regret = (second - best) * n
        scored.append((regret, n, v, e))

    # tri par regret decroissant, avec nb de requetes comme cle secondaire
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)

    # meme boucle de placement que greedy_by_requests
    solution = _empty_solution(instance)
    remaining = {c: instance.X for c in range(instance.C)}

    for _regret, _n, v, e in scored:
        s = instance.video_sizes[v]
        ep = instance.endpoints[e]
        for c, _L_c in sorted(ep.caches.items(), key=lambda kv: kv[1]):
            if v in solution[c]:
                break
            if remaining[c] >= s:
                solution[c].add(v)
                remaining[c] -= s
                break
    return solution


# ---------------------------------------------------------------------------
# dictionnaire utilise par le CLI pour choisir un algo par son nom
GREEDY_ALGOS = {
    "greedy_gain": greedy_by_gain_density,
    "greedy_requests": greedy_by_requests,
    "greedy_regret": greedy_by_regret,
}
