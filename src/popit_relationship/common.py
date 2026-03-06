import asyncio
import os
from functools import wraps
from xml.etree import ElementTree as ET

import networkx as nx
from networkx.exception import NetworkXError

CACHE_PATH_DEFAULT = "./primport-cache.gpickle"
GRAPHML_PATH_DEFAULT = "./primport-cache.graphml"
KEY_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
KEY_RELATIONSHIP = "http://purl.org/vocab/relationship/Relationship"


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def graph_init():
    try:
        return nx.read_gpickle(os.environ.get("CACHE_PATH", CACHE_PATH_DEFAULT))
    except FileNotFoundError:
        graph = nx.MultiDiGraph()
        graph_save(graph)

        return graph


def graph_prune(graph, node_type):
    try:
        for source in graph.predecessors(node_type):
            for dest in graph.successors(source):
                for key, _ in graph.succ[source][dest].items():
                    graph.remove_edges_from((source, dest, key))

            if graph.in_degree(source) == 0:
                graph.remove_node(source)

    except NetworkXError:
        pass


def graph_save(graph):
    return nx.write_gpickle(graph, os.environ.get("CACHE_PATH", CACHE_PATH_DEFAULT))


def graph_export_graphml(graph, path=None):
    output_path = path or os.environ.get("GRAPHML_PATH", GRAPHML_PATH_DEFAULT)
    root = ET.Element(
        "graphml",
        attrib={"xmlns": "http://graphml.graphdrawing.org/xmlns"},
    )
    graphml_graph = ET.SubElement(
        root, "graph", attrib={"id": "G", "edgedefault": "directed"}
    )

    node_keys = _graphml_keys(root, graph.nodes(data=True), "node")
    edge_keys = _graphml_keys(root, graph.edges(keys=True, data=True), "edge")

    for node, attributes in graph.nodes(data=True):
        node_element = ET.SubElement(graphml_graph, "node", attrib={"id": str(node)})
        _graphml_data_elements(node_element, attributes, node_keys)

    for source, target, key, attributes in graph.edges(keys=True, data=True):
        edge_attributes = {"source": str(source), "target": str(target), "id": str(key)}
        edge_element = ET.SubElement(graphml_graph, "edge", attrib=edge_attributes)
        _graphml_data_elements(edge_element, attributes, edge_keys)

    tree = ET.ElementTree(root)
    return tree.write(output_path, encoding="utf-8", xml_declaration=True)


def _graphml_keys(root, entries, scope):
    keys = {}

    for entry in entries:
        attributes = entry[-1]

        for name, value in attributes.items():
            if name not in keys:
                key_id = f"{scope}_{len(keys)}"
                ET.SubElement(
                    root,
                    "key",
                    attrib={
                        "id": key_id,
                        "for": scope,
                        "attr.name": str(name),
                        "attr.type": _graphml_type(value),
                    },
                )
                keys[name] = key_id

    return keys


def _graphml_data_elements(parent, attributes, keys):
    for name, value in attributes.items():
        data_element = ET.SubElement(parent, "data", attrib={"key": keys[name]})
        data_element.text = _graphml_value(value)


def _graphml_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    return "string"


def _graphml_value(value):
    if isinstance(value, bool):
        return str(value).lower()
    return "" if value is None else str(value)


def node_get_type(graph, node):
    try:
        return [j for i, j, k in graph.edges if i == node and k == KEY_TYPE][0]
    except IndexError:
        return False
