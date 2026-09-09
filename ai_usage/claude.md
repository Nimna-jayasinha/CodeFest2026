Prompt 1 -  We are working on SLIIT CodeFest 2026 AI Competition, Sub track 1B: “Connecting Facts Across Thousands of Pages.” We have a corpus of interconnected documents where the answer to a question may require connecting facts from multiple documents. Before implementing anything, help us understand the problem deeply. Explain what makes this different from a standard RAG system, what the key technical challenges are, and what capabilities our system should have to successfully answer multi document, multi hop questions. Do not propose a complete solution yet. focus on problem understanding and possible technical considerations.  


Absolutely. The important thing here is to **not jump straight into “let’s build a RAG pipeline.”** A competition like *“Connecting Facts Across Thousands of Pages”* is really testing whether your system can **reason over a distributed body of evidence**, rather than simply retrieve a relevant paragraph.

# 1. What is the problem actually asking?

At a high level, you have:

> **Thousands of interconnected documents → one question → answer requires combining evidence scattered across multiple documents.**

The key phrase is **“connecting facts.”**

Imagine the corpus contains:

* Document A: Information about **Person X**
* Document B: Information about **Company Y**
* Document C: Information about **Event Z**
* Document D: Information about **Person X's relationship with Company Y**
* Document E: Information about **Event Z involving Company Y**

The question might effectively require:

> “What organization was associated with the person who participated in Event Z?”

There may be **no single document containing the answer**.

Instead:

```text
Question
   ↓
Find Entity/Event
   ↓
Document A
   ↓
Discover another entity
   ↓
Document B
   ↓
Discover another relationship
   ↓
Document C
   ↓
Combine evidence
   ↓
Answer
```

That is fundamentally different from:

```text
Question
   ↓
Retrieve relevant chunk
   ↓
LLM
   ↓
Answer
```

The competition is therefore closer to **information retrieval + knowledge graph traversal + multi-hop reasoning + evidence synthesis** than simple RAG.

---

# 2. Standard RAG vs. this problem

Let's make this distinction very clear.

## Standard RAG

A typical RAG system does:

```text
User Question
      ↓
Embedding
      ↓
Vector Database
      ↓
Top-K relevant chunks
      ↓
LLM
      ↓
Answer
```

For example:

> “Who was the CEO of Apple in 2015?”

A good retrieval system might directly retrieve:

> “Tim Cook became CEO of Apple in 2011.”

The LLM doesn't have to perform much reasoning.

---

## Multi-document / multi-hop QA

Now imagine:

> “Which company employed the researcher who received the award mentioned in Document X?”

You might need:

```text
Question
  ↓
Award
  ↓
Document 1
  ↓
Researcher
  ↓
Document 7
  ↓
Employment
  ↓
Company
  ↓
Document 43
  ↓
Verify relationship
  ↓
Answer
```

The answer isn't necessarily retrievable as one semantic chunk.

This creates the central distinction:

### Standard RAG asks:

> **“Which documents are relevant to this question?”**

### Multi-hop QA asks:

> **“Which sequence of facts and documents must I connect to answer this question?”**

That's a much harder problem.

---

# 3. Think of the corpus as a graph

This mental model will be extremely useful for your team.

Instead of thinking:

```text
Document 1
Document 2
Document 3
...
Document 10,000
```

think:

```text
                 ┌──────────────┐
                 │  Document A  │
                 └──────┬───────┘
                        │
                   mentions
                        ↓
                 ┌──────────────┐
                 │   Entity X   │
                 └──────┬───────┘
                        │
                   related to
                        ↓
                 ┌──────────────┐
                 │  Document B  │
                 └──────┬───────┘
                        │
                   mentions
                        ↓
                 ┌──────────────┐
                 │   Entity Y   │
                 └──────┬───────┘
                        │
                        ↓
                 ┌──────────────┐
                 │  Document C  │
                 └──────────────┘
```

There are potentially several types of edges:

* document → entity
* entity → document
* entity → entity
* person → organization
* organization → location
* event → person
* event → date
* document → document
* document → citation
* concept → concept

The question becomes:

> **What path through this graph connects the information required to answer the question?**

That's the essence of multi-hop retrieval.

---

# 4. What makes this technically difficult?

There are several major challenges.

## Challenge 1 — Finding the first useful document

This sounds easy, but it isn't.

Suppose the question is:

> “What position did the person who founded X hold before joining Y?”

The question may not explicitly contain the name of the person.

You need to discover:

```text
Question
 ↓
X
 ↓
Founder
 ↓
Person
```

So the retrieval system needs to understand **entities and relationships**, not just semantic similarity.

A vector search might retrieve documents talking about:

* X
* founders
* employment
* positions

But that doesn't necessarily mean you've found the correct chain.

---

# 5. Challenge 2 — Entity linking

This is a huge issue in large corpora.

Suppose you encounter:

> “Michael Johnson”

There could be multiple Michael Johnsons.

Or:

> “Apple”

could mean:

* Apple Inc.
* the fruit
* Apple Records
* something else depending on corpus context.

Your system needs to understand:

> **Which entity does this mention refer to?**

This is called **entity resolution / entity linking**.

For multi-hop reasoning, mistakes here are deadly.

A wrong entity at hop 1 can produce:

```text
Wrong Entity
     ↓
Wrong Document
     ↓
Wrong Relationship
     ↓
Wrong Answer
```

The system may still produce a very convincing-looking answer.

That's one of the nastier failure modes.

---

# 6. Challenge 3 — Finding the next hop

Finding one relevant document isn't enough.

Suppose:

```text
Question
 ↓
Document A
```

Document A gives you:

> Person X worked for Organization Y.

Now you need to recognize:

> **Organization Y is probably the key to the next retrieval step.**

Then:

```text
Document A
   ↓
Organization Y
   ↓
Search corpus
   ↓
Document B
```

This is **iterative retrieval**.

The system must dynamically decide:

> “Based on what I've learned so far, what should I search for next?”

That's fundamentally different from retrieving Top-10 chunks once at the beginning.

---

# 7. Challenge 4 — Hop count is unknown

Some questions might require:

```text
Question → A → B
```

Others:

```text
Question → A → B → C
```

Others potentially:

```text
Question → A → B → C → D → E
```

So the system shouldn't necessarily assume:

> “Every question is exactly 2-hop.”

It needs some mechanism for deciding:

### “Do I have enough evidence?”

versus

### “I need another hop.”

This introduces a **stopping problem**.

Too few hops:

> incomplete answer.

Too many hops:

> irrelevant information + increased chance of reasoning errors.

---

# 8. Challenge 5 — Retrieval noise grows rapidly

Imagine every retrieval step returns 10 candidate documents.

After one hop:

```text
10 candidates
```

After two:

```text
10 × 10 = 100 possible paths
```

After three:

```text
10 × 10 × 10 = 1,000
```

Obviously a real system doesn't have to explore all of them, but this illustrates the problem.

You need to control:

> **search-space explosion.**

This makes ranking extremely important.

---

# 9. Challenge 6 — Connecting facts is not the same as retrieving facts

Suppose you retrieve these three facts:

### Document A

> Alice founded Company X.

### Document B

> Company X acquired Company Y.

### Document C

> Bob became CEO of Company Y.

You have all the facts.

But you still need to reason:

```text
Alice
 ↓ founded
Company X
 ↓ acquired
Company Y
 ↓ CEO
Bob
```

The challenge is not merely:

> “Did we retrieve the correct documents?”

It is also:

> **“Did we correctly compose the relationships between those documents?”**

That's the **reasoning layer**.

---

# 10. Challenge 7 — Temporal reasoning

This is another big one.

Consider:

> “Which company did Person X work for before joining Company Y?”

The corpus might contain:

```text
2012 → Company A
2016 → Company B
2020 → Company Y
```

A semantic retrieval system might find all three.

But the answer requires understanding **time/order**.

Similarly:

* before
* after
* during
* founded in
* acquired in
* predecessor
* successor
* former CEO
* current CEO

These are relational and temporal constraints.

---

# 11. Challenge 8 — Negation and contradictions

Large corpora can contain statements such as:

Document A:

> “X is the CEO of Y.”

Document B:

> “X stepped down as CEO in 2021.”

Document C:

> “Z became CEO in 2022.”

If the question asks:

> “Who is the current CEO?”

simply retrieving Document A can produce the wrong answer.

The system needs to reason about:

```text
claim
+
timestamp
+
source
+
potential contradiction
```

This becomes **evidence reconciliation**.

---

# 12. Challenge 9 — Evidence provenance

For a competition like this, I would consider this extremely important.

Your system shouldn't merely produce:

> **Answer: John Smith**

It should internally know:

```text
John Smith
    ↑
Document 47
    ↑
Relationship discovered from Document 12
    ↑
Initial entity discovered from Document 3
```

In other words:

> **Why does the system believe this answer?**

You can think of this as an **evidence chain**.

```text
Answer
  ↑
Evidence 3
  ↑
Evidence 2
  ↑
Evidence 1
```

This is valuable for:

* debugging
* answer verification
* confidence estimation
* reducing hallucination
* explaining the answer

---

# 13. Challenge 10 — Context management

Thousands of pages obviously cannot be dumped into an LLM.

Even if you technically could, that would be a terrible strategy.

You need to decide:

> What information is actually worth putting into the reasoning context?

For example:

```text
10,000 documents
       ↓
100 relevant candidates
       ↓
20 promising documents
       ↓
8 evidence passages
       ↓
4 supporting facts
       ↓
Final reasoning
```

This is essentially a **progressive narrowing problem**.

---

# 14. The system needs several different capabilities

Rather than thinking about the solution as “one AI model,” think about the capabilities your system needs.

### Capability 1 — Understand the question

It should identify:

* entities
* attributes
* relationships
* constraints
* temporal conditions
* expected answer type

For example:

> “Who founded the company that acquired X?”

The system should recognize something like:

```text
Target = person

Relationship chain:
person
   ↓ founded
company
   ↓ acquired
X
```

That is already a reasoning structure.

---

# 15. Capability 2 — Retrieve information semantically

The system needs to retrieve documents based on:

* meaning
* entities
* keywords
* relationships
* potentially metadata

Pure keyword search may miss paraphrases.

Pure vector search may retrieve semantically similar but logically irrelevant information.

So conceptually, you should think about **hybrid retrieval** rather than assuming one retrieval method will solve everything.

---

# 16. Capability 3 — Navigate between documents

Once the system finds Document A, it should be able to ask:

> “What entities or relationships in this document could lead me closer to the answer?”

For example:

```text
Document A
   ↓
Person X
   ↓
Organization Y
   ↓
Date Z
```

Those become potential navigation points.

This is where the corpus's **interconnectedness** becomes valuable.

---

# 17. Capability 4 — Perform multi-hop reasoning

The system needs to construct something like:

```text
Hop 1:
X → Person A

Hop 2:
Person A → Organization B

Hop 3:
Organization B → Event C

Hop 4:
Event C → Answer
```

The important thing is that every hop should ideally be supported by evidence.

---

# 18. Capability 5 — Maintain state

This is easy to overlook.

During reasoning, the system needs to remember:

```text
Known:
Person = Alice
Company = X
Year = 2019
Relationship = founded
```

Then incorporate new information.

Otherwise, it may repeatedly retrieve the same documents or lose track of what it's trying to prove.

