from pathlib import Path
import re
import pickle
import networkx as nx


# ============================================================
# CONFIGURATION
# ============================================================

ARCHIVE_DIR = Path(
    r"H:\Codefest2026\Ashen_Era_Archive"
)

WIKI_DIR = ARCHIVE_DIR / "wiki"

OUTPUT_DIR = Path("data/graph")

GRAPH_FILE = OUTPUT_DIR / "knowledge_graph.pkl"


# ============================================================
# NORMALIZE ENTITY NAME
# ============================================================

def filename_to_entity(path):

    name = path.stem

    name = name.replace("_", " ")
    name = name.replace("-", " ")

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip().title()


# ============================================================
# EXTRACT MARKDOWN LINKS
# ============================================================

def extract_markdown_links(text):

    links = []

    # Standard Markdown links:
    # [Iron-Ring Cartel](iron_ring_cartel.md)

    pattern = r"\[([^\]]+)\]\(([^)]+)\)"

    for match in re.finditer(
        pattern,
        text
    ):

        label = match.group(1).strip()
        target = match.group(2).strip()

        # Ignore images
        start_position = match.start()

        if (
            start_position > 0
            and text[start_position - 1] == "!"
        ):
            continue

        links.append(
            {
                "label": label,
                "target": target
            }
        )

    return links


# ============================================================
# EXTRACT WIKI-STYLE LINKS
# ============================================================

def extract_wiki_links(text):

    links = []

    # Supports:
    # [[Iron-Ring Cartel]]
    #
    # and:
    # [[Iron-Ring Cartel|the cartel]]

    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"

    for match in re.finditer(
        pattern,
        text
    ):

        entity = match.group(1).strip()

        if entity:
            links.append(entity)

    return links


# ============================================================
# RESOLVE MARKDOWN TARGET
# ============================================================

def resolve_markdown_target(
    target
):

    # Remove anchors:
    # entity.md#history
    # becomes entity.md

    target = target.split("#")[0]

    target_path = Path(target)

    # We only want links to Markdown/wiki pages.

    if (
        target_path.suffix.lower()
        != ".md"
    ):
        return None

    return filename_to_entity(
        target_path
    )


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph():

    graph = nx.Graph()

    wiki_files = list(
        WIKI_DIR.rglob("*.md")
    )

    print(
        f"Found {len(wiki_files)} "
        f"wiki Markdown files."
    )

    # --------------------------------------------------------
    # PASS 1
    # Add every wiki page as an entity node.
    # --------------------------------------------------------

    for file_path in wiki_files:

        entity = filename_to_entity(
            file_path
        )

        relative_path = str(
            file_path.relative_to(
                ARCHIVE_DIR
            )
        )

        graph.add_node(
            entity,
            source=relative_path,
            entity_type="wiki"
        )

    # --------------------------------------------------------
    # PASS 2
    # Add relationships from links.
    # --------------------------------------------------------

    for file_path in wiki_files:

        source_entity = filename_to_entity(
            file_path
        )

        try:

            text = file_path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            text = file_path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

        # ----------------------------------------------------
        # Markdown links
        # ----------------------------------------------------

        markdown_links = (
            extract_markdown_links(
                text
            )
        )

        for link in markdown_links:

            target_entity = (
                resolve_markdown_target(
                    link["target"]
                )
            )

            if not target_entity:
                continue

            if (
                target_entity
                == source_entity
            ):
                continue

            if (
                target_entity
                not in graph
            ):

                graph.add_node(
                    target_entity,
                    source=None,
                    entity_type="referenced"
                )

            graph.add_edge(
                source_entity,
                target_entity,
                relation="references"
            )

        # ----------------------------------------------------
        # Wiki-style [[...]] links
        # ----------------------------------------------------

        wiki_links = extract_wiki_links(
            text
        )

        for target_entity in wiki_links:

            target_entity = (
                target_entity.strip()
            )

            if (
                target_entity
                == source_entity
            ):
                continue

            if (
                target_entity
                not in graph
            ):

                graph.add_node(
                    target_entity,
                    source=None,
                    entity_type="referenced"
                )

            graph.add_edge(
                source_entity,
                target_entity,
                relation="references"
            )

    return graph


# ============================================================
# SAVE GRAPH
# ============================================================

def save_graph(graph):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        GRAPH_FILE,
        "wb"
    ) as file:

        pickle.dump(
            graph,
            file
        )

    print()
    print(
        f"Saved graph to: "
        f"{GRAPH_FILE}"
    )


# ============================================================
# GRAPH STATISTICS
# ============================================================

def show_statistics(graph):

    print()
    print(
        "================================"
    )
    print(
        "KNOWLEDGE GRAPH STATISTICS"
    )
    print(
        "================================"
    )

    print(
        f"Nodes: "
        f"{graph.number_of_nodes()}"
    )

    print(
        f"Edges: "
        f"{graph.number_of_edges()}"
    )

    isolated = list(
        nx.isolates(graph)
    )

    print(
        f"Isolated nodes: "
        f"{len(isolated)}"
    )

    connected_nodes = (
        graph.number_of_nodes()
        - len(isolated)
    )

    print(
        f"Connected nodes: "
        f"{connected_nodes}"
    )


# ============================================================
# SHOW SAMPLE RELATIONSHIPS
# ============================================================

def show_examples(
    graph,
    limit=20
):

    print()
    print(
        "================================"
    )
    print(
        "SAMPLE RELATIONSHIPS"
    )
    print(
        "================================"
    )

    count = 0

    for source, target in graph.edges():

        print(
            f"{source} "
            f"<--> "
            f"{target}"
        )

        count += 1

        if count >= limit:
            break


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Building ByteKnights "
        "Knowledge Graph..."
    )

    print()

    graph = build_graph()

    show_statistics(
        graph
    )

    show_examples(
        graph
    )

    save_graph(
        graph
    )

    print()
    print(
        "Knowledge graph build complete."
    )


if __name__ == "__main__":
    main()