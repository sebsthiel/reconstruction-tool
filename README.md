# reconstruction-tool

This is a **Python dependency graph visualization tool** that analyzes code architecture.

**Core Functionality:**
- Extracts import dependencies from Python files using AST parsing
- Builds a directed graph of module dependencies within a codebase
- Analyzes git commit history to calculate **churn** for each module
- Creates an abstracted view of dependencies at a configurable depth level
- Visualizes the dependency graph with matplotlib, showing metrics like code size and churn

**Key Features:**
- **Nodes** are sized by lines of code and colored by churn (blue = low churn, red = high churn)
- **Edges** thickness represents the number of distinct dependencies between modules
- **Filtering** can filter on module prefix, excluding files, and show only top-N modules by churn
- **Git integration** is used to track how frequently each module changes (to calculate churn)
- Uses GraphViz for graph layout

**Usage:**
```
python reconstruction.py /path/to/python/project
```

**Configuration options** at the top of the file you can control depth level, enable/disable churn calculation, module filtering, Enable external dependencies.