You can think of this as a temporary **working memory**.

---

# 19. Capability 6 — Verify the reasoning chain

Before answering:

> “Does this actually follow?”

Suppose the system constructs:

```text
A → B
B → C
C → D
```

It should verify that:

* A really relates to B
* B really relates to C
* C really relates to D
* the relationships have the correct direction
* dates aren't contradictory
* the final answer satisfies the original question

This is **chain validation**.

---

# 20. Capability 7 — Know when to stop

A strong system should recognize:

> “I have sufficient evidence.”

rather than endlessly searching.

Conceptually:

```text
Search
 ↓
Evidence?
 ├── No → continue
 └── Yes
       ↓
   sufficient?
     ├── No → another hop
     └── Yes → answer
```

This becomes especially important when the corpus is huge.

---

# 21. Capability 8 — Handle uncertainty

Sometimes the corpus may not contain enough evidence.

A good system shouldn't manufacture a connection.

It should be capable of recognizing:

> “I found A and B, but I cannot establish the required relationship between them.”

That's much better than:

> “The answer is X.”

with a completely fabricated bridge.

---

# 22. A useful way to decompose the problem

I would mentally divide the entire competition into **five layers**:

```text
┌─────────────────────────────┐
│       FINAL ANSWER          │
├─────────────────────────────┤
│    Reasoning / Synthesis    │
├─────────────────────────────┤
│    Evidence Verification    │
├─────────────────────────────┤
│    Multi-Hop Navigation     │
├─────────────────────────────┤
│    Retrieval + Entity Link  │
├─────────────────────────────┤
│       Document Corpus       │
└─────────────────────────────┘
```

Each layer can fail independently.

---

# 23. Important distinction: retrieval failure vs reasoning failure

This is something I'd recommend your team explicitly track.

Suppose the correct answer is **Alice**.

### Case A — Retrieval failure

The correct document was never retrieved.

```text
Correct evidence
      X
      ↓
Retriever
      ↓
Wrong documents
```

No reasoning model can recover the answer.

---

### Case B — Reasoning failure

The correct documents were retrieved:

```text
Document A ✓
Document B ✓
Document C ✓
```

but the model connects them incorrectly.

That's a reasoning problem.

---

### Case C — Entity-linking failure

Correct information exists, but the system connects:

```text
Michael Johnson #1
```

to:

```text
Michael Johnson #2
```

That's an entity resolution problem.

---

### Case D — Evidence interpretation failure

The document says:

> “Alice was formerly CEO.”

but the model interprets it as:

> “Alice is CEO.”

That's an extraction/temporal reasoning problem.

---

# 24. Multi-hop doesn't necessarily mean "more documents"

Another subtle point.

A question can involve multiple reasoning hops **within the same document**, while another may require five separate documents.

So:

> **Hop count ≠ document count.**

A hop represents a reasoning/relationship transition.

For example:

```text
Document A
Person → Company → Event
```

could already involve multiple hops.

Whereas:

```text
Document A → Document B
```

might only represent one meaningful relationship.

This distinction will matter when you evaluate your system.

---

# 25. What your evaluation should ultimately care about

Even before implementing anything, think about the following dimensions.

### 1. Retrieval recall

> Did we retrieve the evidence we needed?

### 2. Path correctness

> Did we follow the correct chain?

### 3. Entity correctness

> Did we identify the correct entities?

### 4. Relationship correctness

> Did we understand how entities are connected?

### 5. Evidence sufficiency

> Is there enough evidence supporting the answer?

### 6. Final answer accuracy

> Is the actual answer correct?

### 7. Efficiency

> How much searching/reasoning was necessary?

A system that gets the right answer by searching hundreds/thousands of documents may be much less practical than one that finds the correct chain quickly.

---

# 26. The biggest misconception to avoid

Don't approach this as:

> **“Let's put all the PDFs into a vector database and ask GPT questions.”**

That's ordinary RAG thinking.

Instead:

> **“Let's treat the corpus as a distributed information network and determine how the required evidence can be discovered, connected, verified, and synthesized.”**

That's much closer to what this sub-track is asking you to solve.

---

# 27. The architecture you should have in your head — NOT the implementation

Without proposing a complete solution yet, your conceptual system might look like:

```text
                    QUESTION
                       │
                       ▼
              Question Understanding
                       │
                       ▼
              Initial Evidence Search
                       │
                       ▼
                Candidate Documents
                       │
                       ▼
                Entity / Fact Extraction
                       │
                       ▼
              ┌─────────────────────┐
              │  Current Knowledge  │
              │       State         │
              └──────────┬──────────┘
                         │
                         ▼
                  Next-Hop Search
                         │
                         ▼
                  New Evidence
                         │
                         ▼
                Chain Construction
                         │
                         ▼
                  Chain Validation
                         │
                  ┌──────┴──────┐
                  │             │
               enough?        not enough
                  │             │
                  ▼             └──────→ another hop
             Answer
```

**That is the conceptual problem.** The technologies used underneath it are a separate discussion.

---

# 28. What I would prioritize learning before implementation

For your team, I'd make sure everyone understands these concepts first:

| Area                     | Why it matters                        |
| ------------------------ | ------------------------------------- |
| Information Retrieval    | Finding useful evidence               |
| Dense retrieval          | Semantic matching                     |
| BM25 / keyword retrieval | Exact entities and terminology        |
| Hybrid retrieval         | Combining semantic + lexical signals  |
| Reranking                | Selecting the best evidence           |
| Entity Linking           | Correctly identifying entities        |
| Knowledge Graphs         | Representing relationships            |
| Graph Traversal          | Navigating connections                |
| Multi-hop QA             | Core competition problem              |
| Query decomposition      | Breaking complex questions into steps |
| Evidence chains          | Supporting reasoning                  |
| Temporal reasoning       | Before/after/current relationships    |
| Contradiction handling   | Conflicting evidence                  |
| Context management       | Keeping reasoning focused             |
| Hallucination control    | Avoiding unsupported conclusions      |
| Answer verification      | Checking the final chain              |

You **do not need to implement all of these as separate components**. They're the technical concepts that explain why this problem is hard.

---

# 29. The key mental model

If you remember only one thing from this discussion, remember this:

### Standard RAG

```text
Question
   ↓
Retrieve
   ↓
Read
   ↓
Answer
```

### Your competition

```text
Question
   ↓
Understand what must be connected
   ↓
Find starting evidence
   ↓
Identify entities / relationships
   ↓
Navigate to new evidence
   ↓
Connect facts
   ↓
Check temporal / relational consistency
   ↓
Determine whether evidence is sufficient
   ↓
Possibly continue another hop
   ↓
Build evidence chain
   ↓
Verify
   ↓
Answer
```

So the core problem isn't really **“How do we search thousands of pages?”**

It's:

> **“How do we discover the right chain of evidence across thousands of pages, while avoiding wrong entities, irrelevant paths, missing hops, contradictions, and unsupported conclusions?”**

That distinction should drive your entire system design.

If we move to the next stage, I'd recommend **first analyzing the actual SLIIT CodeFest 2026 Sub-track 1B dataset/question format and likely evaluation criteria**, and from that derive the *specific* technical requirements before choosing technologies or designing the architecture.

Prompt 2 - Based on our understanding, let's discuss possible system architectures for solving the multi document, multi hop question answering problem. We are considering a RAG based approach but we need to go beyond simple single step retrieval. Suggest a few possible architectures or strategies for connecting related facts across documents. For each approach explain how it would work, its advantages, limitations and implementation complexity. Don't assume 1 approach is automatically the best. We want to compare the alternatives and decide as a team which direction to take

Yes — and I’d actually resist choosing “the RAG architecture” yet. For this problem, there are several reasonable ways to move from **single-hop retrieval → multi-hop evidence discovery**, and they make very different engineering trade-offs.

I checked the current CodeFest 2026 material as context: the official site describes CodeFest 2026 as including tertiary AI/innovation challenges, and the broader competition emphasizes technical depth and real-world AI solutions. ([Codefest - Codefest][1])

For your specific **“Connecting Facts Across Thousands of Pages”** track, I would compare the following architectures.

---

# 1. Architecture A — Iterative / Agentic RAG

This is probably the most natural extension of ordinary RAG.

Instead of:

```text
Question
   ↓
Retrieve Top-K
   ↓
LLM
   ↓
Answer
```

you make retrieval **iterative**:

```text
                  Question
                     ↓
              Initial Retrieval
                     ↓
              Relevant Documents
                     ↓
              Extract New Facts
                     ↓
           "What should I search next?"
                     ↓
               Next Retrieval
                     ↓
              More Documents
                     ↓
             Combine Evidence
                     ↓
                  Answer
```

### Example

Question:

> Which organization was the researcher who received Award X working for when they published Paper Y?

The system might reason:

```text
Question
 ↓
Award X
 ↓
Researcher = Alice
 ↓
Search Alice
 ↓
Paper Y
 ↓
Publication date = 2019
 ↓
Search Alice's employment around 2019
 ↓
Organization = ABC Research
 ↓
Answer
```

The important thing is that **each retrieval depends on what was discovered in the previous retrieval**.

---

## Advantages

### ✅ Relatively easy to build

You can start with an existing RAG system and add:

* query generation
* iterative retrieval
* state
* stopping criteria

You don't need to construct a complete knowledge graph first.

### ✅ Flexible

It can handle questions you didn't anticipate.

You aren't limited to predefined relationship types such as:

```text
PERSON → WORKS_FOR → COMPANY
```

The LLM can reason about more complicated relationships.

### ✅ Good fit for unknown hop counts

It could naturally perform:

```text
2 hops
3 hops
5 hops
...
```

depending on the question.

### ✅ Easy to demonstrate

For a competition presentation, you can actually show:

```text
Question
 ↓
Hop 1
 ↓
Hop 2
 ↓
Hop 3
 ↓
Evidence
 ↓
Answer
```

That makes the system's behavior understandable to judges.

---

## Limitations

The big problem is:

### ❌ LLM-driven search can wander

It might decide:

> “Maybe this document is relevant…”

and start exploring irrelevant branches.

You can end up with:

```text
Question
 ↓
A
 ↓
B
 ↓
C
 ↓
Wrong direction
 ↓
D
 ↓
...
```

### ❌ Hallucinated intermediate queries

The LLM could incorrectly infer:

> “Person X probably worked at Company Y.”

and search based on a false assumption.

### ❌ Retrieval errors compound

If Hop 1 is wrong:

```text
Wrong Hop 1
   ↓
Wrong Hop 2
   ↓
Wrong Hop 3
   ↓
Confident wrong answer
```

### ❌ Potentially expensive

Multiple LLM calls + multiple retrieval operations per question can become expensive and slow.

---

## Complexity

**Implementation: Medium**

You can build a prototype fairly quickly.

**Research/optimization: High**

Getting it to reliably navigate thousands of documents is considerably harder.

---

# 2. Architecture B — Graph-Augmented RAG

This takes a different philosophy.

Instead of treating documents simply as chunks, you explicitly represent the relationships between entities.

Imagine extracting:

```text
Alice
   │
   ├── founded → Company X
   │
   ├── worked_at → University Y
   │
   └── authored → Paper Z
```

and:

```text
Company X
   │
   ├── acquired → Company Y
   └── located_in → Country Z
```

You effectively create:

```text
               Alice
              /  |  \
        founded  |   authored
            /   |       \
      Company X |      Paper Z
           |
        acquired
           ↓
      Company Y
```

Then questions can be answered partly through **graph traversal**.

---

## How it works

You have two major stores:

```text
Documents
   ↓
Vector / lexical index

Entities + Relationships
   ↓
Knowledge graph
```

At query time:

```text
Question
   ↓
Identify entities
   ↓
Find entity in graph
   ↓
Traverse relationships
   ↓
Locate relevant documents
   ↓
Retrieve supporting passages
   ↓
LLM synthesizes answer
```

This is often called **GraphRAG-style reasoning**.

---

## Advantages

### ✅ Excellent for interconnected corpora

This is the architecture most aligned with the phrase:

> **“Connecting Facts.”**

The connections become explicit.

### ✅ Multi-hop becomes natural

For example:

```text
Person
 ↓ worked_at
Company A
 ↓ acquired
Company B
 ↓ founded
Person C
```

Graph traversal can discover this path directly.

### ✅ Better control

You can constrain traversal:

```text
maximum hops = 4
```

or:

```text
only follow relevant relationship types
```

That can dramatically reduce search noise.

### ✅ Strong explainability

You can show:

```text
Alice
 ↓
founded
 ↓
Company X
 ↓
acquired
 ↓
Company Y
 ↓
CEO
 ↓
Bob
```

That's an excellent evidence trail.

---

## Limitations

### ❌ Building the graph is difficult

You need to extract:

```text
entities
relationships
entity types
dates
possibly relationship confidence
```

from thousands of pages.

Extraction errors create graph errors.

### ❌ Entity resolution becomes critical

Suppose:

```text
"John Smith"
```

appears in 50 documents.

Are they:

```text
John Smith #1
John Smith #2
John Smith #3
```

or the same person?

A graph is only as good as its entity resolution.

### ❌ Information loss

Not everything in documents naturally fits into clean triples.

For example:

> “Although X had previously served as CEO, the company announced in 2022 that she would transition to an advisory role.”

That's much richer than:

```text
X → CEO → Company
```

You need to preserve the original evidence.

---

## Complexity

**Implementation: High**

But once built, the reasoning layer can be very powerful.

---

# 3. Architecture C — Hybrid RAG + Graph

This is probably the architecture I'd want your team to seriously consider.

Rather than choosing:

> Vector RAG **OR** Knowledge Graph

use both.

```text
                  Question
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
   Vector Retrieval        Entity/Graph Search
          │                     │
          ↓                     ↓
   Candidate Documents      Candidate Paths
          │                     │
          └──────────┬──────────┘
                     ↓
                Evidence
                     ↓
              Multi-hop Reasoning
                     ↓
                 Verification
                     ↓
                  Answer
```

The graph answers:

> **“What is connected to what?”**

The document retrieval system answers:

> **“Where is the actual textual evidence?”**

That distinction is powerful.

---

## Example

Suppose the graph knows:

```text
Alice
 ↓ worked_at
Company X
 ↓ acquired
Company Y
```

The system can then retrieve the original passages supporting:

```text
Alice worked at X.
X acquired Y.
```

The LLM gets:

```text
Graph path:
Alice → X → Y

Evidence:
Document 17
Document 92
```

and synthesizes the answer.

---

## Advantages

### ✅ Best of both worlds

Graph:

> navigation

RAG:

> textual evidence

LLM:

> reasoning/synthesis

### ✅ More robust than pure graph

You don't have to encode every nuance into graph relationships.

### ✅ More controlled than pure agentic RAG

The graph provides a structure for navigation.

### ✅ Excellent explainability

You can potentially show:

```text
Reasoning Path
Alice
 ↓
Company X
 ↓
Company Y

Evidence
📄 Doc 17
📄 Doc 92
```

---

## Limitations

### ❌ Highest engineering complexity

Now you have:

* document processing
* chunking
* embeddings
* vector search
* entity extraction
* entity resolution
* graph construction
* graph querying
* reranking
* reasoning
* evidence verification

That's a lot.

### ❌ Graph quality matters

A bad graph can actually make retrieval **worse**, because the system may confidently follow incorrect edges.

### ❌ More infrastructure

Potentially:

```text
Vector DB
+
Graph DB
+
LLM
+
Embedding model
+
Reranker
```

---

## Complexity

**High**

But potentially the most capable architecture for this particular problem.

---

# 4. Architecture D — Query Decomposition + Parallel Retrieval

Here the focus is not primarily graph traversal.

Instead, the system breaks a complex question into smaller questions.

For example:

> “Who founded the company that acquired X and where was its founder educated?”

becomes:

```text
Q1:
Which company acquired X?

Q2:
Who founded that company?

Q3:
Where was that founder educated?
```

Then:

```text
             Original Question
                    ↓
             Query Decomposer
             /       |       \
            ↓        ↓        ↓
           Q1       Q2       Q3
            ↓        ↓        ↓
         Search   Search   Search
            \        |       /
             \       |      /
              Evidence
                  ↓
             Final Reasoning
```

---

## Advantages

### ✅ Simple conceptual model

Very understandable:

> Break complex question → answer subquestions → combine.

### ✅ Parallelizable

Independent subquestions can be searched simultaneously.

That can improve latency.

### ✅ Works well for compositional questions

Especially:

```text
Who?
Where?
When?
Which organization?
What happened after?
```

---

## Limitations

The biggest issue:

### ❌ Subquestions may depend on previous answers

For example:

```text
Q1 → determines entity
Q2 → depends on Q1
Q3 → depends on Q2
```

So they aren't truly parallel.

The system needs something like:

```text
Q1
 ↓
Answer
 ↓
Generate Q2
 ↓
Answer
 ↓
Generate Q3
```

which brings you back toward iterative RAG.

### ❌ Decomposition can be wrong

The LLM might misunderstand the question and produce the wrong subquestions.

### ❌ Doesn't inherently model relationships

It decomposes the question, but doesn't necessarily understand the corpus as a connected network.

---

## Complexity

**Medium**

Good starting point, but probably insufficient alone for difficult multi-hop questions.

---

# 5. Architecture E — Search / Beam-Search Over Evidence Paths

This one is particularly interesting from an algorithmic perspective.

Instead of asking an LLM:

> “What should I search next?”

you treat retrieval as a **search problem**.

Suppose:

```text
Question
   ↓
A
```

From A you discover:

```text
B
C
D
```

Instead of following B blindly:

```text
A → B → ...
```

you maintain multiple candidate paths:

```text
Path 1: A → B
Path 2: A → C
Path 3: A → D
```

Score them.

Keep the strongest.

Then expand:

```text
A → B → E
A → B → F
A → C → G
A → D → H
```

Again rank.

This resembles **beam search**.

---

## Advantages

### ✅ Reduces catastrophic wrong-path decisions

Instead of committing immediately to one chain, you maintain alternatives.

### ✅ More algorithmically controlled

You can define:

```text
beam width = 5
maximum hops = 4
minimum evidence score = X
```

### ✅ Potentially more reproducible

Less dependent on an LLM making arbitrary decisions.

---

## Limitations

### ❌ Search space can explode

Even with pruning, the number of paths can grow quickly.

### ❌ Requires a good path-scoring mechanism

How do you determine:

> Is A → B more promising than A → C?

You might need:

* embedding similarity
* entity overlap
* relationship compatibility
* LLM scoring
* reranker score

### ❌ More algorithmically complicated

Compared with basic RAG.

---

## Complexity

**High**

But potentially very interesting if your team wants a stronger algorithmic component.

---

# 6. Architecture F — Multi-Agent Research System

Another option is to divide responsibilities among specialized agents.

For example:

```text
                  Question
                     ↓
              Coordinator Agent
             /        |         \
            ↓         ↓          ↓
       Retriever   Entity      Evidence
        Agent      Agent       Agent
            \         |          /
             \        |         /
                Coordinator
                     ↓
               Verification
                     ↓
                  Answer
```

You might have:

### Retrieval agent

Find candidate documents.

### Entity agent

Resolve people, companies, locations, etc.

### Reasoning agent

Construct the relationship chain.

### Verification agent

Check whether claims are actually supported.

---

## Advantages

### ✅ Modular

Each agent has a clear job.

### ✅ Easy to experiment

You can improve one component independently.

### ✅ Natural for complex research questions

The system behaves somewhat like a research team.

---

## Limitations

### ❌ Overengineering risk

You don't automatically get better performance just because you have five agents.

### ❌ Expensive

Multiple LLM calls.

### ❌ Coordination problems

Agents can disagree.

```text
Agent A: Person = X
Agent B: Person = Y
```

Now somebody has to resolve that.

### ❌ Latency

Potentially much slower than a carefully designed retrieval pipeline.

---

## Complexity

**Very High**

I wouldn't make this the first architecture unless your experiments show that simpler approaches aren't enough.

---

# 7. Architecture G — Two-Stage Retrieval + Multi-Hop Reranking

This is a more conservative architecture.

Instead of building a graph, focus heavily on retrieval quality.

```text
Question
   ↓
Broad Retrieval
   ↓
100 candidate chunks
   ↓
Reranker
   ↓
20 candidates
   ↓
LLM reasoning
   ↓
Identify missing evidence
   ↓
Second retrieval
   ↓
More evidence
   ↓
Answer
```

You essentially create:

> **retrieve → reason → retrieve again → reason**

without constructing an explicit knowledge graph.

---

## Advantages

### ✅ Much easier than GraphRAG

Existing RAG infrastructure can be reused.

### ✅ Strong retrieval can solve surprisingly many questions

Especially if the dataset has good textual links.

### ✅ Less preprocessing

No massive graph-building pipeline.

### ✅ Easier to debug

You can inspect:

```text
retrieval score
reranker score
evidence
answer
```

---

## Limitations

### ❌ Doesn't explicitly model relationships

It may still struggle with:

```text
A → B → C → D
```

when each relationship isn't obvious semantically.

### ❌ Reranking isn't reasoning

A reranker can say:

> “This passage is relevant.”

It doesn't necessarily understand:

> “This passage is the second step in the required evidence chain.”

---

## Complexity

**Medium**

This is probably the safest baseline architecture.

---

# 8. Comparison

Here's how I'd compare them.

| Architecture          | Multi-hop ability | Engineering | Explainability | Flexibility | Main weakness               |
| --------------------- | ----------------: | ----------: | -------------: | ----------: | --------------------------- |
| Iterative RAG         |              ⭐⭐⭐⭐ |         ⭐⭐⭐ |            ⭐⭐⭐ |       ⭐⭐⭐⭐⭐ | Can wander                  |
| GraphRAG              |             ⭐⭐⭐⭐⭐ |       ⭐⭐⭐⭐⭐ |          ⭐⭐⭐⭐⭐ |        ⭐⭐⭐⭐ | Graph construction          |
| Hybrid Graph + RAG    |             ⭐⭐⭐⭐⭐ |       ⭐⭐⭐⭐⭐ |          ⭐⭐⭐⭐⭐ |       ⭐⭐⭐⭐⭐ | Complexity                  |
| Query Decomposition   |               ⭐⭐⭐ |         ⭐⭐⭐ |            ⭐⭐⭐ |        ⭐⭐⭐⭐ | Bad decomposition           |
| Beam/Path Search      |             ⭐⭐⭐⭐⭐ |        ⭐⭐⭐⭐ |           ⭐⭐⭐⭐ |        ⭐⭐⭐⭐ | Search explosion            |
| Multi-Agent           |              ⭐⭐⭐⭐ |       ⭐⭐⭐⭐⭐ |           ⭐⭐⭐⭐ |       ⭐⭐⭐⭐⭐ | Cost/coordination           |
| Retrieval + Reranking |               ⭐⭐⭐ |          ⭐⭐ |            ⭐⭐⭐ |        ⭐⭐⭐⭐ | Weak relationship reasoning |

