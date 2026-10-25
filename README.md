
# Lost Item Recovery Agent

An AI-based project that simulates the recovery of misplaced items in a campus environment using classical Artificial Intelligence search algorithms. The system compares BFS, Greedy Best-First Search, and A* to find routes, prioritize candidate locations, and simulate recovery missions.

## Project Information

- **Course:** ECSCT24301 – Foundation of AI
- **University:** Adani University
- **Project Track:** Applied AI Project
- **Domain:** Artificial Intelligence, Search Algorithms, Path Planning
- **Language:** Python
- **Interface:** Flask, HTML, CSS, JavaScript

## Overview

Finding a misplaced item can require checking multiple locations. Random searching may waste time and movement. This project models the campus as a graph or grid and uses AI search algorithms to identify routes and prioritize locations to inspect.

The application provides an interactive interface for exploring search algorithms, visualizing routes, simulating recovery missions, and comparing algorithm performance.

**Note:** This is a simulation-based project. It does not detect real objects using cameras, GPS, physical sensors, or a trained machine-learning model. Candidate beliefs and recovery outcomes are simulated or supplied as inputs.

## Features

- Campus graph and grid-based environments
- Breadth-First Search (BFS)
- Greedy Best-First Search
- A* search algorithm
- Heuristic-based pathfinding
- Candidate-location ranking
- Simulated lost-item recovery missions
- Interactive route and grid visualization
- Algorithm comparison
- Benchmark experiments
- Performance metrics and CSV export
- Automated testing

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application and AI algorithms |
| Flask | Backend server and API |
| HTML | Webpage structure |
| CSS | Interface styling |
| JavaScript | Frontend interactions and visualization |
| NumPy | Numerical utilities |
| pandas | Data processing and benchmark results |
| Matplotlib | Charts and visualization utilities |
| pytest | Automated testing |

## AI Algorithms

### 1. Breadth-First Search (BFS)

- Explores nodes level by level.
- Uses a FIFO queue.
- Finds a minimum-edge path in an unweighted graph.
- Does not generally minimize total weighted path cost.

### 2. Greedy Best-First Search

- Prioritizes the estimated remaining distance to the goal.
- Uses a heuristic function to guide exploration.
- Can explore fewer nodes in some scenarios.
- Does not guarantee an optimal path.

### 3. A* Search

A* combines the cost already incurred with an estimate of the remaining cost.

**Evaluation function:**

`f(n) = g(n) + h(n)`

Where:
- `g(n)` = cost from the start to the current node.
- `h(n)` = estimated cost from the current node to the goal.
- `f(n)` = estimated total path cost.

A* can find an optimal path when the cost model, heuristic properties, and implementation satisfy the required conditions.

## Heuristic Functions

### Manhattan Distance

`h(n) = |x1 - x2| + |y1 - y2|`

Suitable for four-directional grid movement under appropriate cost assumptions.

### Euclidean Distance

`h(n) = sqrt((x1 - x2)^2 + (y1 - y2)^2)`

Measures straight-line distance between two points. Its admissibility on the campus graph depends on the relationship between edge costs and geometric distances.

### Zero Heuristic

`h(n) = 0`

With nonnegative edge costs, A* behaves as uniform-cost search. It is equivalent to BFS only when all step costs are equal.

## Candidate Ranking and Recovery

The candidate planner uses information such as:

- Route or search cost
- Configured inspection effort
- User-supplied candidate belief values

The system prioritizes candidate locations and simulates the process of visiting and inspecting them.

Candidate beliefs are not learned from real-world data. The multi-location visit order uses a greedy nearest-neighbor strategy, which is not guaranteed to be globally optimal.

## Project Architecture

```text
lost-item-recovery-agent/
│
├── app.py
├── requirements.txt
├── pytest.ini
├── README.md
│
├── backend/
│   ├── web/
│   ├── environment/
│   ├── search/
│   ├── planner/
│   ├── benchmark/
│   ├── visualization/
│   └── tests/
│
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── documentation/
    └── TECHNICAL_DOCUMENTATION.md
```

