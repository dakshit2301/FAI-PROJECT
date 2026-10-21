# Lost Item Recovery Agent

A Foundation of AI project that models searching for a misplaced item as pathfinding through a campus graph or a four-directional grid. The website uses plain HTML, CSS, and JavaScript in the browser with a small Flask API; search and planning logic remains in Python.

## Features

- A weighted, undirected campus graph with 20 named locations, 26 corridors, and simulated blocked edges.
- A rectangular grid with cardinal movement, obstacles, and seeded generation.
- BFS (fewest edges), Greedy Best-First Search (heuristic priority), and A* (`f(n) = g(n) + h(n)`).
- Manhattan, Euclidean, and null heuristics, used where appropriate.
- Candidate-location ranking based on path cost, fixed room inspection effort, and user-provided belief.
- A greedy nearest-neighbor multi-location tour and a simulated mission that replans from each reached candidate.
- Algorithm comparison on the same campus start/goal pair.
- Repeatable quick, standard, and configurable benchmark runs with summary metrics and raw CSV export.
- Campus and grid route visualizations rendered in the browser.
- A methodology section describing PEAS and the search problem formulation.

The application is a simulation. The selected actual item location is simulation truth, not a real sensor or learned prediction. Candidate probabilities are supplied manually.

## Technology

- Python 3.11 or newer
- Flask (local Python web/API server)
- HTML, CSS, and JavaScript (browser interface)
- pandas (benchmark summary and CSV data)
- Matplotlib and NumPy (existing benchmark visualization utilities/tests)
- pytest

Install dependencies from the repository root using `requirements.txt`.

## Project layout

```text
project/
├── app.py                         # Root-level website launcher
├── README.md
├── requirements.txt
├── pytest.ini
├── lost_item_agent/
│   ├── web/
│   │   ├── server.py              # Flask routes and Python search API
│   │   └── static/
│   │       ├── index.html         # Website structure
│   │       ├── styles.css         # Website styling
│   │       └── app.js             # Browser interactions and SVG maps
│   ├── environment/               # Campus graph, grid, nodes, edges, results
│   ├── search/                    # BFS, Greedy, A*, heuristic functions
│   ├── planner/                   # Candidate ranking and mission planning
│   ├── benchmark/                 # Scenarios, runner, summaries, CSV support
│   ├── visualization/             # Python benchmark chart utilities
│   └── tests/                     # Search, planner, benchmark, and API tests
└── requirements.txt
```

## Windows setup and launch

From PowerShell in the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The server listens on localhost only.

To start from inside `lost_item_agent` instead:

```powershell
python -m pip install -r requirements.txt
python app.py
```

## Search and planning details

- **BFS** uses a FIFO queue and returns a path with the fewest edges. On the weighted campus graph, that path is not necessarily the lowest movement cost.
- **Greedy Best-First Search** prioritizes `h(n)` and does not guarantee a lowest-cost path.
- **A\*** prioritizes `g(n) + h(n)` and is cost-optimal when the selected heuristic is admissible.
- Manhattan distance is appropriate for unit-cost cardinal grid moves. Euclidean distance is used with the campus graph coordinates; the null heuristic is zero.
- Candidate priority is `(path cost + room search effort) × (1 − user belief)`. Beliefs are not learned.
- The recommended candidate tour uses a greedy nearest-neighbor approximation, not an optimal TSP solution.
- Blocked corridors and obstacles are simulation inputs. There are no live sensors or real campus integrations.

## Benchmarks

The quick suite contains small grids and the campus graph. Standard scenarios also vary grid size and obstacle density, including a 50×50 stress case. A custom grid can be configured in the website.

For each trial, the benchmark runner supplies the same map and start/goal pair to BFS, Greedy, and A*. It reports success, path cost/length, expanded/generated nodes, and search-function execution time. Seeds reproduce map generation and sampled pairs; runtime measurements vary. The website displays summary statistics and offers raw-trial CSV download.

Memory usage and candidate-count benchmark sweeps are not currently part of the website benchmark workflow.

## Tests

From the repository root:

```powershell
python -m pytest -q
```

The tests cover graph/grid behavior, algorithm correctness, candidate planning and mission rerouting, benchmark calculations/exports, visualization helpers, and the Flask website API.

## Limitations

- The campus map is schematic and not a real building plan.
- The selected item location is known only to the simulation.
- Candidate priors are manual and are not updated or learned.
- Room inspection effort is fixed for each bundled location.
- The nearest-neighbor tour is an approximation and does not guarantee the globally shortest multi-location tour.
- The app is intended for local demonstration, not public deployment.