---

# 9. There is another important dimension: when do you build the graph?

This is something your team should discuss.

You don't necessarily have to choose:

> **Graph OR RAG**

You can have different levels of structure.

### Level 1 — No explicit graph

```text
Documents → Chunks → Embeddings
```

Simplest.

### Level 2 — Lightweight entity index

```text
Documents
 ↓
Entities
 ↓
Entity → documents
```

This is surprisingly useful.

### Level 3 — Relationship graph

```text
Entity → Relationship → Entity
```

Much more powerful.

### Level 4 — Full evidence graph

```text
Document
 ↓ supports
Claim
 ↓ about
Entity
 ↓ relationship
Entity
 ↓ supported by
Document
```

Much more sophisticated.

**You don't necessarily need Level 4.**

---

# 10. My recommendation for your team's experimentation

I wouldn't choose a final architecture yet.

I'd create **three competing prototypes**.

## Prototype 1 — Strong RAG baseline

```text
Hybrid Retrieval
      ↓
Reranker
      ↓
LLM
```

This establishes:

> “How far can ordinary RAG go?”

This baseline is extremely important.

---

## Prototype 2 — Iterative RAG

Then add:

```text
Retrieve
 ↓
Extract facts
 ↓
Generate next query
 ↓
Retrieve
 ↓
Repeat
```

Now you can measure:

> Does multi-hop retrieval significantly improve performance?

---

## Prototype 3 — Lightweight Graph + RAG

Don't immediately build a giant knowledge graph.

Start with:

```text
Documents
 ↓
Entities + relationships
 ↓
Entity graph
 ↓
Graph traversal
 ↓
Retrieve supporting passages
 ↓
LLM
```

Then compare it against Prototype 2.

---

# 11. What I would NOT do initially

I would avoid starting with:

```text
Multi-Agent
+ Knowledge Graph
+ Vector DB
+ Reranker
+ Query Decomposition
+ Autonomous Agent
+ 5 LLMs
```

😂 That's the classic competition-project trap.

It sounds incredibly intelligent in the architecture diagram.

Then two weeks later:

> “Why is the answer wrong?”

Nobody knows which component messed it up.

---

# 12. The experiment that could settle the debate

Your team should eventually create a small evaluation set.

For example, 50–100 questions categorized as:

```text
Category A — Single-hop
Category B — 2-hop
Category C — 3-hop
Category D — 4+ hop
Category E — Temporal
Category F — Entity ambiguity
Category G — Multiple possible paths
Category H — Distractor-heavy
```

Then run:

```text
                   Accuracy
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
     Basic RAG    Iterative RAG   Graph RAG
```

Don't decide based on:

> “GraphRAG sounds more advanced.”

Decide based on:

> **Which architecture actually finds the correct evidence chain on our competition questions?**

That distinction could save your team a *lot* of development time.

---

# 13. One architecture I'd keep in the back of your mind

There is a particularly interesting middle ground:

```text
                  QUESTION
                     ↓
             Query Understanding
                     ↓
          ┌──────────┴──────────┐
          ↓                     ↓
     Vector Search          Entity Search
          ↓                     ↓
      Candidates          Entity candidates
          └──────────┬──────────┘
                     ↓
               Path Builder
                     ↓
              Evidence Graph
                     ↓
             Path Ranking
                     ↓
             Evidence Retrieval
                     ↓
               Verification
                     ↓
                  Answer
```

Notice what this **doesn't** require:

> a gigantic perfect knowledge graph.

Instead, you construct a **small temporary evidence graph around the question**.

That could be a very attractive direction for a competition because you get some of the benefits of GraphRAG without having to perfectly structure the entire corpus beforehand.

---

# 14. The real architectural decision

I think your team's decision should ultimately revolve around this question:

> **Where should the intelligence live?**

### Option A

**LLM does most of the navigation**

→ Iterative/Agentic RAG

### Option B

**Graph does most of the navigation**

→ GraphRAG

### Option C

**Search algorithm does the navigation**

→ Beam/path search

### Option D

**Question decomposition drives navigation**

→ Decomposition RAG

### Option E

**Combine structured navigation + textual retrieval**

→ Hybrid Graph + RAG

That's the fundamental architectural choice.

And importantly, **RAG itself isn't the problem**. RAG is still likely to be one of your core components. The question is whether retrieval is:

> **one-shot**

or

> **iterative, structured, graph-guided, or search-guided.**

For this competition, I'd benchmark **strong hybrid RAG → iterative RAG → lightweight graph+RAG** before committing to anything more elaborate. That gives you a sensible progression from simple to sophisticated while producing evidence for your architectural decision rather than relying on hype.


Prompt 3 - we have access to the Ashen Era Archive corpus provided for the competition. Before implementing RAG system help us plan how to inspect analyze the dataset. We want to understand the document formats, structure, matadata, document length, relationship between documents and any pattern that may affect retrieval. Also identify potential challenges such as duplicate information, inconsistent source reliability, fragmented facts or important documents. Suggest practical dataset inspection steps and what findings we should pay attention to. Don't implement the solution yet 

Absolutely. Before touching embeddings, chunking, vector databases, or RAG, I’d treat the **Ashen Era Archive** as a dataset-analysis problem first.

Your goal at this stage is to answer:

> **“What kind of information system is this corpus actually?”**

Because the answer will strongly influence whether you eventually need plain RAG, iterative retrieval, graph-assisted retrieval, document-level retrieval, etc.

I’d structure the inspection into **8 stages**.

---

# 1. First: inventory the entire corpus

Don't open documents randomly. Start by getting a bird's-eye view.

Create an inventory containing at least:

| Field              | What to determine                           |
| ------------------ | ------------------------------------------- |
| Total files        | How many documents?                         |
| File types         | PDF, TXT, DOCX, HTML, JSON, CSV, etc.       |
| Total size         | MB/GB                                       |
| Folder structure   | Are folders meaningful?                     |
| Naming conventions | Do filenames encode IDs/categories?         |
| Document IDs       | Is there a unique identifier?               |
| Metadata           | Title, author, date, source, category, etc. |
| Language           | One language or multiple?                   |
| Scanned documents  | Are some PDFs image-only?                   |
| Tables/images      | How much non-text content exists?           |

### Why this matters

Suppose you discover:

```text
archive/
├── books/
├── newspapers/
├── letters/
├── reports/
└── records/
```

That immediately tells you something important:

> **Document type itself may be a retrieval signal.**

Similarly, if filenames look like:

```text
DOC_001.pdf
DOC_002.pdf
DOC_003.pdf
```

then filenames probably aren't useful.

But if they're:

```text
war_1942_report.pdf
smith_biography.pdf
royal_decree_1832.pdf
```

you may already have valuable metadata.

---

# 2. Inspect the document formats

Don't assume every PDF behaves the same.

For each format, determine:

### PDF

Check:

* Is text selectable?
* Is it OCR?
* Are pages individually structured?
* Are headers/footers repeated?
* Are tables present?
* Are footnotes important?
* Are citations/references present?
* Are there multiple columns?

A PDF might visually look like:

```text
Title
Author
Date

Main text...

References
```

but extracted text could become:

```text
Title Author Date Main References...
```

with the ordering corrupted.

That can seriously affect retrieval.

---

### HTML

Check whether useful information exists in:

```text
<title>
<h1>
<h2>
<body>
<table>
<meta>
```

Don't throw away HTML metadata automatically.

---

### JSON/XML

These can be extremely valuable because relationships may already be represented structurally.

For example:

```json
{
  "document_id": "D102",
  "title": "...",
  "author": "...",
  "date": "...",
  "references": ["D45", "D87"]
}
```

If the Ashen Era Archive contains anything like this, **stop and investigate it carefully**.

It could give you explicit document relationships without needing to infer everything from text.

---

# 3. Analyze document length distribution

This is one of the first statistics I'd calculate.

For every document:

```text
document_id
pages
characters
words
tokens
```

Then look at the distribution.

You might discover something like:

```text
Very short
██████████████

Medium
████████████████████████

Long
████████

Extremely long
██
```

The important question isn't merely:

> “How long are the documents?”

It's:

> **“How uneven are they?”**

Imagine:

```text
80% → < 5 pages
15% → 20–50 pages
5% → 500+ pages
```

That creates a very different retrieval problem.

A 500-page historical report probably shouldn't be treated the same way as a 2-page letter.

---

# 4. Inspect the internal structure of documents

For a sample of short, medium, and very long documents, inspect their structure.

Look for:

```text
Title
Abstract/summary
Sections
Subsections
Paragraphs
Tables
Figures
Footnotes
References
Appendices
```

Especially look for **repeating structural patterns**.

For example:

```text
Document
 ├── Metadata
 ├── Summary
 ├── Main content
 ├── Related events
 └── References
```

If most documents follow this structure, that's extremely useful.

Because later you may discover that:

> The answer is usually in one section, while relationships to other documents are contained in another section.

That would directly influence retrieval.

---

# 5. Analyze the metadata very carefully

This is potentially one of the **highest-value inspection steps**.

Build a metadata table.

Something like:

| Document | Title | Author | Date | Type      | Source    | References |
| -------- | ----- | ------ | ---- | --------- | --------- | ---------- |
| D001     | ...   | ...    | 1942 | Report    | Archive A | D034       |
| D002     | ...   | ...    | 1951 | Letter    | Archive B | D001       |
| D003     | ...   | ...    | 1948 | Newspaper | Archive C | D017       |

Then ask:

### What metadata fields exist?

Possibilities:

* author
* publication date
* event date
* location
* document type
* organization
* source
* collection
* subject
* tags
* citations
* references
* related documents
* document ID
* parent document
* version
* language

---

## Why metadata matters for your competition

Suppose the question asks:

> “What happened to X after the 1948 agreement?”

Semantic similarity alone doesn't necessarily understand:

**after 1948**.

But metadata may contain dates.

Similarly:

> “According to the newspaper reports…”

Document type becomes important.

So metadata could become a **retrieval constraint**, not merely descriptive information.

---

# 6. Investigate document-to-document relationships

This is probably the **most important dataset-specific analysis** for your competition.

Remember your track:

> **Connecting Facts Across Thousands of Pages**

So we need to understand:

> **How are these pages connected?**

Look for explicit relationships such as:

```text
Document A
   ↓ cites
Document B
```

or:

```text
Document A
   ↓ references
Document C
```

or:

```text
Document A
   ↓ continuation of
Document B
```

or:

```text
Document A
   ↓ about same event as
Document D
```

or even:

```text
Document A
   ↓ mentions
Person X
```

---

# 7. Build a relationship map during inspection

Not implementation yet — just analysis.

Conceptually, create something like:

```text
              D001
             /    \
         cites     mentions
          /          \
        D034       Person X
         |             |
       cites        appears in
         |             |
        D087          D102
```

