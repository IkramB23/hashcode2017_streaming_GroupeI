# tests automatiques sur l'exemple du sujet
# la solution donnee dans le pdf doit produire un score de 462500
# c'est notre garantie que le parser et le scorer sont corrects
from pathlib import Path

import pytest

from src.greedy import GREEDY_ALGOS
from src.parser import parse_instance
from src.scorer import FastScorer, compute_score, validate_solution


# fichier d'exemple recopie a la main depuis le pdf hash code
EXAMPLE_PATH = Path(__file__).with_name("example.in")

# solution proposee dans le pdf:
#   3
#   0 2
#   1 3 1
#   2 0 1
EXAMPLE_SOLUTION = {
    0: {2},
    1: {3, 1},
    2: {0, 1},
}


def test_parse_example():
    # verifie que le parser lit bien les valeurs du pdf
    inst = parse_instance(EXAMPLE_PATH)
    assert (inst.V, inst.E, inst.R, inst.C, inst.X) == (5, 2, 4, 3, 100)
    assert inst.video_sizes == [50, 50, 80, 30, 110]
    assert inst.endpoints[0].latency_dc == 1000
    assert inst.endpoints[0].caches == {0: 100, 2: 200, 1: 300}
    assert inst.endpoints[1].latency_dc == 500
    assert inst.endpoints[1].caches == {}
    assert len(inst.requests) == 4


def test_reference_score_equals_462500():
    # la valeur cible imposee par le sujet
    inst = parse_instance(EXAMPLE_PATH)
    validate_solution(inst, EXAMPLE_SOLUTION)
    assert compute_score(inst, EXAMPLE_SOLUTION) == 462500


def test_fast_score_equals_reference():
    # le scorer rapide doit donner la meme chose que le lent
    inst = parse_instance(EXAMPLE_PATH)
    scorer = FastScorer(inst)
    assert scorer.score(EXAMPLE_SOLUTION) == 462500


@pytest.mark.parametrize("algo_name", list(GREEDY_ALGOS))
def test_greedy_algorithms_return_valid_solution(algo_name):
    # chaque glouton doit rendre une solution valide et non nulle
    inst = parse_instance(EXAMPLE_PATH)
    sol = GREEDY_ALGOS[algo_name](inst)
    validate_solution(inst, sol)
    assert compute_score(inst, sol) > 0


def test_reference_and_fast_scorer_agree_on_empty():
    # une solution vide doit valoir 0 avec les deux scorers
    inst = parse_instance(EXAMPLE_PATH)
    empty = {c: set() for c in range(inst.C)}
    assert compute_score(inst, empty) == 0
    assert FastScorer(inst).score(empty) == 0
