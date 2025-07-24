# SIMPLIFICATION_PLAN

## 1. Overview
This document proposes a streamlined architecture for the request→response pipeline by reducing redundancy, consolidating modules, and focusing on four essential components:

1. **Parser**: Converts user requests into a structured `ReqPrompt` and `ResponseObjective`.
2. **Retriever (RAG)**: Fetches relevant context objects (topic, resources, weights) via a unified interface.
3. **Synthesizer**: Generates candidate responses using `ReqPrompt + RAGContext`.
4. **Feedback Loop**: Evaluates output against the `ResponseObjective` and length constraints; retries with minimal adjustments.

Additionally, we recommend a lightweight **Context & History Manager** to track session state, memory, and summarization.

---

## 2. Current Complexity
- Multiple RAG backends (Chroma, Pinecone, HuggingFace, Simple, Enhanced): duplication of interface code
- Redundant YAML data schemas and folders (e.g., `data_old`, `data/projects` vs. `modules/rag_*` loader logic)
- Overly generic `content_processor` and `enhanced_cross_reference_integrator`
- Complex weighting logic scattered across modules
- No unified feedback/evaluation layer; retry loops embedded in synthesizer clients
- History & memory management ad hoc (session_meta.yaml, tutorials, UI state)

---

## 3. Simplification Goals
1. **Consolidate**: One RAG retriever interface with selectable plugin drivers.
2. **Isolate**: Clear separation between parsing, retrieval, generation, and evaluation.
3. **Minimize**: Remove unused modules, tests, and legacy folders (`data_old`, redundant integrators).
4. **Standardize**: Single YAML structure for prompts, context definitions, and resource metadata.
5. **Formalize**: A concise feedback loop layer with configurable thresholds.
6. **Manage**: A slim ContextManager for sliding-window history and memory summary.

---

## 4. Essential Components

### 4.1 Parser Module
- `core/parser.py`
  - Function: `parse_request(text) -> (ReqPrompt, ResponseObjective)`
  - Keep minimal: NLP logic or regex; no cross-reference logic.

### 4.2 Retriever Interface
- Single `core/rag.py` with:
  - `retrieve(query, top_k, weights) -> List[RAGContext]`
  - Plugin drivers under `core/rag/drivers` (e.g., `simple.py`, `chroma.py`).
  - Default: `simple` or `chroma` driver.

### 4.3 Synthesizer Module
- `core/synthesizer.py`
  - Function: `generate(prompt, contexts) -> CandidateResponse`
  - Stateless, pure LLM invocation.

### 4.4 Feedback Loop
- New `core/evaluator.py`:
  - `evaluate(response, objective, length_limit) -> Score` (0–1)
  - `retry(prompt, contexts, feedback)`: adjusts `prompt` and regenerates up to N attempts.

### 4.5 Context & History Manager
- `core/context_manager.py`
  - Sliding-window storage for recent turns.
  - Periodic summarization of older history via LLM.
  - API: `get_history()`, `add_turn(turn)`, `summarize_old()`.

---

## 5. Implementation Steps

1. **Audit & Prune**
   - Delete legacy folders: `/data_old`, unused integrators, and redundant tests.
   - Remove obsolete docs: `KNOWLEDGE_GRAPH_ARCHITECTURE.md`, `ENHANCED_*`, etc.

2. **Define Core Interfaces**
   - Create `modules/core/` folder.
   - Draft base classes for Parser, Retriever, Synthesizer, Evaluator, ContextManager.

3. **Refactor Parser**
   - Move `modules/parser.py` to `core/parser.py`.
   - Strip cross-reference code; update tests.

4. **Consolidate RAG**
   - Implement `core/rag.py` with driver factory.
   - Move `modules/rag_simple.py` and `modules/rag_chroma.py` under `core/rag/drivers/`.
   - Update `data_loader.py` and `import_data_to_rag.py` to use new API.

5. **Simplify Synthesizer**
   - Consolidate `modules/synthesizer.py` into `core/synthesizer.py`.
   - Remove cross-reference variants.

6. **Implement Evaluator**
   - Create `core/evaluator.py` with objective & length checks.
   - Add retry orchestration.

7. **Build Context Manager**
   - Create `core/context_manager.py`.
   - Integrate with memory extension for persistent state.

8. **Orchestrate in App**
   - Update `app.py` to: parse → retrieve → generate → evaluate → respond.

9. **Testing**
   - Update existing tests to reference `core/` modules.
   - Write tests for evaluator and context_manager.

10. **Documentation**
   - Add architecture overview to `README.md`.
   - Archive old design docs.
   - Reference `SIMPLIFICATION_PLAN.md` in project root.

---

## 6. Context & History Recommendations
- **Sliding Window**: Keep last N turns in context (e.g., 6).  
- **Summarization**: Summarize every M turns (e.g., 10) and drop older details.  
- **Long-term Memory**: Use Goose memory extension for persistent user preferences.  
- **Stateless Core**: Limit state to ContextManager; modules remain pure.

---

*End of Plan*