Then investigate:

### Are relationships explicit?

For example:

```text
related_documents: [D34, D87]
```

That's gold.

### Or implicit?

Perhaps D001 says:

> “As described in the report published by the Royal Council…”

while the actual report is D034.

Then the relationship has to be inferred.

That's considerably harder.

---

# 8. Identify entities across the corpus

Sample documents and look for recurring:

### People

```text
Person A
Person B
Person C
```

### Organizations

```text
Organization X
Organization Y
```

### Places

```text
City A
Kingdom B
Region C
```

### Events

```text
Battle X
Treaty Y
Conference Z
```

### Objects/concepts

```text
Artifact X
Project Y
Policy Z
```

Then ask:

> **How frequently do the same entities appear across different documents?**

For example:

```text
Person X
 ├── D001
 ├── D017
 ├── D044
 ├── D092
 └── D317
```

If this pattern is common, that's evidence that **entity-centric retrieval** may become extremely important.

---

# 9. Look for fragmented facts

This is probably the single most important thing to identify through manual inspection.

Take a hypothetical question:

> “Who succeeded the leader who signed Treaty X?”

The corpus could contain:

### Document A

> Leader John signed Treaty X.

### Document B

> John died in 1852.

### Document C

> William succeeded John in 1852.

No document contains:

> “William succeeded the leader who signed Treaty X.”

The answer exists only after connecting:

```text
Treaty X
   ↓
John
   ↓
death
   ↓
William
```

You want to find **how often this happens in your corpus**.

---

# 10. Categorize fragmentation

I would specifically look for these patterns.

### Type A — Same entity across documents

```text
D1 → Person X
D2 → Person X
D3 → Person X
```

### Type B — Same event across documents

```text
D1 → Event X
D2 → Event X
D3 → Event X
```

### Type C — Relationship split across documents

```text
D1: A → B

D2: B → C

D3: C → D
```

### Type D — Temporal chain

```text
D1: Event in 1940
D2: consequence in 1942
D3: appointment in 1945
```

### Type E — Reference chain

```text
D1 cites D2
D2 cites D3
D3 contains answer
```

### Type F — Alias/name variation

```text
"William Smith"
"W. Smith"
"Smith"
"Lord Smith"
```

This one can cause **massive retrieval problems**.

---

# 11. Look for duplicate information

You specifically mentioned duplicates — excellent instinct.

Duplicates can appear at several levels.

## Exact duplicates

Two documents contain essentially identical text.

```text
D001 ≈ D034
```

---

## Near duplicates

Same article/report with tiny changes:

```text
D001:
"The treaty was signed in 1842."

D034:
"The treaty was formally signed in 1842."
```

---

## Repeated summaries

Many documents may describe the same event.

```text
D1 → Event X
D2 → Event X
D3 → Event X
D4 → Event X
```

This creates a retrieval problem:

> The most frequently repeated fact may not be the most authoritative source.

---

# 12. Investigate source reliability

This is another thing I'd explicitly analyze before RAG.

Imagine you find:

```text
Official Archive
Newspaper
Personal diary
Anonymous report
Later historical analysis
```

They may all discuss the same event.

But they shouldn't necessarily have equal evidential weight.

Create a source taxonomy.

For example:

| Source type         | Possible characteristics           |
| ------------------- | ---------------------------------- |
| Official record     | High authority for official events |
| Contemporary report | Valuable but potentially biased    |
| Newspaper           | Potentially incomplete/bias        |
| Personal account    | First-hand but subjective          |
| Later analysis      | Useful synthesis                   |
| Unknown             | Lower confidence                   |

I'm deliberately saying **“possible”** here — don't assign reliability scores until you've actually inspected the corpus and competition expectations.

---

# 13. Look for conflicting facts

Find examples where documents disagree.

For example:

```text
D001:
Event happened in 1842.

D057:
Event happened in 1843.
```

Or:

```text
D003:
Person X founded Organization Y.

D091:
Person Z founded Organization Y.
```

You need to understand:

> Is this actual contradiction, different interpretations, or different contexts?

This matters because eventually your QA system may retrieve both.

---

# 14. Check temporal patterns

Historical/archival corpora can be particularly sensitive to time.

Inspect whether documents contain:

* publication dates
* event dates
* date ranges
* approximate dates
* relative dates
* conflicting dates

Examples:

```text
1842
circa 1842
Spring of 1842
three years later
before the treaty
after his appointment
```

These aren't equivalent representations.

If the corpus frequently uses relative temporal language, **temporal reasoning may become a major part of the challenge.**

---

# 15. Look for "important documents"

Not all documents will contribute equally.

You want to discover whether some documents act like **hubs**.

For example:

```text
             D17
              |
       ┌──────┼──────┐
       ↓      ↓      ↓
      D32    D44    D51
       |             |
       ↓             ↓
      D87           D92
```

Maybe D17 is a major historical record referenced by 300 other documents.

That's an extremely important finding.

You could have:

### Hub documents

Many documents reference them.

### Bridge documents

They connect otherwise separate parts of the corpus.

### Leaf documents

Mostly contain information but have few connections.

This gives you an idea of the **topology of the corpus**.

---

# 16. Don't only inspect the most relevant documents

This is an important methodological point.

Your sample should contain:

### Random documents

To understand the general corpus.

### Short documents

To understand simple cases.

### Long documents

To understand difficult retrieval cases.

### Highly referenced documents

To identify hubs.

### Rarely referenced documents

To understand isolated information.

### Documents with rich metadata

To understand available structure.

### Documents with missing metadata

To understand robustness requirements.

### Documents from different source types

To understand reliability.

---

# 17. Create a dataset profiling report

Before implementing anything, I'd want your team to produce a report with approximately these sections:

```text
ASHEN ERA ARCHIVE
DATASET PROFILING REPORT

1. Corpus Overview
2. File Formats
3. Document Counts
4. Document Length Distribution
5. Metadata Analysis
6. Document Structure
7. Entity Distribution
8. Document Relationships
9. Duplicate Analysis
10. Source Analysis
11. Temporal Patterns
12. Fragmented Facts
13. Contradictions
14. Hub / Important Documents
15. Retrieval Risks
16. Initial Design Implications
```

Notice the last section is **not a solution design**.

It should simply say things like:

> “Entity names frequently vary across documents.”

or:

> “Long documents contain multiple unrelated sections.”

Those are **observations**, not implementation decisions.

---

# 18. A practical inspection workflow

I'd do it in this order.

### Phase 1 — Corpus inventory

Answer:

```text
How many?
What formats?
How large?
What metadata?
```

↓

### Phase 2 — Structural profiling

Answer:

```text
How are documents organized?
How long?
What sections?
How much text?
```

↓

### Phase 3 — Relationship discovery

Answer:

```text
How do documents connect?
Explicit references?
Shared entities?
Shared events?
Citations?
```

↓

### Phase 4 — Information fragmentation

Answer:

```text
Are facts distributed?
How many hops?
What types of chains?
```

↓

### Phase 5 — Noise analysis

Answer:

```text
Duplicates?
Near duplicates?
Boilerplate?
Contradictions?
Low-quality sources?
```

↓

### Phase 6 — Retrieval risk analysis

Only now ask:

```text
What could make retrieval fail?
```

---

# 19. The findings I would consider "red flags"

While inspecting, keep a dedicated **retrieval risk log**.

For example:

| Finding                          | Why it matters                             |
| -------------------------------- | ------------------------------------------ |
| Same entity has many aliases     | Entity retrieval can fail                  |
| Huge documents                   | Chunking/retrieval becomes difficult       |
| Many near duplicates             | Retriever may over-rank repeated facts     |
| Important facts only appear once | Recall becomes critical                    |
| References form chains           | Citation traversal may matter              |
| Lots of temporal information     | Time-aware reasoning needed                |
| Contradictory sources            | Evidence verification needed               |
| Poor metadata                    | Can't rely heavily on metadata             |
| Scanned PDFs                     | OCR quality becomes critical               |
| Tables contain key facts         | Plain text extraction may lose information |
| Same event described differently | Semantic retrieval challenge               |
| Hub documents                    | Potentially important retrieval nodes      |
| Facts split across 3+ documents  | Genuine multi-hop requirement              |

---

# 20. One particularly important analysis: answer-path reconstruction

Before building the system, I'd manually take perhaps **20–50 representative questions** from the competition material, if available, and do something very specific.

For each question, manually record:

```text
Question
   ↓
Required fact 1
   ↓
Document X
   ↓
Required fact 2
   ↓
Document Y
   ↓
Required fact 3
   ↓
Document Z
   ↓
Answer
```

Then classify the question:

```text
Single-hop
2-hop
3-hop
4+ hop
Entity resolution
Temporal
Comparison
Aggregation
Cross-source
```

This will tell you far more about the real problem than generic RAG discussions.

---

# 21. The key dataset questions your team should answer

By the end of inspection, you should be able to answer these:

### Corpus

**1. How many documents are there?**

**2. What formats are they in?**

**3. How large are they?**

---

### Structure

**4. Are documents internally structured?**

**5. Are sections/headings meaningful?**

**6. Are tables, images, footnotes, or references important?**

---

### Metadata

**7. What metadata exists?**

**8. Is metadata reliable and complete?**

**9. Does metadata encode relationships?**

---

### Relationships

**10. How do documents connect?**

**11. Are connections explicit or implicit?**

**12. Are there hub/bridge documents?**

---

### Information

**13. How often is information duplicated?**

**14. How often is information fragmented?**

**15. How many hops are typically required?**

---

### Entities

**16. Are entities consistently named?**

**17. Are aliases common?**

**18. Are ambiguous entities common?**

---

### Reliability

**19. Are sources of different authority mixed together?**

**20. Are there contradictions?**

---

### Retrieval

**21. What makes the correct document hard to find?**

**22. Can the answer be found through semantic similarity alone?**

**23. Does finding one document help discover the next one?**

**24. Are there documents that are critical but rarely mentioned?**

---

# 22. And then the architecture decision becomes much easier

Imagine your inspection produces:

### Finding A

> 70% of multi-hop questions follow explicit document references.

That strongly favors **reference-aware/graph-assisted retrieval**.

---

### Finding B

> Most relationships are implicit through shared entities.

That suggests **entity-centric retrieval / graph construction**.

---

### Finding C

> Documents are mostly short and highly interconnected.

A **lightweight iterative RAG** approach may be sufficient.

---

### Finding D

> Many questions require 3–5 hops and there are huge numbers of distractor documents.

You probably need much stronger **path selection/search mechanisms**.

---

### Finding E

> Most answers exist in two or three highly relevant passages, but finding the second passage is difficult.

That points toward **iterative retrieval + reranking**, rather than immediately building a huge graph.

---

### Finding F

> There are many conflicting sources.

Then **evidence provenance and source-aware reasoning** become first-class requirements.

---

## The big picture

Right now, **don't ask:**

> “Which vector database should we use?”

or:

> “Should we use LangChain/LlamaIndex?”

or:

> “Which embedding model is best?”

Those are implementation questions.

Your current question should be:

> **“What structure does the Ashen Era Archive naturally contain, and what properties make the required evidence chains difficult to retrieve?”**

Once you've answered that empirically, you'll have a much stronger basis for choosing between:

```text
                 Ashen Era Archive
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
     Iterative RAG   Graph + RAG   Path Search
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                  Competition QA
```

And importantly, **the dataset itself should decide which branch wins**, not the fact that one architecture sounds more sophisticated.

If you can provide the **Ashen Era Archive files (or a directory/file listing)**, the next useful step would be to perform this profiling systematically and produce a **dataset-inspection report with actual counts, distributions, relationship patterns, and examples**—still without implementing the RAG system.

Prompt 4 - mplement a simple baseline RAG pipeline for our archive using existing document chunks and FAISS index. Keep the implementation modular and do not add multi hop reasoning yet. We want the baseline so we can evaluate its weakness before improving it

Yep — now that you’ve uploaded the actual **chunks + FAISS index**, we can build the baseline properly rather than guessing. I inspected both files first.

### What we have

* **2,487 document chunks**
* **255 source documents**
* JSONL fields:
  `chunk_id`, `source`, `path`, `type`, `page`, `chunk_index`, `text`
* FAISS index contains **2,487 vectors**
* FAISS vector dimension is **384**
* The chunk IDs align with the index positions `0 → 2486`
* The index is an inner-product/`IndexFlatIP`-style FAISS index.

So the baseline is:

```text
                    SIMPLE BASELINE RAG

Question
   │
   ▼
Embedding Model
   │
   ▼
Existing FAISS Index
   │
   │ Top-K
   ▼
Retrieved Chunks
   │
   ▼
Context Builder
   │
   ▼
LLM
   │
   ▼
Answer + Evidence + Retrieval Scores
```

**No multi-hop. No agents. No graph. No query decomposition. No iterative retrieval.**

### Modular implementation

I created:

```text
ashen_baseline_rag/
│
├── config.py          # configuration
├── retriever.py       # FAISS + embedding retrieval
├── context.py         # retrieved-context construction
├── generator.py       # LLM answer generation
├── rag.py             # pipeline orchestration
├── main.py            # CLI entry point
├── evaluate.py        # Recall@K / MRR evaluation
├── requirements.txt
├── .env.example
└── README.md
```

### Download the implementation

[Download the Ashen Era baseline RAG](sandbox:/mnt/data/ashen_baseline_rag.zip)

I also saved it to your Library as `/ashen_baseline_rag.zip`.

### One important thing before running

The FAISS index is **384-dimensional**. I set the default embedding model to:

```text
sentence-transformers/all-MiniLM-L6-v2
```

because it produces 384-dimensional embeddings.

**But we should verify that this is the exact embedding model that was originally used to create your FAISS index.** Dimension matching alone doesn't guarantee semantic compatibility. If your teammate used a different 384-dimensional model, we need to change `EMBEDDING_MODEL` to that exact model.

### How we'll evaluate the baseline

This is actually the important part of this phase.

For example, suppose a question requires:

```text
Question
   │
   ├── Chunk 142 → Fact A
   │
   └── Chunk 981 → Fact B
             ↓
          Answer
```

Our baseline does only:

```text
Question
   ↓
FAISS
   ↓
Top 5 chunks
   ↓
LLM
```

So we'll record cases like:

| Failure            | What happened                                                |
| ------------------ | ------------------------------------------------------------ |
| Retrieval failure  | Required chunk wasn't retrieved                              |
| Ranking failure    | Required chunk exists but wasn't in Top-K                    |
| Generation failure | Evidence was retrieved but answer was wrong                  |
| Multi-hop failure  | One fact retrieved, connected fact missing                   |
| Context failure    | Relevant evidence retrieved but context was poorly assembled |

That gives us **evidence for what to improve next**, instead of immediately throwing GraphRAG/agents at the problem.

One limitation: I could validate the uploaded JSONL and inspect the FAISS file structure here, but the execution environment doesn't currently have `faiss-cpu` or `sentence-transformers` installed, so I couldn't perform a live retrieval query against the index. The implementation itself is syntax-checked and ready for an environment with those dependencies installed.

**Next step should be running ~10–20 representative archive questions through this baseline and analyzing exactly where it fails.** That's where we'll discover whether our first upgrade should be better retrieval, reranking, query expansion, or actual multi-hop reasoning.


Prompt 5 - Our baseline retrieves information about Ederon Fellgard but cannot connect him to the faction and then to the relevant accord. We believe this is a multi hop retrieval problem and have decided to investigate query expansion. Explain how a two hop retrieval approach could solve this while keeping FAISS as the underlying vector search system.

Exactly. The important insight is that **FAISS itself doesn't need to change**. The weakness is that we're currently doing only **one semantic retrieval operation**, while the answer requires following a relationship:

> **Ederon Fellgard → faction → accord**

A two-hop approach can keep FAISS as the retrieval engine and add a small reasoning/query-expansion layer *between* retrieval calls.

## 1. Why the current baseline fails

Your current pipeline is essentially:

```text
Question
   ↓
Embed question
   ↓
FAISS
   ↓
Top-K chunks
   ↓
LLM
   ↓
Answer
```

Suppose the question is something like:

> "What accord was associated with the faction that Ederon Fellgard belonged to?"

The embedding for the whole question may strongly retrieve chunks mentioning:

```text
Ederon Fellgard
```

But the relevant evidence might be distributed:

```text
Document A
"Ederon Fellgard was a prominent member of the
Ashen Vanguard..."

             ↓

Document B
"The Ashen Vanguard signed the
Accord of ..."
```

The first FAISS search finds **Ederon Fellgard**, but there may be little semantic similarity between:

```text
"Ederon Fellgard"
```

and

```text
"Accord of ..."
```

That's the gap we need to bridge.

---

# 2. The two-hop idea

Instead of asking FAISS to solve the entire question at once:

```text
Question → FAISS → Answer
```

we perform:

```text
Question
   ↓
HOP 1
   ↓
Find Ederon Fellgard
   ↓
Extract faction
   ↓
HOP 2
   ↓
Search for that faction + accord
   ↓
Retrieve relevant evidence
   ↓
Answer
```

So FAISS remains the underlying search system.

The **query changes between hops**.

---

# 3. Hop 1 — retrieve the initial entity

Start with the original question:

> "What accord was associated with the faction that Ederon Fellgard belonged to?"

Generate the initial query:

```text
"Ederon Fellgard faction affiliation"
```

Then:

```text
q1 = embed("Ederon Fellgard faction affiliation")

results1 = FAISS.search(q1, top_k=5)
```

FAISS might return:

```text
Chunk 142
"Ederon Fellgard rose to prominence within
the Ashen Vanguard..."

Chunk 317
"Fellgard served as a commander of the
Ashen Vanguard..."

Chunk 891
"...Ederon Fellgard..."
```

Now we've found the first piece:

```text
Ederon Fellgard
        ↓
Ashen Vanguard
```

---

# 4. The crucial step: query expansion

This is where your investigation becomes interesting.

We don't simply send the original question to FAISS again.

We **expand the query using information discovered in Hop 1**.

Original:

```text
Ederon Fellgard
```

Discovered:

```text
Ashen Vanguard
```

So construct a new query:

```text
"Ashen Vanguard accord agreement treaty"
```

or potentially:

```text
"Ashen Vanguard accord"
```

Then embed this new query:

```text
q2 = embed(
    "Ashen Vanguard accord agreement treaty"
)

results2 = FAISS.search(q2, top_k=5)
```

Now FAISS is searching for the **second relationship** rather than trying to solve the entire question.

---

# 5. What the complete process looks like

For your Ederon example:

```text
                    USER QUESTION
                         │
                         ▼
       "What accord was associated with
        the faction Ederon belonged to?"
                         │
                         ▼
                 ┌─────────────┐
                 │   HOP 1     │
                 │    FAISS    │
                 └──────┬──────┘
                        │
                        ▼
              Ederon Fellgard
                        │
                 extract relationship
                        │
                        ▼
                Ashen Vanguard
                        │
                        ▼
                 ┌─────────────┐
                 │   HOP 2     │
                 │    FAISS    │
                 └──────┬──────┘
                        │
                        ▼
             Ashen Vanguard + accord
                        │
                        ▼
                  Relevant chunks
                        │
                        ▼
                ┌─────────────┐
                │     LLM     │
                └──────┬──────┘
                       │
                       ▼
                    ANSWER
```

That's essentially **iterative retrieval with query expansion**.

---

# 6. Where does the query expansion come from?

There are several levels of sophistication.

### Approach A — LLM-generated expansion

After Hop 1, give the retrieved chunks to the LLM:

```text
Question:
What accord was associated with the faction
that Ederon Fellgard belonged to?

Evidence:
"Ederon Fellgard was a senior member
of the Ashen Vanguard..."

Task:
Identify the entity discovered that could help
answer the question.
```

LLM produces:

```text
Ashen Vanguard
```

Then:

```text
"Ashen Vanguard accord"
```

is sent to FAISS.

This is probably the **easiest first experiment**.

---

# 7. Approach B — Entity extraction

Instead of asking the LLM to generate an entire query, explicitly extract entities and relationships.

Hop 1 gives:

```json
{
  "entity": "Ederon Fellgard",
  "relationship": "member_of",
  "target": "Ashen Vanguard"
}
```

Then construct:

```text
Ashen Vanguard accord
```

This is more controlled.

The architecture becomes:

```text
FAISS
 ↓
Retrieved chunks
 ↓
Entity/relationship extraction
 ↓
Query builder
 ↓
FAISS
```

This is particularly attractive for your competition because you're trying to understand **connections between facts**, rather than just generate more natural-language queries.

---

# 8. Approach C — Generate multiple expanded queries

We don't have to trust one expansion.

Suppose Hop 1 discovers:

```text
Ashen Vanguard
```

Instead of generating only:

```text
"Ashen Vanguard accord"
```

generate:

```text
"Ashen Vanguard accord"
"Ashen Vanguard treaty"
"Ashen Vanguard agreement"
"Ashen Vanguard signed"
```

Run each through FAISS:

```text
                  Ashen Vanguard
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
       accord        treaty       agreement
          │             │             │
        FAISS          FAISS         FAISS
          │             │             │
          └─────────────┼─────────────┘
                        ↓
                 combine results
                        ↓
                     rerank
```

This is **query expansion**, but it introduces another important design decision: how many expanded queries should we allow?

For your first experiment, I'd keep it small — perhaps **2–3 expansions**.

---

# 9. We should distinguish query expansion from multi-hop reasoning

This is important for your project.

They're related, but not identical.

### Simple query expansion

```text
Question
 ↓
Generate alternative queries
 ↓
FAISS
 ↓
Combine results
```

The searches are essentially independent.

### Two-hop retrieval

```text
Question
 ↓
FAISS
 ↓
Discover entity/fact
 ↓
Use discovered fact
 ↓
Generate new query
 ↓
FAISS
```

The second search **depends on the result of the first search**.

That's much closer to your actual problem.

For Ederon:

```text
Hop 1:
Ederon → Ashen Vanguard

Hop 2:
Ashen Vanguard → Accord
```

The second query literally cannot be constructed correctly until we discover the faction.

---

# 10. How I'd modify your existing baseline

Your current modular architecture was:

```text
retriever.py
context.py
generator.py
rag.py
```

We don't need to throw it away.

I'd extend it to:

