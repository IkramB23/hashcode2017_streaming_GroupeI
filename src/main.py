# point d'entree en ligne de commande
#
# deux sous-commandes:
#   run       -> lance un algo sur une instance et ecrit le .out
#   benchmark -> lance tous les algos sur toutes les instances et affiche un tableau
#
# exemples:
#   python -m src.main run --instance me_at_the_zoo --algo greedy_regret
#   python -m src.main run --instance videos_worth_spreading --algo hill_climbing --time 20
#   python -m src.main benchmark --time 10
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Dict

from .greedy import GREEDY_ALGOS
from .local_search import hill_climbing
from .parser import Instance, parse_instance
from .scorer import FastScorer, validate_solution
from .writer import write_solution


# chemins du projet (calcules a partir de l'emplacement du fichier)
ROOT = Path(__file__).resolve().parent.parent
INSTANCES_DIR = ROOT / "instances" / "instances"
OUTPUTS_DIR = ROOT / "outputs"

# on hardcode les instances officielles pour eviter les fautes de frappe au CLI
INSTANCE_FILES = {
    "me_at_the_zoo": INSTANCES_DIR / "me_at_the_zoo.in",
    "videos_worth_spreading": INSTANCES_DIR / "videos_worth_spreading.in",
    "trending_today": INSTANCES_DIR / "trending_today.in",
    "kittens": INSTANCES_DIR / "kittens.in",
}


# ---------------------------------------------------------------------------
def _run_greedy(instance: Instance, name: str):
    # helper interne: execute un glouton et renvoie (solution, temps)
    algo = GREEDY_ALGOS[name]
    t0 = time.time()
    sol = algo(instance)
    return sol, time.time() - t0


def _run_hill_climbing(instance: Instance, base: str, time_limit: float, seed: int):
    # helper interne: HC en partant du glouton "base"
    base_sol, _ = _run_greedy(instance, base)
    scorer = FastScorer(instance)
    t0 = time.time()
    res = hill_climbing(
        instance,
        base_sol,
        time_limit=time_limit,
        seed=seed,
        verbose=False,
        scorer=scorer,
    )
    return res.solution, time.time() - t0, res


# ---------------------------------------------------------------------------
def cmd_run(args: argparse.Namespace) -> None:
    # sous-commande "run": un algo sur une instance
    path = INSTANCE_FILES[args.instance]
    print(f"Loading {path.name} ...", flush=True)
    t0 = time.time()
    instance = parse_instance(path)
    print(f"  parsed in {time.time() - t0:.2f}s -> {instance.summary()}")

    scorer = FastScorer(instance)

    if args.algo in GREEDY_ALGOS:
        sol, elapsed = _run_greedy(instance, args.algo)
        info = ""
    elif args.algo == "hill_climbing":
        sol, elapsed, res = _run_hill_climbing(
            instance, args.base, args.time, args.seed
        )
        # infos supplementaires pour donner un feedback pendant la demo
        info = (
            f" | HC iters={res.iterations} improvements={res.improvements}"
            f" (from {res.initial_score} -> {res.best_score})"
        )
    else:
        raise SystemExit(f"unknown algo: {args.algo}")

    # on verifie que la solution respecte les contraintes avant de la garder
    validate_solution(instance, sol)
    score = scorer.score(sol)
    print(f"algo={args.algo} score={score} time={elapsed:.2f}s{info}")

    # ecriture du .out avec un nom pratique pour la comparaison
    out_path = OUTPUTS_DIR / f"{args.instance}__{args.algo}.out"
    write_solution(out_path, sol)
    print(f"  wrote {out_path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
def cmd_benchmark(args: argparse.Namespace) -> None:
    # sous-commande "benchmark": tous les algos, plusieurs instances
    instances = args.instances or list(INSTANCE_FILES.keys())
    greedy_algos = ["greedy_gain", "greedy_requests", "greedy_regret"]

    print(f"Benchmark: instances={instances} | HC time budget={args.time}s")
    header = ["instance"] + greedy_algos + ["hill_climbing"]
    rows = []

    for name in instances:
        path = INSTANCE_FILES[name]
        print(f"\n--- {name} ---", flush=True)
        instance = parse_instance(path)
        print(f"  {instance.summary()}")
        scorer = FastScorer(instance)

        scores: Dict[str, int] = {}
        best_greedy_sol = None
        best_greedy_score = -1
        best_greedy_name = None

        # on execute les 3 gloutons
        for algo in greedy_algos:
            sol, elapsed = _run_greedy(instance, algo)
            validate_solution(instance, sol)
            s = scorer.score(sol)
            scores[algo] = s
            print(f"  {algo:>18s}: score={s:>10d}  time={elapsed:.2f}s")
            write_solution(OUTPUTS_DIR / f"{name}__{algo}.out", sol)
            # on garde le meilleur pour lancer le HC dessus
            if s > best_greedy_score:
                best_greedy_score = s
                best_greedy_sol = sol
                best_greedy_name = algo

        # HC en partant du meilleur glouton
        print(
            f"  hill_climbing starting from {best_greedy_name} "
            f"(score={best_greedy_score}) for {args.time}s ...",
            flush=True,
        )
        t0 = time.time()
        res = hill_climbing(
            instance,
            best_greedy_sol,
            time_limit=args.time,
            seed=args.seed,
            verbose=False,
            scorer=scorer,
        )
        validate_solution(instance, res.solution)
        scores["hill_climbing"] = res.best_score
        print(
            f"  {'hill_climbing':>18s}: score={res.best_score:>10d}  "
            f"time={time.time() - t0:.2f}s  iters={res.iterations}  "
            f"improvements={res.improvements}"
        )
        write_solution(OUTPUTS_DIR / f"{name}__hill_climbing.out", res.solution)
        rows.append((name, scores))

    # tableau recap final
    print("\n" + "=" * 84)
    print("FINAL SCORES (higher is better)")
    print("=" * 84)
    print(f"{'instance':<24s}" + "".join(f"{h:>15s}" for h in header[1:]))
    print("-" * 84)
    for name, scores in rows:
        line = f"{name:<24s}"
        for algo in header[1:]:
            line += f"{scores[algo]:>15d}"
        print(line)
    print("=" * 84)


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    # construction du parser argparse et de ses sous-commandes
    p = argparse.ArgumentParser(description="Hash Code 2017 - streaming videos")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="lance un algo sur une instance")
    run.add_argument("--instance", required=True, choices=list(INSTANCE_FILES))
    run.add_argument(
        "--algo",
        required=True,
        choices=list(GREEDY_ALGOS) + ["hill_climbing"],
    )
    run.add_argument(
        "--base",
        default="greedy_gain",
        choices=list(GREEDY_ALGOS),
        help="glouton de depart pour hill_climbing",
    )
    run.add_argument("--time", type=float, default=10.0, help="temps limite HC (s)")
    run.add_argument("--seed", type=int, default=42)
    run.set_defaults(func=cmd_run)

    bench = sub.add_parser("benchmark", help="lance tous les algos sur toutes les instances")
    bench.add_argument(
        "--instances",
        nargs="*",
        choices=list(INSTANCE_FILES),
        help="restreindre a un sous-ensemble (par defaut: toutes)",
    )
    bench.add_argument("--time", type=float, default=10.0)
    bench.add_argument("--seed", type=int, default=42)
    bench.set_defaults(func=cmd_benchmark)

    return p


def main(argv: list[str] | None = None) -> None:
    # cree le dossier outputs s'il n'existe pas et lance la commande demandee
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
