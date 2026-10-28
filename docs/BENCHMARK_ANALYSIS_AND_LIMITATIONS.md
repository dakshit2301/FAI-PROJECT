# Benchmark Analysis, Failure Cases, and Scalability Limitations

**Course:** ECSCT24301 – Foundation of AI  
**Project:** Lost Item Recovery Agent: An Intelligent Search Agent for Recovering Misplaced Objects in a Dynamic Environment  
**Authors:** Krushal Patel, Jambukiya Dakshit, Parmar Prince  
**Institution:** Faculty of Engineering Sciences and Technology, Adani University  

---

## 1. Executive Summary & Algorithmic Comparison

The Lost Item Recovery Agent compares three foundational pathfinding paradigms across weighted graph and grid environments:
1. **Breadth-First Search (BFS):** Uninformed baseline search using a FIFO queue.
2. **Greedy Best-First Search (Greedy):** Informed heuristic search prioritizing $f(n) = h(n)$.
3. **A\* Search (A\*):** Cost-optimal heuristic search prioritizing $f(n) = g(n) + h(n)$.

### Theoretical Comparison

| Search Property | BFS | Greedy Best-First | A\* |
| :--- | :--- | :--- | :--- |
| **Strategy** | Uninformed (FIFO queue) | Informed ($f = h$) | Informed ($f = g + h$) |
| **Frontier Structure** | Queue (`collections.deque`) | Min-Heap (`heapq`) | Min-Heap (`heapq`) |
| **Completeness** | Yes (finite branching $b$) | Yes (finite state spaces) | Yes (when $c(u,v) \ge \epsilon > 0$) |
| **Cost-Optimality** | No (only hop-count optimal) | No (frequently suboptimal) | **Yes** (when $h$ is admissible) |
| **Re-opening Needed** | No | No | No (if $h$ is consistent / monotonic) |
| **Time Complexity** | $O(b^d)$ | $O(b^m)$ worst-case | $O(b^{\epsilon \cdot d})$ with good heuristic |
| **Space Complexity** | $O(b^d)$ (all frontier nodes in RAM) | $O(b^m)$ (all generated nodes in RAM) | $O(b^d)$ (all generated nodes in RAM) |

---

## 2. Empirical Benchmark Results

Benchmarks were executed across six standardized test scenarios spanning varying state-space scales and obstacle densities:

| Scenario Name | Environment Type | Dimensions / Nodes | Obstacle Density | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Tiny-Open** | GridMap | $5 \times 5$ (25 cells) | $0.0\%$ | Unit baseline, obstacle-free |
| **Small-Light** | GridMap | $10 \times 10$ (100 cells) | $10.0\%$ | Light obstacle scattering |
| **Medium-Moderate** | GridMap | $15 \times 15$ (225 cells) | $20.0\%$ | Moderate campus classroom layout |
| **Large-Dense** | GridMap | $25 \times 25$ (625 cells) | $28.0\%$ | Dense labyrinth with dead-ends |
| **Stress-Test** | GridMap | $50 \times 50$ (2,500 cells) | $15.0\%$ | High-scale state space |
| **Campus-Graph** | CampusGraph | 20 nodes, 26 edges | Corridor blocks | Realistic weighted campus building |

### Empirical Insights

1. **Path Cost & Optimality:**
   - **Campus Graph:** On the weighted campus graph, BFS frequently returns higher movement cost than A\* because it minimizes edge count (hops) rather than edge weights. For example, moving between distant campus wings via stairs or longer corridors might use 3 hops with cost 6.5, whereas A\* finds a 4-hop route with cost 4.5.
   - **Obstacle Grids:** Greedy Best-First Search frequently takes suboptimal detours. When encountering concave obstacles, Greedy blindly hugs the wall closest in direct line-of-sight to the goal, leading to substantial path inflation compared to A\*.
   - **A\* Guarantees:** A\* consistently achieved the lowest cost across 100% of successful trials, confirming the theoretical guarantee of admissibility.

2. **Search Space Exploration (Nodes Expanded):**
   - Greedy Best-First expands the fewest nodes in simple, open layouts where Euclidean or Manhattan distance points directly toward the destination without barriers.
   - However, in dense obstacle scenarios (e.g. `Large-Dense`), Greedy gets trapped in dead-ends and concavities, causing frontier thrashing.
   - BFS expands nodes uniformly in all directions (spherical/diamond expansion wave), expanding up to 4× to 10× more nodes than A\*.
   - A\* maintains a focused search beam directed toward the goal while strictly respecting accumulated cost $g(n)$.

3. **Execution Runtime:**
   - Microsecond timings reflect algorithm complexity: A\* incurs slight heap reordering overhead per push compared to BFS's $O(1)$ deque append, but this overhead is vastly outweighed by A\*'s exponential reduction in expanded states on medium-to-large grids.

---

## 3. Failure Cases and Edge Conditions