```text
baseline_rag/
│
├── config.py
│
├── retriever.py
│       └── FAISS retrieval
│
├── query_expander.py
│       └── creates next-hop queries
│
├── hop_controller.py
│       └── manages Hop 1 → Hop 2
│
├── context.py
│       └── combines evidence
│
├── generator.py
│       └── final answer
│
├── rag.py
│       └── overall pipeline
│
└── evaluate.py
```

The important architectural change is:

```text
retriever
      ↑
      │
query_expander
      ↑
      │
hop_controller
```

---

# 11. Very simple pseudocode

The first experimental version can be surprisingly simple:

```python
def two_hop_rag(question):

    # ----------------
    # HOP 1
    # ----------------
    query_1 = question

    chunks_1 = retriever.search(
        query_1,
        top_k=5
    )

    # Extract useful entity/relationship
    intermediate = query_expander.extract_entity(
        question,
        chunks_1
    )

    # Example:
    # intermediate = "Ashen Vanguard"

    # ----------------
    # HOP 2
    # ----------------
    query_2 = query_expander.create_query(
        question,
        intermediate
    )

    chunks_2 = retriever.search(
        query_2,
        top_k=5
    )

    # ----------------
    # FINAL ANSWER
    # ----------------
    evidence = chunks_1 + chunks_2

    answer = generator.answer(
        question,
        evidence
    )

    return answer
```

Notice something important:

**FAISS hasn't changed at all.**

We're simply calling:

```python
retriever.search(...)
```

twice.

---

# 12. What we should log

For the competition, don't just return the answer.

Log the entire retrieval chain.

For example:

```json
{
  "question": "What accord was associated with the faction Ederon Fellgard belonged to?",

  "hop_1": {
    "query": "Ederon Fellgard faction affiliation",
    "chunks": [
      "chunk_142",
      "chunk_317",
      "chunk_891"
    ],
    "discovered_entity": "Ashen Vanguard"
  },

  "hop_2": {
    "query": "Ashen Vanguard accord",
    "chunks": [
      "chunk_1042",
      "chunk_1177",
      "chunk_1291"
    ]
  },

  "final_answer": "...",

  "evidence": [
    "chunk_142",
    "chunk_1042"
  ]
}
```

This will be **extremely useful for your experiments**.

You'll be able to see:

```text
Did Hop 1 work?
        ↓
Did we identify the correct faction?
        ↓
Did Hop 2 retrieve the correct accord?
        ↓
Did the LLM connect the evidence?
```

---

# 13. The biggest danger: error propagation

Two-hop retrieval isn't automatically better.

Consider:

```text
Ederon Fellgard
       ↓
WRONG faction
       ↓
WRONG query
       ↓
WRONG accord
```

That's a classic cascading error.

So we should **not blindly trust Hop 1**.

Instead, retain the top few candidate entities.

For example:

```text
Hop 1

Ederon Fellgard
      │
      ├── Ashen Vanguard     0.82
      ├── Fellgard Legion    0.61
      └── Northern Pact      0.42
```

Then potentially run:

```text
Ashen Vanguard accord
Fellgard Legion accord
Northern Pact accord
```

and rank the resulting evidence.

That's a primitive form of **beam search**.

But I wouldn't implement that immediately.

---

# 14. Your experimental progression should be controlled

I'd recommend testing these versions separately:

### Baseline 0

```text
Question
 ↓
FAISS
 ↓
Top-K
 ↓
LLM
```

You already have this.

### Experiment 1 — Two-hop, single expansion

```text
Question
 ↓
FAISS
 ↓
Entity extraction
 ↓
Expanded query
 ↓
FAISS
 ↓
LLM
```

This should be your **first experiment**.

### Experiment 2 — Two-hop + multiple expansions

```text
Question
 ↓
FAISS
 ↓
Entity
 ↓
Query 1 ── FAISS
Query 2 ── FAISS
Query 3 ── FAISS
 ↓
Merge/rank
 ↓
LLM
```

### Experiment 3 — Two-hop + reranking

```text
FAISS
 ↓
Candidate chunks
 ↓
Reranker
 ↓
Best evidence
```

### Experiment 4 — Variable-hop retrieval

Only after you've established that two-hop retrieval actually helps:

```text
Hop 1
 ↓
Hop 2
 ↓
Is evidence sufficient?
 ↓ NO
Hop 3
 ↓
Is evidence sufficient?
 ↓ YES
Answer
```

**Don't jump to Experiment 4 yet.**

---

# 15. What we should measure

This is where your project becomes scientifically convincing.

Compare:

| Metric                      | Baseline | Two-hop |
| --------------------------- | -------: | ------: |
| Answer accuracy             |        ? |       ? |
| Recall@5                    |        ? |       ? |
| Recall@10                   |        ? |       ? |
| MRR                         |        ? |       ? |
| Correct intermediate entity |        — |       ? |
| Correct second-hop evidence |        — |       ? |
| Latency                     |        ? |       ? |
| Number of FAISS searches    |        1 |       2 |

Especially measure:

### Hop-1 success

> Did we identify the correct intermediate entity?

### Hop-2 success

> Given the correct intermediate entity, did FAISS retrieve the evidence needed for the final answer?

### End-to-end success

> Did the system produce the correct answer?

This lets you diagnose whether the problem is:

```text
        ┌─ Hop 1 retrieval failure
        │
Question┼─ Query expansion failure
        │
        ├─ Hop 2 retrieval failure
        │
        └─ Generation failure
```

That's much more informative than simply saying **"RAG accuracy improved by 8%."**

---

## The key idea

The elegant part of this approach is that **we don't need to replace FAISS**.

We're changing:

```text
ONE-SHOT RETRIEVAL

Question
   ↓
FAISS
   ↓
Answer
```

into:

```text
DEPENDENT RETRIEVAL

Question
   ↓
FAISS
   ↓
Intermediate fact
   ↓
Query expansion
   ↓
FAISS
   ↓
Second fact
   ↓
LLM
   ↓
Answer
```

For your archive, that gives us a very clean hypothesis to test:

> **Can information discovered from the first retrieval be used to formulate a better second retrieval query, allowing FAISS to recover evidence that direct retrieval misses?**

If the answer is **yes**, you've demonstrated that the baseline's weakness is genuinely related to multi-hop retrieval—and then we have a strong empirical reason to move toward more sophisticated multi-hop mechanisms.

Prompt 6 - we have decided to implement a multi hop text pipeline. The first hop, should retrieve evidence for the original question, then identify entities, relationships that require additional investigation. Generate targeted follow up queries, retrieve additional evidence, and finally provide the combined evidence to the LLM. Implement this as a separate module so we can compare it against our baseline.

Yes — this is the right next experiment. I implemented the **two-hop multi-hop pipeline as a separate module**, while keeping your existing baseline untouched.

The implementation is based on the structure of your current baseline: the existing FAISS retriever, JSONL chunks, embedding model, and LLM generator remain the same. 

### New architecture

```text
                    QUESTION
                       │
                       ▼
              ┌────────────────┐
              │    HOP 1       │
              │ Existing FAISS │
              └───────┬────────┘
                      │
                      ▼
              First-hop evidence
                      │
                      ▼
              ┌────────────────┐
              │ Query Expander │
              │                │
              │ Entities       │
              │ Relationships  │
              │ Missing facts  │
              └───────┬────────┘
                      │
                      ▼
             Targeted queries
                ┌─────┼─────┐
                ▼     ▼     ▼
              FAISS FAISS FAISS
                └─────┼─────┘
                      ▼
              ┌────────────────┐
              │   Combined     │
              │   Evidence     │
              └───────┬────────┘
                      ▼
                     LLM
                      │
                      ▼
                    ANSWER
```

For your Ederon example:

```text
Ederon Fellgard
       │
       │ Hop 1
       ▼
"Ashen Vanguard"
       │
       │ query expansion
       ▼
"Ashen Vanguard accord"
       │
       │ Hop 2
       ▼
Relevant accord evidence
       │
       ▼
     Answer
```

### What I added

The new module contains:

* `multihop.py`

  * `QueryExpander`
  * `MultiHopRAG`
  * two-hop orchestration
* `multihop_main.py`

  * separate CLI entry point
* `README_MULTIHOP.md`

  * architecture and evaluation methodology

The original baseline modules are retained, so you can make a clean comparison.

### Important design choice

I deliberately limited it to **two hops**.

There is **no**:

* Hop 3
* recursive agent loop
* graph database
* graph traversal
* new vector index
* autonomous searching

The second retrieval is driven entirely by information discovered during Hop 1.

The query-expansion LLM is instructed to return:

```json
{
  "entities": [],
  "relationships": [],
  "follow_up_queries": []
}
```

and at most **3 targeted follow-up queries** are generated.

### Run it

```bash
python multihop_main.py "YOUR QUESTION" --top-k 5 --max-follow-ups 3
```

The output records the entire chain:

```text
question
    ↓
hop_1
    ↓
entities
relationships
follow_up_queries
    ↓
hop_2
    ↓
combined_evidence
    ↓
answer
```

That logging is especially important because we want to know **why** the system improved, not merely whether it improved.

### Compare against the baseline

Your baseline is:

```text
Question
   ↓
FAISS
   ↓
Top-K
   ↓
LLM
```

The experiment is now:

```text
                    BASELINE
                       │
                Question → FAISS → LLM
                       │
                       │
                    COMPARE
                       │
                       ▼
                   MULTI-HOP
                       │
       Question → FAISS → Entity/Relation
                              ↓
                         New Query
                              ↓
                            FAISS
                              ↓
                       Combined Evidence
                              ↓
                             LLM
```

For your gold questions, I'd specifically track:

| Metric                       | Baseline | Multi-hop |
| ---------------------------- | -------: | --------: |
| Answer accuracy              |          |           |
| Hop-1 Recall@K               |          |           |
| Intermediate entity accuracy |        — |           |
| Follow-up query quality      |        — |           |
| Hop-2 Recall@K               |        — |           |
| End-to-end evidence recall   |          |           |
| Latency                      |          |           |
| FAISS searches/question      |        1 |       2–4 |

The **intermediate entity accuracy** and **Hop-2 Recall@K** are particularly valuable. If Ederon → faction succeeds but faction → accord fails, we know the next improvement belongs in the second-hop retrieval/query-generation stage rather than the final LLM.

### Download

[Download the two-hop multi-hop RAG module](sandbox:/mnt/data/ashen_multihop_rag.zip)

I also saved it separately in your Library as `/ashen_multihop_rag.zip`.

One technical point remains the same as the baseline: your supplied FAISS index is 384-dimensional, and the exact embedding model used to build that index should match the model used at query time. 

**The next experiment I'd run is the Ederon Fellgard question through both systems and inspect the complete Hop-1 → expansion → Hop-2 trace.** That will tell us whether query expansion actually bridges the missing faction → accord connection.

Prompt 7 - we observed The correct evidence is being retrieved, but some irrelevant documents are also entering the final evidence set. We are considering four thresholds: deduplication, source diversity, and evidence limits. Compare these approaches and explain their risks, particularly the possibility that filtering by similarity score could remove a less similar chunk containing an important fact.

Yes — this is exactly the **next retrieval-quality problem** you should investigate before adding another layer of reasoning.

Your observation is important:

> **The correct evidence is already being retrieved. The problem is that irrelevant evidence is also surviving into the final evidence set.**

