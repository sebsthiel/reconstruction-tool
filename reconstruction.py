import ast
from pathlib import Path
import sys
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from collections import defaultdict
from pydriller import Repository

ROOT_FOLDER = ""
DEPTH = 1
ENABLE_CHURN = True
SHOW_EXTERNAL_DEPENDENCIES = False
MODULE_PREFIX_FILTER = ""


def extract_imports(source, package=""):
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0 and package:  # relative import
                base_parts = package.split(".")[:len(package.split(".")) - (node.level - 1)]
                base = ".".join(base_parts)
                if not base:  # This happens when we try to resolve a relative import that goes beyond the top-level package
                    continue
                module = f"{base}.{node.module}" if node.module else base
            else:
                module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
    return imports


def extract_imports_from_file(file_path, source_module=""):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        package = source_module if file_path.endswith("__init__.py") else ".".join(source_module.split(".")[:-1])
        return extract_imports(source_code, package)
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Warning: Error reading {file_path}: {e}")
        return []


def module_name_from_file_path(full_file_path):
    file_name = full_file_path[len(ROOT_FOLDER):]
    file_name = file_name.lstrip("/")
    file_name = file_name.replace("/__init__.py", "")
    file_name = file_name.replace("/", ".")
    file_name = file_name.replace(".py", "")
    return file_name


def is_relevant(module_name):
    if "test" in module_name:
        return False
    

    if MODULE_PREFIX_FILTER == "" or module_name.startswith(MODULE_PREFIX_FILTER):
        return True
    return False


def top_level_module(module_name, depth=2):
    components = module_name.split(".")
    result =".".join(components[:depth])
    if result == "":
        return print(f"Warning: Module '{module_name}' has no components after abstraction.")
    return result

def compute_module_prefix(root_folder):
    parts = []
    path = Path(root_folder).resolve()
    while (path / "__init__.py").exists():
        parts.append(path.name)
        path = path.parent
    return ".".join(reversed(parts))  # e.g. "zeeguu.core"


def find_git_root(start_path):
    """Find the git repository root by traversing up from start_path."""
    path = Path(start_path).resolve()
    while path != path.parent:
        if (path / ".git").exists():
            return str(path)
        path = path.parent
    return None


def calculate_churn(depth=2):
    print("Calculating churn via git history...")
    git_root = find_git_root(ROOT_FOLDER)
    if not git_root:
        print("Warning: No git repository found. Skipping churn calculation.")
        return {}
    
    root_folder_resolved = Path(ROOT_FOLDER).resolve()
    churn = defaultdict(int)
    for commit in Repository(git_root).traverse_commits():
        for modified_file in commit.modified_files:
            path = modified_file.new_path or modified_file.old_path
            if path is None or not path.endswith(".py"):
                continue
            full_path = Path(git_root) / path
            # Only process files within ROOT_FOLDER
            try:
                relative_path = full_path.relative_to(root_folder_resolved)
            except ValueError:
                # File is not in our ROOT_FOLDER
                continue
            
            # Construct path as if it were in ROOT_FOLDER for module name extraction
            adjusted_path = str(root_folder_resolved) + "/" + str(relative_path)
            module = module_name_from_file_path(adjusted_path)
            if is_relevant(module):
                abs_module = top_level_module(module, depth)
                churn[abs_module] += 1
    return churn


def create_graph():
    graph = nx.DiGraph()
    module_loc = {}
    internal_modules = set()
    prefix = compute_module_prefix(ROOT_FOLDER)  # e.g. "zeeguu.core"

    for file in Path(ROOT_FOLDER).rglob("*.py"):
        file_path = str(file)
        source_module = module_name_from_file_path(file_path)
        print(f"Source: {source_module}")
        if not is_relevant(source_module):
            continue

        graph.add_node(source_module)
        module_loc[source_module] = file.stat().st_size
        internal_modules.add(source_module)

        for used_module in extract_imports_from_file(file_path, source_module):
            # Strip "zeeguu.core." prefix so absolute imports match file-based names
            if prefix and used_module.startswith(prefix + "."):
                used_module = used_module[len(prefix) + 1:]
            if is_relevant(used_module):
                graph.add_edge(source_module, used_module)

    nx.set_node_attributes(graph, module_loc, "loc")
    return graph, internal_modules


