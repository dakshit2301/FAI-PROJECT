# Lost Item Recovery Demonstration Log

- Start location: Main Entrance
- Pathfinding algorithm: A*

| Step | From | Inspect | Route | Cost | Expanded | Outcome |
|---:|---|---|---|---:|---:|---|
| 1 | Main Entrance | Canteen | Main Entrance -> Reception -> Canteen | 2.00 | 3 | Not found; replan |
| 2 | Canteen | Lab-A | Canteen -> Corridor-G3 -> Corridor-G2 -> Lab-A | 3.50 | 6 | Not found; replan |
| 3 | Lab-A | Library | Lab-A -> Library | 1.00 | 2 | Item recovered |