### A. Unreachable Destinations & Blocked Paths
- **Scenario:** The target room or grid destination is isolated due to closed passages, locked fire doors, or an unbroken wall of obstacles.
- **Handling:**
  - All three algorithms (`bfs`, `greedy_best_first`, `astar`) gracefully exhaust their frontier when no path exists.
  - Return `SearchResult(success=False, path=[], path_cost=0.0, notes="Goal is unreachable from start.")`.
  - In `CandidatePlanner`, unreachable candidates are assigned `pathfinding_cost = math.inf` and `priority_score = math.inf`.
  - Unreachable candidates are sorted to the bottom of the recommendation table.
  - In `execute_mission`, the agent logs `"Location unreachable"` for that candidate and continues to subsequent reachable candidates from its current location without crashing or aborting the entire mission.

### B. Single Corridor Cuts (Bridges)
- **Scenario:** In the campus graph, blocking `Corridor-G1 ↔ Stairwell` severs access to the entire First Floor (Classrooms 101–103, Offices A & B, Washroom-F).
- **Handling:**
  - The system detects that the first floor candidate locations have become unreachable.
  - If alternative stairs or corridors exist (e.g. `Library ↔ Stairwell`), A\* automatically discovers the detour route.

### C. Start Equals Goal
- **Scenario:** The user specifies their current location as the target candidate.
- **Handling:**
  - Fast-path check immediately returns `path=[start]`, `path_cost=0.0`, `nodes_expanded=1`, `success=True`.
  - In candidate scoring, travel cost is 0.0, so the candidate is evaluated solely on room inspection effort and user belief.

### D. Heuristic Overestimation (Inadmissibility Risk)
- **Scenario:** If a user configures a custom campus layout where edge weights are smaller than straight-line Euclidean distance (e.g., Euclidean distance between two rooms is 5.0, but an edge weight is set to 2.0).
- **Consequence:** The heuristic becomes inadmissible ($h(n) > h^*(n)$), causing A\* to potentially return a suboptimal path.
- **Mitigation:** The system includes a built-in mathematical verification endpoint (`/api/campus/verify_heuristic`) and helper `verify_heuristic_admissibility_and_consistency` that checks every node pair and edge, alerting the user to any overestimation or triangle inequality violations.

---

## 4. Scalability Limitations & Computational Complexity

### A. Memory Explosion in BFS ($O(b^d)$)
- BFS stores every visited state in its FIFO queue and visited set.
- On a $100 \times 100$ grid (10,000 cells) or $3D$ multi-building campus, a deep goal at depth $d=150$ can require storing tens of thousands of states in memory, leading to RAM exhaustion.

### B. High-Resolution Grid Scaling
- As grid dimensions scale to $50 \times 50$ (2,500 nodes) and $100 \times 100$ (10,000 nodes):
  - Heap operations in A\* take $O(\log N)$ time.
  - A\* remains tractable because consistent heuristics prune the effective branching factor from $b \approx 3.8$ down to $b^* \approx 1.05 - 1.2$.
  - Without heuristic guidance (BFS), searching a 2,500-cell grid across opposite corners consumes millions of operation cycles.

### C. Multi-Candidate Tour Ordering (The TSP Dilemma)
- Finding the globally optimal sequence to visit $k$ candidate rooms is the **Travelling Salesperson Problem (TSP)**, which is NP-hard.
- Finding the exact minimum tour requires $O(k!)$ brute-force evaluation or $O(k^2 2^k)$ dynamic programming (Held-Karp). For $k = 15$ candidates, $15! \approx 1.3 \times 10^{12}$ evaluations, which is computationally prohibitive for interactive browser responses.
- **Agent Solution:** The agent employs a **Greedy Nearest-Neighbor approximation** ($O(k^2)$). While fast and intuitive for users, it is a heuristic approximation and does not guarantee the absolute shortest multi-room tour.

### D. Simulation Truth vs Physical Reality
- **Item Location:** The "actual item location" is simulation truth, not real-time radio/Bluetooth/vision sensor data.
- **Belief Weights:** Probabilities are user-supplied subjective estimates, not Bayesian posterior distributions learned from camera feeds or door access logs.
- **Inspection Effort:** Room search costs (1.0 to 5.0 scale) are static estimates of physical room clutter, not dynamic real-time measurements.

---

## 5. Summary of Saved Submission Artifacts

All benchmark trials and generated evidence are persisted in the repository under `output/`:
- `output/benchmark_results_raw.csv`: Granular trial-by-trial logs with node counts, runtimes, and path metrics.
- `output/benchmark_summary.csv`: Aggregated means, minimums, maximums, and success rates.
- `output/submission_evidence/chart_execution_time.png`: Runtime comparison across algorithms.
- `output/submission_evidence/chart_expanded_nodes.png`: Search effort and space exploration comparison.
- `output/submission_evidence/chart_path_cost.png`: Cost-optimality validation.
- `output/submission_evidence/chart_scaling.png`: Scaling behavior across grid sizes.
- `output/submission_evidence/chart_success_rate.png`: Success rate comparison under obstacle constraints.
