# Lost Item Recovery Agent

A Foundation of AI project that models searching for a misplaced item as pathfinding through a campus graph or a four-directional grid. It includes BFS, Greedy Best-First Search, A*, candidate-location prioritization, a Streamlit interface, and repeatable benchmark scenarios.

## What is implemented

- A weighted, undirected campus graph with 20 named locations, 26 corridors, and blockable edges.
- A rectangular grid with cardinal movement, obstacles, and seeded map generation.
- BFS (shortest in number of edges), Greedy Best-First Search (prioritizes `h(n)`), and A* (`f(n) = g(n) + h(n)`).
- Manhattan, Euclidean, and null heuristics. A* is cost-optimal when the selected heuristic is admissible; BFS is not weight-optimal on non-uniform graphs, and Greedy does not guarantee an optimal path.
- Search inputs keep the last-seen location separate from the user's current position. User-entered visited places are added to the candidate search list and highlighted on the map.
- Candidate ranking uses `(path cost + room search effort) × (1 - user belief)`. Beliefs are user-supplied, not learned.
- A simulated mission that checks candidate locations in the recommended order and recomputes the route from the last reached location after each unsuccessful inspection. The selected “actual item location” is simulation input, not a sensor or a real recovered object.
- A Streamlit dashboard with a campus-search workspace, grid playground, algorithm comparison, benchmark charts/exports, and methodology.
- Reproducible map and start/goal generation for benchmark scenarios. Runtime measurements are real and can vary between runs.

## Technology

- Python 3.11 or newer
- Streamlit
- Matplotlib
- pandas
- NumPy
- pytest

Install exact/current compatible versions through `requirements.txt`; dependencies are version-ranged rather than fully locked.

## Interface

The Streamlit interface uses a light neutral background and restrained green accents. It uses standard system fonts and Streamlit controls, without external font downloads or decorative icon-heavy sections. The theme is configured in `.streamlit/config.toml` and is applied when launching from the workspace root.

## Project layout

```text
project/
├── app.py                         # Workspace-root Streamlit launcher
├── README.md
├── requirements.txt
├── pytest.ini
├── PROJECT_RULES.md               # GSD workflow rules, not application requirements
├── .agent/ .agents/ .gemini/ .gsd/ adapters/
│                                  # Retained agent/workflow configuration
├── scripts/                       # Agent/workflow validation and search scripts
└── lost_item_agent/
    ├── app.py                     # Package-level Streamlit launcher
    ├── app/
    │   ├── main.py                # Streamlit UI entry point
    │   └── components/            # Search, maps, comparisons, benchmarks, theory
    ├── environment/               # Campus graph, grid, nodes, edges, results
    ├── search/                    # BFS, Greedy, A*, heuristic functions
    ├── planner/                   # Candidate ranking and multi-location missions
    ├── benchmark/                 # Scenarios, runner, summaries, CSV exporter
    ├── visualization/             # Matplotlib charts
    └── tests/                     # pytest and Streamlit AppTest suite
```

The package-level and workspace-root launchers, requirements files, and pytest configurations are intentionally present so the application can be run from either directory.

## Windows setup and launch

Run these commands in PowerShell from the workspace root:

```powershell
cd "D:\COLLEGE\SEMESTER 5\FOUNDATION OF AI\project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The dashboard is served at `http://localhost:8501`. From the package directory, the equivalent commands are:

```powershell
cd "D:\COLLEGE\SEMESTER 5\FOUNDATION OF AI\project\lost_item_agent"
python -m streamlit run app.py
```

## Search and planning details

- **BFS** uses a FIFO queue and returns a path with the fewest edges. Its returned path cost is the sum of the edge weights on that path, but BFS does not minimize that cost when weights differ.
- **Greedy Best-First Search** orders the frontier by heuristic estimate `h(n)` and may return a more costly route.
- **A*** orders by `g(n) + h(n)`, tracks the best known `g` value, and processes improved paths. Its optimality depends on using an admissible heuristic.
- The bundled grid uses unit-cost cardinal moves, for which Manhattan distance is admissible. The default campus graph uses Euclidean distance over its location coordinates; the project tests its admissibility on that bundled graph. The null heuristic is always admissible.
- Dynamic corridor controls change the graph used by the next search. The application is a local simulation; it does not detect real closures or objects.
- The candidate tour is a greedy nearest-neighbor approximation, not an optimal TSP tour. The priority score is a ranking heuristic, not a probability-calibrated or learned decision policy.

## Benchmarks and exports

The standard scenario catalogue contains 5×5, 10×10, 20×20, 30×30, and 50×50 grids at varied obstacle densities, plus the campus graph. The UI also offers a three-scenario fast suite and a configurable custom grid. The UI’s seed and trials-per-scenario controls apply to each selected suite.

For a given trial, all algorithms use the same map and start/goal pair. The seed reproduces map generation and sampled pairs, but not wall-clock timings. Metrics are:

- `nodes_expanded` and `nodes_generated`: search work, including failed attempts.
- `execution_time_ms`: measured by the search function, including unsuccessful searches.
- `path_cost` and `path_length`: populated only when a route is found.
- `success` and `success_rate`: whether a route was found and the fraction of successful trials.

The dashboard plots benchmark summaries and provides raw-trial and summary CSV downloads. In summary tables, path cost/length use successful trials; node counts and runtime include failed trials.

## Tests

From the workspace root:

```powershell
python -m pytest -q
```

The suite covers graph and grid behavior, path correctness, weighted-path distinctions, heuristic properties, candidate planning and mission rerouting, benchmark aggregation/export, charts, and Streamlit page/workspace execution.

## Limitations

- Candidate priors are manually supplied; the system does not learn or update beliefs from observations.
- The simulation assumes the selected actual location contains the item. It does not integrate sensors, databases, or a real campus map.
- Room search effort is fixed per bundled campus location.
- Benchmarks record peak Python allocation per search. The Benchmarks page also includes a deterministic candidate-count sensitivity view for the bundled campus map.
- A dynamic obstacle is applied before the search/mission is run; there is no external event feed or live sensor-based rerouting.
- The nearest-neighbor candidate tour is an approximation and does not guarantee the globally shortest tour.
