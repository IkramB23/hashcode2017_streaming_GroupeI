# Hash Code 2017 — Streaming Video Caching

Projet d'Advanced Problem Solving.

**Groupe :** Ikram Benchalal · Nada Zina · Aya Haddoun

---

## 1. Le problème (résumé)

Google Hash Code 2017. Le principe :

- Il y a **V vidéos**, chacune avec sa taille en MB.
- Il y a **E endpoints** (des groupes d'utilisateurs). Chaque endpoint est
  connecté au **data center** (latence `L_D`) et à quelques **caches**
  (chacun avec sa latence `L_c`, toujours plus petite que `L_D`).
- Il y a **C caches**, tous de la même capacité **X** MB.
- On a **R descriptions de requêtes** `(vidéo, endpoint, nb_de_requêtes)`.

**On doit décider quelles vidéos mettre dans quels caches**, sans dépasser
la capacité, de manière à **minimiser le temps d'attente moyen**.

Le score officiel est en microsecondes :

$$
\text{score} = \left\lfloor \frac{1000 \cdot \sum_R R_n \cdot (L_D - L)}{\sum_R R_n} \right\rfloor
$$

où `L` est la plus petite latence dispo pour la requête (data center ou un
cache connecté qui contient la vidéo). Formule tirée directement du PDF.

L'exemple du PDF (5 vidéos, 3 caches, 2 endpoints, 4 requêtes) doit donner
**462 500**. On vérifie ça dans les tests automatiques.

---

## 2. Structure du projet

```
advanced_problem_solving_project/
├── src/                          # le code
│   ├── parser.py                 # lecture des .in
│   ├── writer.py                 # ecriture des .out
│   ├── scorer.py                 # calcul du score + validation
│   ├── greedy.py                 # les 3 algos gloutons
│   ├── local_search.py           # hill climbing
│   └── main.py                   # CLI (run / benchmark)
├── tests/
│   ├── example.in                # l'exemple du PDF
│   └── test_example.py           # tests automatiques (7 tests)
├── instances/instances/          # les 4 datasets officiels de la prof
│   ├── me_at_the_zoo.in
│   ├── videos_worth_spreading.in
│   ├── trending_today.in
│   └── kittens.in
├── outputs/                      # les .out generes par nos algos
├── hashcode_problem_statement/   # les 74 pages du sujet en images
├── requirements.txt
└── README.md
```

À propos des fichiers `__init__.py` **vides** dans `src/` et `tests/` : c'est
normal. En Python, un `__init__.py` sert juste à dire "ce dossier est un
package importable". Il n'est pas obligé de contenir du code, et laisser vide
est la pratique standard quand on n'a pas besoin d'exposer de raccourci
d'import.

---

## 3. Ce qui est imposé par le sujet (pas de choix)

Ces éléments viennent directement du PDF Hash Code 2017 (dossier
`hashcode_problem_statement/`) :

- Le **format d'entrée** `V E R C X`, puis tailles des vidéos, puis blocs
  d'endpoints, puis lignes de requêtes.
- Le **format de sortie** : ligne 1 = nombre `N` de caches décrits, puis `N`
  lignes `c v0 v1 v2 ...`.
- La **formule du score** (avec `floor` et le facteur 1000).
- Les **contraintes** : capacité `X` par cache, pas de doublons dans un cache,
  ids valides.
- Les **4 instances** `me_at_the_zoo.in`, `videos_worth_spreading.in`,
  `trending_today.in`, `kittens.in` (fournies par la prof, on ne les
  modifie pas).

Et côté cours, la partie méthodologique du PDF impose de **comparer 3
approches** : énumération exhaustive, glouton, recherche locale.

---

## 4. Nos choix (avec les raisons)

C'est la partie importante. Voilà ce qu'on a décidé nous-mêmes.

### 4.1 Le langage : Python 3.12

- Prototypage rapide, la prof accepte n'importe quel langage.
- `numpy` suffit pour tenir la charge sur `kittens` (10 000 vidéos × 500 caches).
- Un port C++ n'aurait été utile que si on visait des optimisations vraiment
  poussées.

### 4.2 Deux scorers au lieu d'un

- Un scorer **de référence** dans `compute_score` : simple, écrit avec des
  boucles Python, lent mais facile à lire → sert de vérité.
- Un scorer **rapide** `FastScorer` : tout est vectorisé en numpy. Il est
  utilisé par la recherche locale pour évaluer des dizaines de milliers de
  mouvements.
- Pourquoi les deux ? Parce que les tests vérifient que **les deux donnent
  462 500** sur l'exemple. Comme ça, si un jour on casse le scorer rapide en
  l'optimisant, on s'en rend compte tout de suite.

### 4.3 Trois gloutons (au lieu d'un seul)

Le PDF donne des indices : trier par nombre de requêtes, puis par « regret »,
puis combiner. On a implémenté les 3 pour pouvoir comparer :

- **`greedy_gain`** : pour chaque paire (vidéo, cache), on calcule le gain
  total si on plaçait la vidéo dans ce cache, puis on trie par
  **densité = gain / taille**. On préfère les petites vidéos rentables. C'est
  notre choix, pas explicitement dans le sujet.
- **`greedy_requests`** : trie les requêtes par `count` décroissant et place
  chaque vidéo dans le cache le plus proche possible. **Directement suggéré
  par le sujet.**
- **`greedy_regret`** : calcule pour chaque `(vidéo, endpoint)` le **regret**
  = `(2ème meilleure latence − meilleure latence) × nb_requêtes`. Un gros
  regret veut dire "rater le meilleur cache coûte cher, donc on le traite en
  priorité". **Directement suggéré par le sujet aussi.**

Résultat : `greedy_regret` bat les deux autres sur `me_at_the_zoo` et
`videos_worth_spreading`. Comparaison intéressante à montrer.

### 4.4 Hill climbing pour la recherche locale

Le sujet parle de **random walk**, **hill climbing** et **tabu search** comme
familles de recherche locale. On a choisi le **hill climbing simple** pour la
1ère présentation parce que :

- Il est simple à coder et à expliquer.
- Il n'accepte que des améliorations strictes → pas de risque de dégradation.
- Il donne déjà des gains visibles (+25 000 sur `me_at_the_zoo`).
- **Tabu search est prévu pour la 2e présentation** (voir roadmap plus bas).

### 4.5 Le voisinage : add / remove / swap

Le sujet dit textuellement « ajouter/retirer une vidéo d'un cache » et
« échanger des vidéos entre deux caches ». On a implémenté exactement ces
trois mouvements dans `local_search.py` :

- **add** : mettre une vidéo dans un cache si ça rentre.
- **remove** : enlever une vidéo d'un cache.
- **swap** : remplacer une vidéo par une autre pas encore dans le cache.

On tire un `(cache, vidéo)` au hasard et on choisit automatiquement le type
de mouvement selon la situation.

### 4.6 Le hill climbing démarre du meilleur glouton

Le sujet recommande « partir d'une solution initiale ». On lance les 3
gloutons, on garde le meilleur, et on lance HC dessus. Meilleur point de
départ = meilleur point d'arrivée.

### 4.7 Pas d'énumération exhaustive implémentée

Le sujet le dit lui-même : « énumération exhaustive : optimal mais coûteux ».
L'espace fait `2^(V·C)`. Pour `kittens` (V = 10 000, C = 500), c'est
infaisable. On en **parle** dans le rapport et à l'oral sans la coder.

### 4.8 Une CLI unique avec sous-commandes

Une seule commande `python -m src.main`, avec deux sous-commandes `run` et
`benchmark`. Plus propre qu'un script par algo. Facilite la démo.

### 4.9 On garde le dossier `instances/instances/` tel quel

Après avoir dézippé, on a laissé la structure exacte du zip. Ça évite les
erreurs si on veut re-vérifier avec le fichier d'origine. Le `main.py` sait
où chercher.

### 4.10 Tests via `pytest` sur l'exemple du PDF

On aurait pu faire un test manuel une seule fois. À la place on a des tests
automatiques qui **rejouent l'exemple du PDF à chaque fois** et vérifient
que le score est bien 462 500. Ça garantit que rien ne casse quand on
modifie le code.

---

## 5. Comment lancer

### Installation

Une seule fois :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Vérifier que tout marche

```powershell
python -m pytest tests/ -v
```

Doit afficher **7 passed** et confirmer le score 462 500 sur l'exemple.

### Lancer un algo sur une instance

```powershell
# glouton simple
python -m src.main run --instance me_at_the_zoo --algo greedy_regret

# recherche locale (temps limite en secondes)
python -m src.main run --instance videos_worth_spreading --algo hill_climbing --time 20
```

Le fichier de soumission est écrit dans `outputs/<instance>__<algo>.out`.

### Lancer le benchmark complet

```powershell
# les 3 instances rapides
python -m src.main benchmark --instances me_at_the_zoo videos_worth_spreading trending_today --time 10

# tout, kittens compris (plus long)
python -m src.main benchmark --time 10
```

---

## 6. Résultats obtenus

Machine locale, HC = 10 secondes de temps limite.

| Instance                 | greedy_gain | greedy_requests | greedy_regret | hill_climbing |
|--------------------------|------------:|----------------:|--------------:|--------------:|
| me_at_the_zoo            |     418 451 |         468 625 |       470 649 |   **495 952** |
| videos_worth_spreading   |     501 537 |         491 993 |       532 455 |   **532 766** |
| trending_today           |      25 791 |         499 980 |       499 980 |       499 980 |
| kittens (greedy_requests seul, 24 s) | – |     **537 077** |             – |             – |

### Ce que ça nous apprend

- `greedy_regret` est le meilleur glouton sur les instances petites et
  moyennes. Bon signe : le tri par regret capture bien l'intuition.
- Le hill climbing **améliore vraiment** `me_at_the_zoo` (+25 000 points).
  Sur les autres l'amélioration est marginale.
- `trending_today` a des caches très gros (50 000 MB). Le glouton sature
  presque tous les besoins → il ne reste plus grand chose à améliorer.
- Sur `kittens` on ne fait tourner que le glouton pour l'instant. Le
  chargement et la 1ère évaluation prennent déjà 20+ secondes. Il faudra un
  **delta-scoring** pour rendre le HC praticable ici (roadmap).

---

## 7. Répartition des tâches

| Personne          | Ce qu'elle a fait                                                             |
|-------------------|-------------------------------------------------------------------------------|
| Ikram Benchalal   | Parser, writer, scorers (référence + rapide), CLI, benchmark, tests           |
| Nada Zina         | Les 3 algos gloutons (`greedy_gain`, `greedy_requests`, `greedy_regret`)      |
| Aya Haddoun       | Recherche locale (hill climbing) et analyse des résultats                     |

---

## 8. Roadmap (après cette 1ère présentation)

- **Tabu search** : mémoriser les derniers mouvements pour éviter de revenir
  en arrière et sortir des minimums locaux. Cité par le sujet.
- **Delta scoring** : au lieu de rescorer toute la solution après un
  mouvement, ne mettre à jour que les requêtes affectées. Ça devrait rendre
  le HC utilisable sur `kittens`.
- **Multi-restart** : relancer plusieurs fois avec des seeds différentes et
  garder un pourcentage de la meilleure solution (comme suggéré dans le
  sujet).
- **Courbes de convergence** avec `matplotlib` pour visualiser l'évolution
  du score dans le temps.
