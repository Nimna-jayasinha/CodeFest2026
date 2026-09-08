from pathlib import Path
import pickle
import re


# ============================================================
# CONFIGURATION
# ============================================================

GRAPH_FILE = Path(
    "data/graph/knowledge_graph.pkl"
)


# ============================================================
# LOAD GRAPH
# ============================================================

print(
    "Loading ByteKnights Knowledge Graph..."
)

with open(
    GRAPH_FILE,
    "rb"
) as file:

    graph = pickle.load(
        file
    )

print(
    f"Loaded graph with "
    f"{graph.number_of_nodes()} nodes "
    f"and {graph.number_of_edges()} edges."
)

print()


# ============================================================
# NORMALIZE
# ============================================================

def normalize(text):

    text = text.lower()

    text = text.replace(
        "_",
        " "
    )

    text = text.replace(
        "-",
        " "
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# FIND ENTITY
# ============================================================

def find_entity(
    query
):

    normalized_query = normalize(
        query
    )

    # --------------------------------------------------------
    # Exact normalized match
    # --------------------------------------------------------

    for node in graph.nodes:

        if (
            normalize(node)
            == normalized_query
        ):

            return node

    # --------------------------------------------------------
    # Entity name contained in query
    # --------------------------------------------------------

    candidates = []

    for node in graph.nodes:

        normalized_node = normalize(
            node
        )

        if (
            normalized_node
            and normalized_node
            in normalized_query
        ):

            candidates.append(
                node
            )

    if candidates:

        # Prefer longest/specific entity
        candidates.sort(
            key=lambda x: len(
                normalize(x)
            ),
            reverse=True
        )

        return candidates[0]

    return None


# ============================================================
# SHOW ONE-HOP NEIGHBORS
# ============================================================

def show_neighbors(
    entity
):

    neighbors = list(
        graph.neighbors(
            entity
        )
    )

    print()
    print(
        f"Entity: {entity}"
    )

    print(
        f"Direct relationships: "
        f"{len(neighbors)}"
    )

    print()

    for neighbor in neighbors:

        edge = graph.get_edge_data(
            entity,
            neighbor
        )

        relation = edge.get(
            "relation",
            "related"
        )

        print(
            f"  -> {neighbor} "
            f"[{relation}]"
        )


# ============================================================
# SHOW TWO-HOP NEIGHBORS
# ============================================================

def show_two_hops(
    entity
):

    print()
    print(
        "TWO-HOP CONNECTIONS"
    )

    print(
        "=" * 50
    )

    first_neighbors = list(
        graph.neighbors(
            entity
        )
    )

    shown = set()

    for first in first_neighbors:

        second_neighbors = list(
            graph.neighbors(
                first
            )
        )

        for second in second_neighbors:

            if second == entity:
                continue

            path = (
                entity,
                first,
                second
            )

            if path in shown:
                continue

            shown.add(
                path
            )

            print(
                f"{entity}"
                f" -> "
                f"{first}"
                f" -> "
                f"{second}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    while True:

        print()
        print(
            "=" * 60
        )

        query = input(
            "Enter entity "
            "(or type 'exit'): "
        ).strip()

        if query.lower() in [
            "exit",
            "quit",
            "q"
        ]:

            print(
                "Graph search stopped."
            )

            break

        if not query:
            continue

        entity = find_entity(
            query
        )

        if not entity:

            print(
                "Entity not found "
                "in knowledge graph."
            )

            continue

        show_neighbors(
            entity
        )

        show_two_hops(
            entity
        )


if __name__ == "__main__":
    main()