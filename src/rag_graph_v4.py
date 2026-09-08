from pathlib import Path
import os
import pickle
import json
import re

import faiss
import numpy as np
import networkx as nx

from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

INDEX_FILE = Path("data/index/archive.index")
METADATA_FILE = Path("data/index/chunks.pkl")
GRAPH_FILE = Path("data/graph/knowledge_graph.pkl")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

FIRST_HOP_K = 8
SECOND_HOP_K = 6
GRAPH_SEARCH_K = 5

MAX_FOLLOW_UP_QUERIES = 3
MAX_GRAPH_QUERIES = 5
MAX_GRAPH_NEIGHBORS = 8

FIRST_HOP_THRESHOLD = 0.30
SECOND_HOP_THRESHOLD = 0.40
GRAPH_THRESHOLD = 0.35

MAX_FINAL_EVIDENCE = 14

ENTITY_SOURCE_BOOST = 0.20
ENTITY_TEXT_BOOST = 0.08


# ============================================================
# LOAD API KEY
# ============================================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY was not found."
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

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


def source_entity_name(source):

    source = Path(source).stem

    source = source.replace(
        ".scan",
        ""
    )

    return normalize_text(source)


# ============================================================
# LOAD SYSTEM COMPONENTS
# ============================================================

print(
    "Loading ByteKnights "
    "Graph-Assisted RAG V4..."
)

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)

index = faiss.read_index(
    str(INDEX_FILE)
)

with open(METADATA_FILE, "rb") as f:
    chunks = pickle.load(f)

with open(GRAPH_FILE, "rb") as f:
    graph = pickle.load(f)

print(
    f"Loaded {len(chunks)} chunks."
)

print(
    f"Loaded graph with "
    f"{graph.number_of_nodes()} nodes "
    f"and {graph.number_of_edges()} edges."
)

print("System ready.")
print()


# ============================================================
# ENTITY-AWARE BOOST
# ============================================================

def calculate_entity_boost(
    query,
    result
):

    normalized_query = normalize_text(
        query
    )

    query_word_set = set(
        normalized_query.split()
    )

    source_name = source_entity_name(
        result["source"]
    )

    normalized_document_text = normalize_text(
        result.get("text", "")
    )

    boost = 0.0

    # Strong exact source/entity-title match
    if (
        source_name
        and len(source_name) >= 4
        and source_name in normalized_query
    ):
        boost += ENTITY_SOURCE_BOOST

    # Partial source-title overlap
    source_words = [
        word
        for word in source_name.split()
        if len(word) >= 5
    ]

    matched_source_words = [
        word
        for word in source_words
        if word in query_word_set
    ]

    if source_words and matched_source_words:

        ratio = (
            len(matched_source_words)
            / len(source_words)
        )

        boost += (
            ENTITY_SOURCE_BOOST
            * ratio
            * 0.5
        )

    # Important query terms in chunk text
    query_words = [
        word
        for word in query_word_set
        if len(word) >= 6
    ]

    text_matches = sum(
        1
        for word in query_words
        if word in normalized_document_text
    )

    if text_matches > 0:

        boost += min(
            ENTITY_TEXT_BOOST,
            text_matches * 0.02
        )

    return boost


# ============================================================
# VECTOR SEARCH
# ============================================================

def search(
    query,
    top_k,
    candidate_multiplier=4
):

    embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True
    )

    embedding = np.array(
        embedding,
        dtype="float32"
    )

    candidate_k = min(
        top_k * candidate_multiplier,
        len(chunks)
    )

    scores, indices = index.search(
        embedding,
        candidate_k
    )

    results = []

    for score, index_id in zip(
        scores[0],
        indices[0]
    ):

        if index_id < 0:
            continue

        chunk = chunks[index_id].copy()

        semantic_score = float(score)

        entity_boost = calculate_entity_boost(
            query,
            chunk
        )

        final_score = (
            semantic_score
            + entity_boost
        )

        chunk["semantic_score"] = semantic_score
        chunk["entity_boost"] = entity_boost
        chunk["score"] = final_score

        results.append(chunk)

    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]


# ============================================================
# GRAPH ENTITY LOOKUP
# ============================================================

