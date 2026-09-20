# parser pour les fichiers d'entree du hash code 2017 "streaming videos"
# on lit un .in et on renvoie un objet Instance qui contient tout ce qu'il faut
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class Request:
    # une description de requete: la video v demandee par l'endpoint e, count fois
    video: int
    endpoint: int
    count: int


@dataclass
class Endpoint:
    # un endpoint = un groupe d'utilisateurs
    # latency_dc = latence vers le data center (obligatoire)
    # caches = dict qui map id_cache -> latence vers ce cache
    latency_dc: int
    caches: Dict[int, int] = field(default_factory=dict)


@dataclass
class Instance:
    # tout ce qui decrit une instance du probleme
    name: str
    V: int  # nombre de videos
    E: int  # nombre d'endpoints
    R: int  # nombre de descriptions de requetes
    C: int  # nombre de caches
    X: int  # capacite d'un cache en MB
    video_sizes: List[int]
    endpoints: List[Endpoint]
    requests: List[Request]

    def summary(self) -> str:
        # petit resume affichable pour la console
        return (
            f"Instance '{self.name}': "
            f"V={self.V}, E={self.E}, R={self.R}, C={self.C}, X={self.X} MB"
        )


def parse_instance(path: str | Path) -> Instance:
    # lit un fichier .in et renvoie l'instance
    path = Path(path)
    with open(path, "r", encoding="ascii") as f:
        # on lit tout d'un coup et on split, c'est plus rapide qu'un readline
        tokens = f.read().split()

    it = iter(tokens)

    def take_int() -> int:
        # petit helper qui consomme le prochain entier du flux
        return int(next(it))

    # 1ere ligne du fichier: V E R C X
    V = take_int()
    E = take_int()
    R = take_int()
    C = take_int()
    X = take_int()

    # 2eme ligne: V tailles de videos
    video_sizes = [take_int() for _ in range(V)]

    # ensuite E blocs decrivant chaque endpoint
    endpoints: List[Endpoint] = []
    for _ in range(E):
        L_D = take_int()  # latence vers le data center
        K = take_int()    # nombre de caches connectes a cet endpoint
        caches: Dict[int, int] = {}
        for _ in range(K):
            c = take_int()
            L_c = take_int()
            caches[c] = L_c
        endpoints.append(Endpoint(latency_dc=L_D, caches=caches))

    # enfin R lignes de requetes (video, endpoint, count)
    requests: List[Request] = []
    for _ in range(R):
        v = take_int()
        e = take_int()
        n = take_int()
        requests.append(Request(video=v, endpoint=e, count=n))

    return Instance(
        name=path.stem,
        V=V,
        E=E,
        R=R,
        C=C,
        X=X,
        video_sizes=video_sizes,
        endpoints=endpoints,
        requests=requests,
    )
