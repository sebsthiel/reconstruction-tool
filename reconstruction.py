import ast
from pathlib import Path
import sys
import os
import networkx as nx

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
    file_name = full_file_path[len(ROOT_FOLDER) :]
    file_name = file_name.replace("/__init__.py", "")
    file_name = file_name.replace("/", ".")
    file_name = file_name.replace(".py", "")
    return file_name

def is_relevant(module_name):
    if "test" in module_name or "test" in module_name:
        return False
    
    return True

def show_graph(graph, size, **args):
    import matplotlib.pyplot as plt

    plt.figure(figsize=size)
    nx.draw(graph, with_labels=True, **args)
    plt.show()

# MAIN
if len(sys.argv) <= 1:
    print("No file specified")
    exit(1)

print(f"Extracting imports")
ROOT_FOLDER = sys.argv[1]

# Create a network graph
graph = nx.DiGraph()
graph.add_node("hello")

# Find all .py files in the specified path and extract imports
for file in Path(ROOT_FOLDER).rglob("*.py"):

    file_path = str(file)
    source_module = module_name_from_file_path(file_path)

    if not is_relevant(source_module):
        continue

    if source_module not in graph.nodes:
        graph.add_node(source_module)
    
    
    for used_module in extract_imports_from_file(file_path):
        if used_module not in graph.nodes:
            graph.add_node(used_module)

        if is_relevant(used_module):
            graph.add_edge(source_module, used_module)
show_graph(graph, size=(10, 10))