def find_graph_entities(text):

    normalized_text = normalize_text(
        text
    )

    matches = []

    for node in graph.nodes:

        normalized_node = normalize_text(
            node
        )

        if not normalized_node:
            continue

        if normalized_node in normalized_text:

            matches.append(
                node
            )

    # Prefer longer, more specific entities
    matches = sorted(
        set(matches),
        key=lambda x: len(
            normalize_text(x)
        ),
        reverse=True
    )

    return matches


# ============================================================
# GET GRAPH NEIGHBORS
# ============================================================

def get_graph_neighbors(
    entities,
    original_question
):

    candidates = []
    seen = set()

    # --------------------------------------------------------
    # COLLECT DIRECT GRAPH NEIGHBORS
    # --------------------------------------------------------

    for entity in entities:

        if entity not in graph:
            continue

        for neighbor in graph.neighbors(entity):

            key = (
                normalize_text(entity),
                normalize_text(neighbor)
            )

            if key in seen:
                continue

            seen.add(key)

            candidates.append(
                {
                    "source_entity": entity,
                    "neighbor": neighbor
                }
            )

    if not candidates:
        return []

    # --------------------------------------------------------
    # SEMANTIC SIMILARITY
    # --------------------------------------------------------

    question_embedding = embedding_model.encode(
        [original_question],
        normalize_embeddings=True
    )[0]

    graph_texts = [
        f"{item['source_entity']} {item['neighbor']}"
        for item in candidates
    ]

    graph_embeddings = embedding_model.encode(
        graph_texts,
        normalize_embeddings=True
    )

    # --------------------------------------------------------
    # DETECT RELATION / BRIDGE TYPE FROM QUESTION
    # --------------------------------------------------------

    question_normalized = normalize_text(
        original_question
    )

    requested_types = []

    type_keywords = {
        "faction": [
            "faction",
            "group",
            "organization",
            "organisation",
            "cartel",
            "choir",
            "house"
        ],

        "accord": [
            "accord",
            "treaty",
            "agreement"
        ],

        "person": [
            "person",
            "individual",
            "member",
            "who"
        ],

        "location": [
            "location",
            "place",
            "where",
            "fortress",
            "citadel",
            "keep",
            "abbey"
        ],

        "relic": [
            "relic",
            "artifact",
            "object",
            "weapon"
        ]
    }

    # Detect types explicitly mentioned in the question
    for entity_type, keywords in type_keywords.items():

        if any(
            keyword in question_normalized.split()
            for keyword in keywords
        ):

            requested_types.append(
                entity_type
            )

    # --------------------------------------------------------
    # SCORE GRAPH NEIGHBORS
    # --------------------------------------------------------

    for item, graph_embedding in zip(
        candidates,
        graph_embeddings
    ):

        semantic_score = float(
            np.dot(
                question_embedding,
                graph_embedding
            )
        )

        neighbor_normalized = normalize_text(
            item["neighbor"]
        )

        type_bonus = 0.0

        # Check whether the neighbor name itself
        # looks compatible with a requested bridge type.
        for requested_type in requested_types:

            keywords = type_keywords[
                requested_type
            ]

            for keyword in keywords:

                if (
                    keyword
                    in neighbor_normalized.split()
                ):

                    type_bonus += 0.12
                    break

        # ----------------------------------------------------
        # SPECIAL GENERIC-NODE PENALTY
        # ----------------------------------------------------

        generic_nodes = {
            "ashen era",
            "annals codex"
        }

        generic_penalty = 0.0

        if (
            neighbor_normalized
            in generic_nodes
        ):

            generic_penalty = 0.10

        # ----------------------------------------------------
        # FINAL GRAPH SCORE
        # ----------------------------------------------------

        final_graph_score = (
            semantic_score
            + type_bonus
            - generic_penalty
        )

        item[
            "graph_semantic_score"
        ] = semantic_score

        item[
            "graph_type_bonus"
        ] = type_bonus

        item[
            "graph_generic_penalty"
        ] = generic_penalty

        item[
            "graph_score"
        ] = final_graph_score

    # --------------------------------------------------------
    # RANK
    # --------------------------------------------------------

    candidates = sorted(
        candidates,
        key=lambda x: x["graph_score"],
        reverse=True
    )

    return candidates[
        :MAX_GRAPH_NEIGHBORS
    ]

    candidates = []
    seen = set()

    # --------------------------------------------------------
    # COLLECT ALL DIRECT GRAPH NEIGHBORS
    # --------------------------------------------------------

    for entity in entities:

        if entity not in graph:
            continue

        for neighbor in graph.neighbors(entity):

            key = (
                normalize_text(entity),
                normalize_text(neighbor)
            )

            if key in seen:
                continue

            seen.add(key)

            candidates.append(
                {
                    "source_entity": entity,
                    "neighbor": neighbor
                }
            )

    if not candidates:
        return []

    # --------------------------------------------------------
    # EMBED THE ORIGINAL QUESTION
    # --------------------------------------------------------

    question_embedding = embedding_model.encode(
        [original_question],
        normalize_embeddings=True
    )[0]

    # --------------------------------------------------------
    # EMBED EACH GRAPH CONNECTION
    # --------------------------------------------------------

    graph_texts = []

    for item in candidates:

        graph_texts.append(
            f"{item['source_entity']} "
            f"{item['neighbor']}"
        )

    graph_embeddings = embedding_model.encode(
        graph_texts,
        normalize_embeddings=True
    )

    # --------------------------------------------------------
    # CALCULATE SEMANTIC RELEVANCE
    # --------------------------------------------------------

    for item, graph_embedding in zip(
        candidates,
        graph_embeddings
    ):

        similarity = float(
            np.dot(
                question_embedding,
                graph_embedding
            )
        )

        item["graph_score"] = similarity

    # --------------------------------------------------------
    # MOST RELEVANT CONNECTIONS FIRST
    # --------------------------------------------------------

    candidates = sorted(
        candidates,
        key=lambda x: x["graph_score"],
        reverse=True
    )

    return candidates[
        :MAX_GRAPH_NEIGHBORS
    ]

