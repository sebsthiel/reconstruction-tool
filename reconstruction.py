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


def top_level_module(module_name, depth=1):
    components = module_name.split(".")
    return ".".join(components[:depth])


def show_graph(graph, size, **args):
    from bokeh.models import (BoxSelectTool, HoverTool, MultiLine,
                          NodesAndLinkedEdges, Plot, Range1d, Scatter, TapTool)
    from bokeh.palettes import Spectral4
    from bokeh.plotting import from_networkx, show

    # nx.draw(graph, with_labels=True, **args)

    plot = Plot(width=size[0], height=size[1], x_range=Range1d(-1.1, 1.1), y_range=Range1d(-1.1, 1.1))
    plot.title.text = "Dependency Graph"

    plot.add_tools(HoverTool(tooltips=None), TapTool(), BoxSelectTool()) #TODO add module name

    graph_renderer = from_networkx(graph, nx.spring_layout, scale=1, center=(0, 0))

    scatter_glyph = Scatter(size=15, fill_color=Spectral4[0])
    graph_renderer.node_renderer.glyph = scatter_glyph
    graph_renderer.node_renderer.selection_glyph = scatter_glyph.clone(fill_color=Spectral4[2])
    graph_renderer.node_renderer.hover_glyph = scatter_glyph.clone(fill_color=Spectral4[1])

    ml_glyph = MultiLine(line_color="#CCCCCC", line_alpha=0.8, line_width=5)
    graph_renderer.edge_renderer.glyph = ml_glyph
    graph_renderer.edge_renderer.selection_glyph = ml_glyph.clone(line_color=Spectral4[2], line_alpha=1)
    graph_renderer.edge_renderer.hover_glyph = ml_glyph.clone(line_color=Spectral4[1], line_width=1)

    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = NodesAndLinkedEdges()

    plot.renderers.append(graph_renderer)

    show(plot)

# MAIN
if len(sys.argv) <= 1:
    print("No file specified")
    exit(1)

print(f"Extracting imports")
ROOT_FOLDER = sys.argv[1]

# Create a network graph
def create_graph():
    graph = nx.DiGraph()

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

    return graph

def get_abstracted_graph(graph, depth=1):
    abstracted_graph = nx.DiGraph()
    for edge in graph.edges:
        source = top_level_module(edge[0], depth)
        target = top_level_module(edge[1], depth)
        if source != target:
            abstracted_graph.add_edge(source, target)

    # for node in graph.nodes:
    #     top_node = top_level_module(node, depth)
    #     if top_node not in abstracted_graph.nodes:
    #         abstracted_graph.add_node(top_node)

    return abstracted_graph


graph = create_graph()
abstracted_graph = get_abstracted_graph(graph, depth=1)
show_graph(abstracted_graph, size=(1000, 1000))