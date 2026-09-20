# lecture / ecriture des fichiers de soumission (.out)
# format impose par hash code 2017:
#   1ere ligne: N = nombre de caches decrits
#   puis N lignes: "c v0 v1 v2 ..." = cache c contient ces videos
from __future__ import annotations

from pathlib import Path
from typing import Dict, Set


# type alias pour rendre le code plus lisible
# on represente une solution comme un dict: id_cache -> set des videos dedans
CacheContents = Dict[int, Set[int]]


def write_solution(path: str | Path, cache_contents: CacheContents) -> None:
    # ecrit une solution au format demande
    # les caches vides ne sont pas ecrits (le sujet le permet)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    non_empty = {c: videos for c, videos in cache_contents.items() if videos}

    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write(f"{len(non_empty)}\n")
        # on trie les caches par id juste pour avoir une sortie deterministe
        for c in sorted(non_empty):
            videos = sorted(non_empty[c])
            f.write(f"{c} " + " ".join(str(v) for v in videos) + "\n")


def read_solution(path: str | Path) -> CacheContents:
    # relit une solution ecrite avant (utile pour verifier un ancien resultat)
    path = Path(path)
    with open(path, "r", encoding="ascii") as f:
        first = f.readline().strip()
        N = int(first) if first else 0
        cache_contents: CacheContents = {}
        for _ in range(N):
            parts = f.readline().split()
            if not parts:
                continue
            c = int(parts[0])
            videos = {int(v) for v in parts[1:]}
            cache_contents[c] = videos
    return cache_contents


def normalize_solution(cache_contents: CacheContents, C: int) -> CacheContents:
    # renvoie une copie ou tous les caches (meme vides) sont presents
    # pratique pour les algos qui veulent iterer sur range(C)
    out: CacheContents = {c: set() for c in range(C)}
    for c, videos in cache_contents.items():
        out[c] = set(videos)
    return out