# ============================================================
# BUILD GRAPH SEARCH QUERIES
# ============================================================

def generate_graph_queries(
    original_question,
    graph_neighbors
):

    queries = []

    for item in graph_neighbors:

        source_entity = item[
            "source_entity"
        ]

        neighbor = item[
            "neighbor"
        ]

        query = (
            f"{neighbor} "
            f"{original_question}"
        )

        queries.append(
            query
        )

        if (
            len(queries)
            >= MAX_GRAPH_QUERIES
        ):
            break

    return queries


# ============================================================
# EVIDENCE TEXT
# ============================================================

def evidence_text(results):

    parts = []

    for number, result in enumerate(
        results,
        start=1
    ):

        location = result["source"]

        if result.get("page") is not None:

            location += (
                f", page {result['page']}"
            )

        parts.append(
            f"""
[EVIDENCE {number}]
Source: {location}

{result['text']}
"""
        )

    return "\n".join(parts)


# ============================================================
# LLM FOLLOW-UP PLANNER
# ============================================================

def generate_follow_up_queries(
    original_question,
    first_hop_results,
    graph_entities=None,
    graph_neighbors=None
):

    evidence = evidence_text(
        first_hop_results
    )

    # --------------------------------------------------------
    # BUILD GRAPH CONTEXT
    # --------------------------------------------------------

    graph_context_parts = []

    if graph_entities:

        graph_context_parts.append(
            "Entities explicitly detected by the "
            "knowledge graph:"
        )

        for entity in graph_entities[:5]:

            graph_context_parts.append(
                f"- {entity}"
            )

    if graph_neighbors:

        graph_context_parts.append(
            "\nDirect graph relationships:"
        )

        for item in graph_neighbors:

            graph_context_parts.append(
                f"- {item['source_entity']} "
                f"-> {item['neighbor']}"
            )

    if graph_context_parts:

        graph_context = "\n".join(
            graph_context_parts
        )

    else:

        graph_context = (
            "No useful graph relationships "
            "were discovered."
        )

    # --------------------------------------------------------
    # PLANNER PROMPT
    # --------------------------------------------------------

    prompt = f"""
You are planning the SECOND retrieval hop for a
multi-document question-answering system.

ORIGINAL QUESTION:

{original_question}


FIRST-HOP VECTOR EVIDENCE:

{evidence}


KNOWLEDGE GRAPH DISCOVERIES:

{graph_context}


Your job is NOT to answer the question.

Your job is to determine which relationship is still
missing and generate search queries that can retrieve
the missing evidence.

Follow these rules carefully:

1. Start from the exact named entity or entities in the
   original question.

2. Give high priority to direct knowledge-graph
   relationships involving those entities.

3. Use graph-discovered neighboring entities as possible
   bridge entities for the next retrieval hop.

4. Preserve exact entity names.

5. Do not assume that an entity appearing in vector
   evidence is the correct bridge merely because its
   semantic similarity is high.

6. Do not replace a graph-supported bridge entity with an
   unrelated entity from noisy vector evidence.

7. Determine exactly what TYPE of answer the original
   question requests.

8. Generate searches specifically aimed at finding that
   requested type.

9. For example:
   - "which accord" -> search for an accord
   - "which person" -> search for a person
   - "which faction" -> search for a faction
   - "which location" -> search for a location

10. If the graph shows:
       Person -> Faction
    and the question asks which accord that faction won,
    search for:
       Faction -> Accord

11. Do not invent relationships that are not supported by
    either the first-hop evidence or graph discoveries.

When the question requires a specific relationship such as
"member of", preserve that relationship exactly in follow-up
searches.

For example, if the question asks for a faction member, prefer:
- "<Faction> members"
- "member of <Faction>"
- "people explicitly belonging to <Faction>"

Avoid broad substitutions such as:
- "associated with <Faction>"
- "connected to <Faction>"
unless the original question itself asks for association.

12. Generate no more than
    {MAX_FOLLOW_UP_QUERIES} queries.

Return ONLY a valid JSON array of strings.
"""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0
    )

    raw = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    raw = raw.replace(
        "```json",
        ""
    )

    raw = raw.replace(
        "```",
        ""
    )

    raw = raw.strip()

    try:

        queries = json.loads(
            raw
        )

        if not isinstance(
            queries,
            list
        ):
            return []

        # Keep only valid non-empty strings
        queries = [
            query.strip()
            for query in queries
            if isinstance(query, str)
            and query.strip()
        ]

        return queries[
            :MAX_FOLLOW_UP_QUERIES
        ]

    except Exception:

        print()
        print(
            "Could not parse follow-up queries."
        )

        print(
            "LLM returned:"
        )

        print(raw)

        return []

    evidence = evidence_text(
        first_hop_results
    )

    prompt = f"""
You are planning the SECOND retrieval hop for a
multi-document question-answering system.

ORIGINAL QUESTION:

{original_question}


FIRST-HOP EVIDENCE:

{evidence}


Your job is NOT to answer the question.

Your job is to determine what relationship or fact is still
missing and generate search queries that can retrieve it.

Rules:

1. Identify concrete named entities discovered in the
   first-hop evidence.

2. Determine which discovered entity should become the
   subject of the second search.

3. Preserve exact entity names whenever possible.

4. Search for the missing relationship required by the
   original question.

5. Do not invent names or facts.

6. Do not merely repeat the original question unless useful.

7. Generate no more than {MAX_FOLLOW_UP_QUERIES} queries.

8. Pay close attention to the requested answer type.

9. If the question asks for an accord, search specifically
   for accords rather than generic conflicts.

10. Do not broaden specific types into unrelated categories.

Return ONLY a valid JSON array of strings.
"""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0
    )

    raw = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    raw = raw.replace(
        "```json",
        ""
    )

    raw = raw.replace(
        "```",
        ""
    )

    raw = raw.strip()

    try:

        queries = json.loads(
            raw
        )

        if not isinstance(
            queries,
            list
        ):
            return []

        return queries[
            :MAX_FOLLOW_UP_QUERIES
        ]

    except Exception:

        print()
        print(
            "Could not parse follow-up queries."
        )

        print(
            "LLM returned:"
        )

        print(raw)

        return []