def get_abstracted_graph(graph, internal_modules=set(), depth=1):
    abstracted_graph = nx.DiGraph()

    internal_abs_modules = {top_level_module(m, depth) for m in internal_modules}  # <-- add this

    module_loc = defaultdict(int)
    for node, data in graph.nodes(data=True):
        abs_node = top_level_module(node, depth)
        module_loc[abs_node] += data.get("loc", 0)

    edge_weight = defaultdict(set)
    for source, target in graph.edges:
        abs_source = top_level_module(source, depth)
        abs_target = top_level_module(target, depth)
        if not SHOW_EXTERNAL_DEPENDENCIES and abs_target not in internal_abs_modules:  
            continue
        if abs_source != abs_target:
            edge_weight[(abs_source, abs_target)].add((source, target))
            abstracted_graph.add_edge(abs_source, abs_target)

    nx.set_node_attributes(abstracted_graph, dict(module_loc), "loc")
    print(f"{len(abstracted_graph.nodes)} nodes in abstracted graph")
    for abs_node in abstracted_graph.nodes:
        print(f"Node '{abs_node}'")
    nx.set_edge_attributes(abstracted_graph, {k: len(v) for k, v in edge_weight.items()}, "dependency_count")
    return abstracted_graph


def show_graph(graph, churn):
    pos = nx.nx_agraph.graphviz_layout(graph, prog="dot")

    # Node size scaled by total file size
    loc_values = [graph.nodes[n].get("loc", 1) for n in graph.nodes]
    max_loc = max(loc_values) if loc_values else 1
    node_sizes = [500 + 4000 * (graph.nodes[n].get("loc", 1) / max_loc) for n in graph.nodes]

    # Node color scaled from blue (low churn) to red (high churn)
    churn_values = [churn.get(n, 0) for n in graph.nodes]
    max_churn = max(churn_values) if any(churn_values) else 1
    colormap = plt.cm.RdYlBu_r  # blue -> yellow -> red
    node_colors = [colormap(churn.get(n, 0) / max_churn) for n in graph.nodes]

    # Edge width scaled by number of distinct low-level dependencies
    weights = [graph.edges[e].get("dependency_count", 1) for e in graph.edges]
    max_weight = max(weights) if weights else 1
    edge_widths = [0.5 + 5 * (w / max_weight) for w in weights]

    plt.figure(figsize=(18, 18))
    nx.draw_networkx(
        graph,
        pos,
        with_labels=False,           # <-- changed
        node_color=node_colors,
        node_size=node_sizes,
        edge_color="#AAAAAA",
        width=edge_widths,
        arrows=True,
        arrowsize=15,
        connectionstyle="arc3,rad=0.1",
    )

    # Remove "zeeguu." prefix for labels
    labels = {node: node.removeprefix("zeeguu.") for node in graph.nodes}
    # Draw labels below each node, offset proportional to node radius
    label_pos = {
        node: (x, y - 0.35 * (node_sizes[i] ** 0.5))
        for i, (node, (x, y)) in enumerate(pos.items())
    }
    nx.draw_networkx_labels(
        graph,
        label_pos,
        labels=labels,
        font_color="black",
        font_size=8,
        font_weight="bold",
    )

    # Colorbar legend
    sm = plt.cm.ScalarMappable(cmap=colormap, norm=mcolors.Normalize(vmin=0, vmax=max_churn))
    plt.colorbar(sm, ax=plt.gca(), label="Churn (commits)", shrink=0.5)

    plt.title("Dependency Graph (zeeguu.*)", fontsize=14)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


# MAIN
if len(sys.argv) <= 1:
    print("No folder specified")
    exit(1)

ROOT_FOLDER = str(Path(sys.argv[1]).resolve())

print(f"Extracting imports from: {ROOT_FOLDER}")

graph, internal_modules = create_graph()
abstracted_graph = get_abstracted_graph(graph, internal_modules, depth=DEPTH)
churn = calculate_churn(depth=DEPTH) if ENABLE_CHURN else {}
show_graph(abstracted_graph, churn)