### Main Components

- **app.py:** Starts the Flask application.
- **backend/web/:** Provides web routes and API endpoints.
- **backend/environment/:** Models the campus graph, grid, locations, and movement rules.
- **backend/search/:** Contains BFS, Greedy, A*, heuristics, and search results.
- **backend/planner/:** Handles candidate ranking and simulated recovery missions.
- **backend/benchmark/:** Runs experiments and exports benchmark data.
- **backend/visualization/:** Provides chart utilities.
- **backend/tests/:** Contains automated tests.
- **frontend/:** Contains the web interface and client-side interactions.

## Installation and Setup

### Requirements

- Windows 10 or Windows 11
- Python 3.11 or newer
- VS Code (recommended)
- Internet access for initial dependency installation

### Step 1: Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd lost-item-recovery-agent
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with the actual repository URL. If you already downloaded the project, open its extracted folder instead.

### Step 2: Create a Virtual Environment

```powershell
py -3.14 -m venv .venv
```

If Python 3.14 is not installed, use the version available on your computer.

### Step 3: Activate the Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run the following command in the current terminal and retry activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Step 4: Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 5: Start the Application

```powershell
python app.py
```

### Step 6: Open the Website

Open your browser and visit:

`http://127.0.0.1:5000`

Keep the terminal running while using the application.

## API Verification

With the application running, use these endpoints:

| Endpoint | Purpose |
|---|---|
| `/` | Main web interface |
| `/api/health` | Backend health check |
| `/api/config` | Campus configuration |

For example:

`http://127.0.0.1:5000/api/health`

The health endpoint should return JSON indicating that the backend is operational.

## Testing

Run the automated test suite from the project root:

```powershell
python -m pytest -q
```

Run a specific test module:

```powershell
python -m pytest backend/tests/test_astar.py -v
```

```powershell
python -m pytest backend/tests/test_web.py -v
```

Record the actual results from your local environment before including test statistics in the final report.

## Benchmarking and Performance Evaluation

The project supports comparisons of search algorithms using benchmark scenarios.

Recommended evaluation metrics:

- Execution time
- Path cost or path length
- Nodes generated
- Nodes expanded
- Search success rate

### Benchmark Procedure

1. Run the quick benchmark to verify the workflow.
2. Run the standard or full benchmark.
3. Save the exported CSV results.
4. Compare BFS, Greedy Best-First Search, and A* on matching scenarios.
5. Generate charts from the measured results.
6. Explain failure cases and performance trade-offs.

**Important:** Actual experimental values should be collected from benchmark runs. Do not report invented runtime, node-count, or success-rate values.

## Limitations

- The campus environment is simulated.
- The system does not detect actual lost objects.
- Candidate beliefs are supplied manually.
- Greedy Best-First Search does not guarantee an optimal route.
- A* can require substantial memory on large search spaces.
- The nearest-neighbor candidate tour is not guaranteed to be globally optimal.
- Runtime measurements depend on the computer and system load.

## Future Improvements

- Incorporate last-seen information into candidate planning where appropriate.
- Improve candidate-location ranking.
- Add search history.
- Support configurable campus locations and blocked corridors.
- Improve route and benchmark visualizations.
- Evaluate larger maps and additional test scenarios.
- Explore integration with validated real-world campus maps.

## References

1. Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. *Numerische Mathematik, 1*, 269–271.
2. Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics, 4*(2), 100–107. https://doi.org/10.1109/TSSC.1968.300136
3. Russell, S. J., & Norvig, P. (2021). *Artificial intelligence: A modern approach* (4th ed.). Pearson.
4. Python Software Foundation. Python documentation. https://docs.python.org/3/
5. Pallets. Flask documentation. https://flask.palletsprojects.com/
6. pytest development team. pytest documentation. https://docs.pytest.org/

## Authors

- Krushal Patel
- Jambukiya Dakshiti
- Parmar Prince

## Academic Project

Developed as part of the Foundation of AI Project-Based Learning course at Adani University.