# ============================================================
# CLEANING HELPERS
# ============================================================

def deduplicate(results):

    seen = set()
    unique = []

    for result in results:

        chunk_id = result[
            "chunk_id"
        ]

        if chunk_id not in seen:

            seen.add(
                chunk_id
            )

            unique.append(
                result
            )

    return unique


def diversify_sources(
    results,
    max_per_source=2
):

    counts = {}
    diverse = []

    for result in results:

        source = result[
            "source"
        ]

        count = counts.get(
            source,
            0
        )

        if (
            count
            >= max_per_source
        ):
            continue

        diverse.append(
            result
        )

        counts[source] = (
            count + 1
        )

    return diverse


def select_final_evidence(
    first_results,
    graph_results,
    second_results,
    max_evidence=MAX_FINAL_EVIDENCE
):

    selected = []
    seen_chunks = set()
    source_counts = {}

    # --------------------------------------------------------
    # Helper
    # --------------------------------------------------------

    def add_results(results, limit):

        added = 0

        for result in results:

            if added >= limit:
                break

            chunk_id = result["chunk_id"]
            source = result["source"]

            if chunk_id in seen_chunks:
                continue

            # Maximum two chunks from same source
            if source_counts.get(source, 0) >= 2:
                continue

            seen_chunks.add(chunk_id)

            source_counts[source] = (
                source_counts.get(source, 0) + 1
            )

            selected.append(result)

            added += 1

    # --------------------------------------------------------
    # GUARANTEE EACH RETRIEVAL STAGE IS REPRESENTED
    # --------------------------------------------------------

    # Original question / anchor evidence
    add_results(
        first_results,
        4
    )

    # Knowledge-graph bridge evidence
    add_results(
        graph_results,
        4
    )

    # Second-hop relationship evidence
    # Give this slightly more space because it often contains
    # the final fact required by a multi-hop question.
    add_results(
        second_results,
        6
    )

    # --------------------------------------------------------
    # FILL ANY UNUSED SLOTS
    # --------------------------------------------------------

    all_results = (
        second_results
        + graph_results
        + first_results
    )

    for result in all_results:

        if len(selected) >= max_evidence:
            break

        chunk_id = result["chunk_id"]
        source = result["source"]

        if chunk_id in seen_chunks:
            continue

        if source_counts.get(source, 0) >= 2:
            continue

        seen_chunks.add(chunk_id)

        source_counts[source] = (
            source_counts.get(source, 0) + 1
        )

        selected.append(result)

    return selected[
        :max_evidence
    ]


