import ast
from pathlib import Path
import sys
import networkx as nx
import matplotlib.pyplot as plt

ROOT_FOLDER = ""


def extract_imports(source):
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
    return imports


def extract_imports_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        return extract_imports(source_code)
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Warning: Error reading {file_path}: {e}")
        return []


def module_name_from_file_path(full_file_path):
    file_name = full_file_path[len(ROOT_FOLDER):]
    file_name = file_name.replace("/__init__.py", "")
    file_name = file_name.replace("/", ".")
    file_name = file_name.replace(".py", "")
    return file_name


def is_relevant(module_name):
    if "test" in module_name or "test" in module_name:
        return False
    
    if module_name.startswith("zeeguu"):
        return True
    
    return False


def top_level_module(module_name, depth=1):
    components = module_name.split(".")
    return ".".join(components[:depth])


def create_graph():
    graph = nx.DiGraph()

    for file in Path(ROOT_FOLDER).rglob("*.py"):
        file_path = str(file)
        source_module = module_name_from_file_path(file_path)

        if not is_relevant(source_module):
            continue

        graph.add_node(source_module)

        for used_module in extract_imports_from_file(file_path):
            if is_relevant(used_module):
                graph.add_edge(source_module, used_module)

    return graph


def get_abstracted_graph(graph, depth=1):
    abstracted_graph = nx.DiGraph()
    for source, target in graph.edges:
        abs_source = top_level_module(source, depth)
        abs_target = top_level_module(target, depth)
        if abs_source != abs_target:
            abstracted_graph.add_edge(abs_source, abs_target)
    return abstracted_graph


def show_graph(graph):
    pos = nx.spring_layout(graph, seed=42)

    plt.figure(figsize=(14, 14))
    nx.draw_networkx(
        graph,
        pos,
        with_labels=True,
        node_color="#4C72B0",
        font_color="black",
        font_size=8,
        font_weight="bold",
        node_size=1500,
        edge_color="#AAAAAA",
        arrows=True,
        arrowsize=15,
    )
    plt.title("Dependency Graph", fontsize=14)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


# MAIN
if len(sys.argv) <= 1:
    print("No folder specified")
    exit(1)

ROOT_FOLDER = sys.argv[1]
print(f"Extracting imports from: {ROOT_FOLDER}")

graph = create_graph()
abstracted_graph = get_abstracted_graph(graph, depth=2)
show_graph(abstracted_graph)