For a multi-hop system, this is especially dangerous because irrelevant chunks can distract the final LLM from the actual evidence chain.

### 1. Compare the four approaches

| Approach                   | Main idea                                                 | Advantage                                                    | Main risk                                                              |
| -------------------------- | --------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------- |
| **Similarity threshold**   | Remove chunks below a score threshold                     | Simple and directly reduces weak matches                     | **Can remove important low-similarity evidence**                       |
| **Deduplication**          | Remove repeated/near-identical chunks or repeated sources | Reduces redundancy without necessarily removing unique facts | May remove useful repeated evidence if deduplication is too aggressive |
| **Source diversity**       | Limit how many chunks come from the same document/source  | Prevents one document from dominating the context            | Can discard multiple genuinely important facts from the same source    |
| **Evidence limit (Top-N)** | Send only a fixed number of chunks to the LLM             | Controls context size and noise                              | Important evidence may fall outside the cutoff                         |

The key point is that **these are not equally risky**.

---

## 2. Similarity threshold — powerful but dangerous

Suppose your retrieval returns:

```text
Chunk A   similarity = 0.91   → directly discusses Ederon Fellgard
Chunk B   similarity = 0.88   → discusses the Ashen Vanguard
Chunk C   similarity = 0.62   → contains the specific Accord connection
Chunk D   similarity = 0.60   → irrelevant historical background
```

If you say:

```text
keep only similarity >= 0.70
```

you get:

```text
A ✓
B ✓
C ✗  ← potentially CRITICAL
D ✗
```

This is the fundamental problem with score-based filtering:

**Similarity measures relevance to the query, not necessarily usefulness for the final reasoning chain.**

In your multi-hop system, this becomes even more important.

The original question might be about:

> Ederon Fellgard + Accord

But the chunk containing the answer might only talk about:

> "The Ashen Vanguard signed the Grey Accord..."

It may not mention **Ederon Fellgard at all**.

Therefore its embedding similarity to the original query can be relatively low.

Yet logically:

```text
Ederon Fellgard
       ↓
Ashen Vanguard
       ↓
Grey Accord
```

That lower-scoring chunk is exactly what you need.

### So I would NOT make similarity thresholding your primary filter.

Use similarity as a **ranking signal**, not a hard deletion rule.

---

# 3. Deduplication — safest first step

Deduplication is much less dangerous.

Imagine Hop 1 returns:

```text
Document A — Chunk 14
Document A — Chunk 15
Document A — Chunk 16
```

and Hop 2 retrieves:

```text
Document A — Chunk 15
Document A — Chunk 16
Document B — Chunk 7
```

You don't need to send the same chunks twice.

Your existing multi-hop implementation already does this at the chunk level.

You can also go one step further with **near-duplicate detection**.

For example:

```text
Chunk A:
"The Ashen Vanguard was formed in 412..."

Chunk B:
"The Ashen Vanguard, formed in 412, ..."
```

These may contain essentially the same information.

### Risk

If you deduplicate too aggressively, you could remove chunks that look similar but contain a **different fact**.

So:

**Exact chunk deduplication → very safe**

**Near-duplicate semantic deduplication → useful, but needs testing**

I'd start with exact `chunk_id` deduplication and only introduce semantic deduplication if redundancy is demonstrably large.

---

# 4. Source diversity — good for reducing dominance

Imagine your Top-10 results are:

```text
Document A: 7 chunks
Document B: 2 chunks
Document C: 1 chunk
```

Even though all seven chunks from A are individually relevant, they could crowd out evidence from B and C.

A source-diversity rule could produce:

```text
Document A: 3
Document B: 3
Document C: 2
Document D: 2
```

This is useful when your questions require **cross-document reasoning**, which your competition task specifically does.

But there's a catch.

Suppose:

```text
Document A contains:
    Fact 1
    Fact 2
    Fact 3
    Fact 4
```

and all four facts are necessary.

A hard rule like:

```text
MAX 2 chunks per source
```

could destroy the evidence chain.

So I wouldn't use:

> "Never retrieve more than X chunks from one source."

Instead, use a **soft diversity preference**.

For example:

```text
First select high-quality evidence.

Then slightly boost underrepresented sources.

Don't automatically delete strong evidence merely because
another chunk comes from the same source.
```

---

# 5. Evidence limits — necessary, but don't make them too aggressive

You eventually need an evidence limit because sending 30–50 chunks to the LLM is inefficient and increases distraction.

For example:

```text
Hop 1: Top-5
Hop 2 Query 1: Top-5
Hop 2 Query 2: Top-5
Hop 2 Query 3: Top-5

Potential evidence = 20 chunks
```

Sending all 20 may be unnecessary.

But:

```text
Top 5 overall
```

could be dangerous.

Why?

Because your evidence isn't necessarily ranked according to **answer importance**.

You could have:

```text
1. Ederon biography        0.93
2. Ederon history          0.91
3. Ederon military career  0.89
4. Ederon birthplace       0.87
5. Accord description      0.65  ← critical
```

The fifth chunk looks weaker semantically but is the missing link.

So a fixed Top-N cutoff has the same fundamental issue:

> **Retrieval relevance ≠ reasoning importance.**

---

# 6. The approach I'd recommend for your project

Don't choose just one threshold.

Use a **conservative evidence-control pipeline**:

```text
                 Hop 1 + Hop 2 results
                         │
                         ▼
                ┌─────────────────┐
                │ Exact Dedup     │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Keep candidate  │
                │ evidence pool   │
                └────────┬────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       Similarity score       Source diversity
        as a ranking             as a preference
              │                     │
              └──────────┬──────────┘
                         ▼
                  Evidence ranking
                         │
                         ▼
                Conservative Top-N
                         │
                         ▼
                       LLM
```

The important change is:

### **Don't use similarity as a hard gate.**

Instead:

```text
similarity = one signal
hop number = another signal
query match = another signal
entity overlap = another signal
source diversity = another signal
```

Then rank the evidence.

---

# 7. Even better for your multi-hop system

Because you **know which evidence came from which hop**, you can exploit that.

For example:

```text
Chunk                    Similarity    Hop
------------------------------------------------
Ederon biography            0.91        1
Ashen Vanguard              0.82        2
Grey Accord                 0.63        2
Random historical event     0.79        1
```

Notice something interesting:

The random historical event has a **higher similarity score** than the Grey Accord.

A pure similarity filter would prefer the random event.

But your multi-hop pipeline knows:

```text
Ederon → Ashen Vanguard → Grey Accord
```

So the Grey Accord chunk has **structural importance**.

This is where your system can eventually become much stronger than ordinary RAG.

---

# 8. I would test the four approaches experimentally

Don't argue theoretically about which one is best. Your competition evaluation should tell you.

Run:

### Experiment A — Baseline

```text
Multi-hop
→ deduplication only
→ all retrieved evidence
```

### Experiment B — Similarity threshold

```text
Multi-hop
→ deduplication
→ similarity threshold
```

Test several thresholds:

```text
0.50
0.60
0.70
0.80
```

Then measure whether **Recall decreases**.

### Experiment C — Source diversity

```text
Multi-hop
→ deduplication
→ source diversity
→ evidence limit
```

Compare against A.

### Experiment D — Evidence limit

Try:

```text
Top 5
Top 8
Top 10
Top 15
Top 20
```

Then measure answer accuracy and evidence recall.

---

# 9. The metric you REALLY want to watch

Don't only measure final answer accuracy.

Track:

### Evidence Recall

> Did the final evidence set still contain **all the chunks required to answer the question?**

This catches the exact failure you're worried about.

Imagine:

```text
Before filtering:

Correct evidence:
✓ Ederon
✓ Ashen Vanguard
✓ Grey Accord

Irrelevant:
✗ War of 417
✗ Northern campaign
```

After similarity filtering:

```text
✓ Ederon
✓ Ashen Vanguard
✗ Grey Accord  ← LOST
✗ War of 417
```

Your evidence precision improved.

But **evidence recall collapsed**.

That's a terrible trade for a multi-hop system.

---

## My recommendation

I'd rank the four techniques like this:

**1. Exact deduplication → implement immediately**
Low risk, removes obvious redundancy.

**2. Evidence limit → implement conservatively**
Useful for context control, but test several values.

**3. Source diversity → use as a soft ranking preference**
Very relevant to your cross-document task, but don't hard-delete same-source evidence.

**4. Similarity threshold → be very careful**
Use it primarily for ranking or very weak-score removal, **not as an aggressive hard cutoff**.

The central principle for your system should be:

> **Optimize for evidence recall first, then reduce redundancy/noise without deleting potentially important low-similarity evidence.**

That's especially important because your task is **connecting facts**, not simply retrieving the most semantically similar paragraphs. A chunk that looks weak in isolation can be the exact bridge that completes the reasoning chain.

Prompt 8 - We have decided to improve the multi-hop pipeline using score filtering, source diversity, deduplication, and a maximum evidence limit. Modify the current implementation rather than replacing the whole architecture. Keep the baseline implementation available so we can compare results.

Done. I **modified the existing multi-hop architecture** rather than replacing it, and kept the original single-pass baseline intact for comparison. The baseline's original design remains the single FAISS retrieval → LLM flow. 

### What was added

The pipeline is now:

```text
Question
   ↓
Hop 1 FAISS
   ↓
Entity / relationship extraction
   ↓
Targeted follow-up queries
   ↓
Hop 2 FAISS
   ↓
Raw combined evidence
   ↓
┌─────────────────────────┐
│ 1. Exact deduplication  │
│ 2. Score filtering      │
│ 3. Source diversity     │
│ 4. Max evidence limit   │
└─────────────────────────┘
   ↓
Filtered evidence
   ↓
LLM
   ↓
Answer
```

### Default configuration

```text
MIN_SCORE = 0.55
MAX_CHUNKS_PER_SOURCE = 3
MAX_EVIDENCE = 12
```

These can all be changed from the CLI or `.env`.

### Important recall protection

I specifically added a safeguard for the issue we discussed:

**The top result from Hop 1 and the top result from every follow-up query are protected from score filtering.**

So if a follow-up query retrieves an important bridge fact with an unexpectedly low similarity score, it isn't automatically thrown away.

The output also now separates:

```text
raw_evidence
        ↓
filtered_evidence
```

and reports:

```text
dedup_removed
score_removed
diversity_removed
limit_removed
output_count
```

That will let you determine **which filter is actually helping or hurting** instead of just looking at final accuracy.

### Comparison experiment

You can now compare:

**Baseline**

```text
Question → FAISS → Top-K → LLM
```

vs.

**Original multi-hop**

```text
Question → Hop 1 → expansion → Hop 2 → LLM
```

vs.

**Improved multi-hop**

```text
Question → Hop 1 → expansion → Hop 2
         → filtering → LLM
```

This is a nice experimental progression because you're changing only the evidence-selection stage, not throwing away the architecture you already tested.

### Download

[Download the updated filtered multi-hop RAG](sandbox:/mnt/data/ashen_multihop_filtered_rag.zip)

I've also saved it as `/ashen_multihop_filtered_rag.zip` in your Library.

**Next thing I'd recommend:** run the same evaluation questions through all three versions and build a small comparison table containing **Answer Accuracy, Raw Evidence Recall, Filtered Evidence Recall, irrelevant-chunk rate, and latency**. That will tell you whether the filtering actually improves the system or merely makes the context smaller.