def filter_by_score(
    results,
    minimum_score
):

    return [
        result
        for result in results
        if result.get(
            "semantic_score",
            result["score"]
        ) >= minimum_score
    ]


def rerank_final_evidence(
    question,
    results,
    max_evidence=MAX_FINAL_EVIDENCE
):

    if not results:
        return []

    # --------------------------------------------------------
    # REMOVE EXACT DUPLICATE CHUNKS
    # --------------------------------------------------------

    results = deduplicate(results)

    # --------------------------------------------------------
    # EMBED ORIGINAL QUESTION
    # --------------------------------------------------------

    question_embedding = embedding_model.encode(
        [question],
        normalize_embeddings=True
    )[0]

    # --------------------------------------------------------
    # EMBED ALL CANDIDATE EVIDENCE
    # --------------------------------------------------------

    evidence_texts = [
        result["text"]
        for result in results
    ]

    evidence_embeddings = embedding_model.encode(
        evidence_texts,
        normalize_embeddings=True
    )

    # --------------------------------------------------------
    # SCORE EVERY CHUNK AGAINST ORIGINAL QUESTION
    # --------------------------------------------------------

    for result, embedding in zip(
        results,
        evidence_embeddings
    ):

        question_score = float(
            np.dot(
                question_embedding,
                embedding
            )
        )

        # Keep original retrieval information.
        original_score = result.get(
            "score",
            0.0
        )

        # Original-question relevance gets the most weight.
        final_evidence_score = (
            (0.70 * question_score)
            + (0.30 * original_score)
        )

        result[
            "question_relevance"
        ] = question_score

        result[
            "final_evidence_score"
        ] = final_evidence_score

    # --------------------------------------------------------
    # GLOBAL SORT
    # --------------------------------------------------------

    results = sorted(
        results,
        key=lambda x: x[
            "final_evidence_score"
        ],
        reverse=True
    )

    # --------------------------------------------------------
    # SOURCE DIVERSITY
    # --------------------------------------------------------

    results = diversify_sources(
        results,
        max_per_source=2
    )

    return results[
        :max_evidence
    ]


# ============================================================
# FINAL ANSWER
# ============================================================

def generate_answer(
    question,
    evidence
):

    context = evidence_text(
        evidence
    )

    system_prompt = """
You are ByteKnights, an intelligent assistant for the
Ashen Era Archive.

Answer using ONLY the provided archive evidence.

Rules:

1. Do not use outside knowledge.
2. Never invent facts.
3. Trace multi-step relationships carefully.
4. Identify exactly what TYPE of entity the question asks for.
5. Only return entities matching that requested type.
6. Pay attention to exact entity names.
7. Do not substitute similarly named entities.
16. Respect the exact relationship requested by the question.
17. Do NOT treat related concepts as equivalent relationships.
    Examples:
    - "allied with" does not automatically mean "member of"
    - "hidden oath to" does not automatically mean "member of"
    - "associated with" does not automatically mean "member of"
    - "visited" does not mean "lived in"
    - "fought in" does not mean "won"
    - "possessed" does not mean "forged"
    - "mentioned alongside" does not establish a relationship
18. If the question asks for a member of a faction, prefer evidence
    that explicitly states that the person was a member, belonged to,
    served as part of, or held a clearly defined position within that
    faction.
19. Every link in a multi-hop reasoning chain must be supported by
    the supplied evidence. Do not bridge a missing relationship through
    plausibility.
20. If several people are associated with a faction but only one is
    explicitly identified as a member, choose the explicitly supported
    member.
21. If the evidence establishes the winning faction but does not
    establish an actual member, say that the available evidence is
    insufficient rather than guessing.
8. Cite factual claims using [Evidence X].
9. If multiple evidence items support a claim, cite them.
10. If evidence conflicts, explain it.
11. If evidence is insufficient, say so.
12. If a question depends on a visible image, figure, map,
    plate, portrait, or illustration, do not claim textual
    evidence proves the visual detail.
"""

    prompt = f"""
QUESTION:

{question}


ARCHIVE EVIDENCE:

{context}


Answer using only the evidence above.
"""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0
    )

    return (
        response
        .choices[0]
        .message
        .content
    )


# ============================================================
# PROCESS QUESTION
# ============================================================

def process_question(
    question
):

    question = question.strip()

    if not question or len(question) < 3:
        print("\nPlease enter a meaningful question.")
        return

    # --------------------------------------------------------
    # HOP 1
    # --------------------------------------------------------

    print()
    print(
        "HOP 1: Vector + entity-aware retrieval..."
    )

    first_results = search(
        question,
        FIRST_HOP_K
    )

    print()
    print(
        "Raw first-hop sources:"
    )

    for result in first_results:

        print(
            f"- {result['source']} "
            f"| final={result['score']:.4f} "
            f"| semantic={result['semantic_score']:.4f} "
            f"| entity+={result['entity_boost']:.4f}"
        )

    first_results = filter_by_score(
        first_results,
        FIRST_HOP_THRESHOLD
    )

    first_results = deduplicate(
        first_results
    )

    first_results = diversify_sources(
        first_results,
        max_per_source=2
    )

    # --------------------------------------------------------
    # GRAPH ENTITY DISCOVERY
    # --------------------------------------------------------

    print()
    print(
        "GRAPH: Detecting known entities..."
    )

    graph_entities = find_graph_entities(
        question
    )

    # Also inspect first-hop evidence text
    if not graph_entities:

        first_text = " ".join(
            result["text"]
            for result in first_results
        )

        graph_entities = find_graph_entities(
            first_text
        )

    if graph_entities:

        print(
            "Detected graph entities:"
        )

        for entity in graph_entities[:5]:
            print(
                f"- {entity}"
            )

    else:

        print(
            "No graph entity detected."
        )

    # --------------------------------------------------------
    # GRAPH EXPANSION
    # --------------------------------------------------------

    graph_neighbors = get_graph_neighbors(
    graph_entities[:3],
    question
)

    print()
    print(
        "Graph neighbors:"
    )

    if not graph_neighbors:

        print(
            "- None"
        )

    for item in graph_neighbors:
        print(
            f"- {item['source_entity']} "
            f"-> {item['neighbor']} "
            f"| semantic="
            f"{item['graph_semantic_score']:.4f} "
            f"| type_bonus="
            f"{item['graph_type_bonus']:.4f} "
            f"| penalty="
            f"{item['graph_generic_penalty']:.4f} "
            f"| final="
            f"{item['graph_score']:.4f}"
        )

    graph_queries = generate_graph_queries(
        question,
        graph_neighbors
    )

    graph_results = []

    for query in graph_queries:

        print()
        print(
            f"GRAPH SEARCH: {query}"
        )

        results = search(
            query,
            GRAPH_SEARCH_K
        )

        graph_results.extend(
            results
        )

    graph_results = filter_by_score(
        graph_results,
        GRAPH_THRESHOLD
    )

    graph_results = deduplicate(
        graph_results
    )

    graph_results = sorted(
        graph_results,
        key=lambda x: x["score"],
        reverse=True
    )

    graph_results = diversify_sources(
        graph_results,
        max_per_source=2
    )

    if not first_results and not graph_entities:
        print(
            "\nNo sufficiently relevant archive evidence "
            "was found for this question."
        )
        return

    # --------------------------------------------------------
    # LLM SECOND HOP
    # --------------------------------------------------------

    print()
    print(
        "LLM: Planning second-hop searches..."
    )

    follow_up_queries = generate_follow_up_queries(
        question,
        first_results,
        graph_entities,
        graph_neighbors
    )

    follow_up_queries = [
        query
        for query in follow_up_queries
        if query
        and "<" not in query
        and ">" not in query
        and "entity1" not in query.lower()
        and "entity2" not in query.lower()
    ]

    print()
    print(
        "Generated follow-up searches:"
    )

    if not follow_up_queries:
        print(
            "\nNo valid second-hop searches were generated."
        )

    for query in follow_up_queries:

        print(
            f"- {query}"
        )

    second_results = []

    for query in follow_up_queries:

        print()
        print(
            f"HOP 2 SEARCH: {query}"
        )

        results = search(
            query,
            SECOND_HOP_K
        )

        second_results.extend(
            results
        )

    second_results = filter_by_score(
        second_results,
        SECOND_HOP_THRESHOLD
    )

    second_results = deduplicate(
        second_results
    )

    second_results = sorted(
        second_results,
        key=lambda x: x["score"],
        reverse=True
    )

    second_results = diversify_sources(
        second_results,
        max_per_source=2
    )

    # --------------------------------------------------------
    # COMBINE ALL EVIDENCE
    # --------------------------------------------------------

    combined = select_final_evidence(
        first_results,
        graph_results,
        second_results,
        MAX_FINAL_EVIDENCE
    )

    print()
    print(
        f"Combined evidence chunks: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # FINAL ANSWER
    # --------------------------------------------------------

    print()
    print(
        "Generating final answer..."
    )

    answer = generate_answer(
        question,
        combined
    )

    print()
    print(
        "================================"
    )

    print(
        "FINAL ANSWER"
    )

    print(
        "================================"
    )

    print()
    print(answer)

    # --------------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------------

    print()
    print(
        "================================"
    )

    print(
        "EVIDENCE USED"
    )

    print(
        "================================"
    )

    for number, result in enumerate(
        combined,
        start=1
    ):

        print()

        print(
            f"[Evidence {number}] "
            f"{result['source']}"
        )

        if result.get(
            "page"
        ) is not None:

            print(
                f"Page: "
                f"{result['page']}"
            )

        print(
            f"Semantic: "
            f"{result['semantic_score']:.4f}"
        )

        print(
            f"Entity boost: "
            f"{result['entity_boost']:.4f}"
        )

        print(
            f"Final score: "
            f"{result['score']:.4f}"
        )

        if "question_relevance" in result:

            print(
                f"Question relevance: "
                f"{result['question_relevance']:.4f}"
            )

        if "final_evidence_score" in result:

            print(
                f"Evidence rank score: "
                f"{result['final_evidence_score']:.4f}"
            )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    while True:

        print()
        print(
            "=" * 60
        )

        question = input(
            "Ask ByteKnights "
            "(or type 'exit'): "
        ).strip()

        if question.lower() in [
            "exit",
            "quit",
            "q"
        ]:

            print(
                "ByteKnights stopped."
            )

            break

        if not question:
            continue

        process_question(
            question
        )


if __name__ == "__main__":
    main()