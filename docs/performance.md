# Performance Assessment: Start Here Page

## Executive Summary
The Start Here page does substantial work on the initial Streamlit run: it loads and validates the full node dataset, builds multiple derived data structures, hydrates local storage, and then renders a very large interactive list (multiple Streamlit widgets per node) across all categories. With ~1000 nodes, the dominant cost is not a single slow computation but the cumulative overhead of **server-side reruns** and **front-end rendering/serialization** of hundreds to thousands of widgets and columns. This aligns with a 10–30s “page not usable” delay.

The most impactful problems are concentrated in:
- **Rendering the full technology list with per-row widgets and nested columns** (very large UI/DOM + Streamlit widget serialization).
- **Repeatedly rebuilding the visible list view on every rerun**, which is triggered by any widget interaction and by the `st_keyup` input.
- **Initial data model construction and validation**, which are non-trivial but secondary to UI render cost.

The sections below prioritize the most likely causes, then explain the mechanics across Streamlit’s execution model, Python CPU cost, browser cost, and serialization overhead.

## Top 3–5 Likely Causes of the 10–30s Delay (Ordered by Impact)

1. **Full list rendering of ~1000 nodes with multiple widgets and columns per row**
   - **Location**: `terra_invicta_tech_optimizer/streamlit_app/ui/start_page.py`, `render_technology_list()`
   - Impact: Creates 5 Streamlit elements per row (image/markdown/markdown/write/button), plus a `st.columns` container per row and a `st.expander` per category. This yields thousands of UI elements and widget states, which are serialized to the browser on the first run.

2. **Large per-run recomputation + rerun amplification from live search**
   - **Location**: `terra_invicta_tech_optimizer/streamlit_app/ui/start_page.py`, `render_search_box()` and `render_technology_list()`
   - Impact: `st_keyup` triggers a rerun every 300ms while typing; each rerun rebuilds the filtered view and re-renders the entire list, re-serializing large UI payloads.

3. **Initial creation of graph data structures and flat lists**
   - **Location**: `terra_invicta_tech_optimizer/streamlit_app/data.py`, `get_models()`; `terra_invicta_tech_optimizer/planner_data.py`, `build_graph_data()` and `build_flat_node_list()`
   - Impact: O(N log N) sorts and multiple passes across nodes/edges. This cost is paid on first load (and on reload token changes) before the UI is rendered.

4. **Graph validation (cycle + missing reference checks)**
   - **Location**: `terra_invicta_tech_optimizer/validation.py`, `GraphValidator.validate()`
   - Impact: DFS over all nodes/prereqs; usually linear in nodes+edges but still adds pre-render latency in the initial preparation phase.

5. **Backlog hydration/persistence via `streamlit_local_storage` component**
   - **Location**: `terra_invicta_tech_optimizer/streamlit_app/storage.py`, `hydrate_backlog_from_storage()`
   - Impact: The component can spawn iframe-backed communication and can cause extra reruns; the code intentionally retries several times. This can amplify perceived delay before the page “stabilizes.”

## Detailed Findings

### 1) Full Technology List Rendering (Most Likely Primary Bottleneck)
**Code**
- `terra_invicta_tech_optimizer/streamlit_app/ui/start_page.py`, `render_technology_list()`

**What the code does**
- Builds a filtered/sorted view and renders **all visible nodes**.
- For each category, creates a `st.expander(..., expanded=True)` and then loops every visible node, rendering:
  - `st.columns` with 5 sub-elements (image/markdown/markdown/write/button).
  - Per-node button (stateful widget).

**Why it is expensive**
- **Streamlit execution model**: The entire function runs top-to-bottom on each rerun. Any user interaction (typing in search, clicking checkboxes, toggling filters) causes a full rerun and re-render of all rows.
- **Python-side cost**: The loop itself is O(N) with some formatting per row. The computation is moderate, but repeated on every rerun.
- **Browser-side cost**: Thousands of DOM nodes and Streamlit widget wrappers are created. Each `st.columns` produces multiple nested containers. Each `st.button` adds JS event handling and widget state.
- **Serialization cost**: Streamlit sends a large “delta” payload (JSON-ish) to the frontend for each element, which is heavy for thousands of components.

**Why this scales poorly for ~1000 nodes**
- 1000 nodes × 5 row elements + columns + expanders => several thousand UI elements per rerun.
- Widget-heavy UIs (buttons for every row) scale worse than static markdown.

**Typical Streamlit symptoms**
- Long “Running…” spinner before UI appears.
- Browser becomes unresponsive while the UI rehydrates.
- Slow or janky interactions when filtering/searching due to full reruns.

---

### 2) Rerun Amplification from `st_keyup` Live Search
**Code**
- `terra_invicta_tech_optimizer/streamlit_app/ui/start_page.py`, `render_search_box()`

**What the code does**
- Uses `st_keyup` with `debounce=300` to trigger a rerun on each paused keystroke.
- Each rerun updates query params and re-renders the full list.

**Why it is expensive**
- **Streamlit reruns**: Every keystroke (after 300ms) triggers a full rerun, re-building the list and resending the UI payload.
- **Browser-side**: Each rerun replaces large sections of DOM, causing repeated layout/paint.

**Why this scales poorly with ~1000 nodes**
- The cost per rerun grows with list size. With 1000 items, even “fast” keystrokes can keep the page in a continuous render loop.

**Typical Streamlit symptoms**
- Search feels “laggy” or the page freezes while typing.
- Noticeable delay between typing and UI updating.

---

### 3) Initial Graph and Flat List Construction
**Code**
- `terra_invicta_tech_optimizer/streamlit_app/data.py`, `get_models()`
- `terra_invicta_tech_optimizer/planner_data.py`, `build_graph_data()` and `build_flat_node_list()`

**What the code does**
- Builds a sorted list of node IDs, maps them to indices, computes prereq/dependent indices, and builds flattened list views sorted by name and cost.

**Why it is expensive**
- **Python CPU**: Sorting and repeated passes across all nodes and prereqs. For 1000 nodes, this is moderate but not negligible.
- **Streamlit execution model**: This happens on the first load (and on reload token changes). The time adds to pre-render latency before any UI appears.

**Why this scales poorly with ~1000 nodes**
- The cost grows with both node count and number of prereqs, even if it’s still within O(N log N) + O(E).

**Typical Streamlit symptoms**
- Initial render delay even before the UI appears, with a “Running…” indicator.

---

### 4) Graph Validation on Each Start Here Run
**Code**
- `terra_invicta_tech_optimizer/validation.py`, `GraphValidator.validate()`
- Called from `pages/Start_here.py` `main()`

**What the code does**
- Checks missing references and cycles across the full node graph.

**Why it is expensive**
- **Python CPU**: A DFS across all nodes and edges. With 1000 nodes, this can still add milliseconds to seconds depending on prereq density.
- **Execution model**: Validation runs every time the Start Here page executes, adding to the total pre-render work.

**Why this scales poorly with ~1000 nodes**
- Complexity increases with both nodes and edges. Densely connected graphs magnify cost.

**Typical Streamlit symptoms**
- Added “pre-flight” delay before UI renders, even when nothing else changes.

---

### 5) Local Storage Hydration and Persistence
**Code**
- `terra_invicta_tech_optimizer/streamlit_app/storage.py`, `hydrate_backlog_from_storage()`
- Called from `pages/Start_here.py` `main()`

**What the code does**
- Uses `streamlit_local_storage` to read persisted backlog items; retries a few times to avoid component initialization races.

**Why it is expensive**
- **Streamlit model**: Component state can cause additional reruns as it initializes, which can repeat expensive list rendering.
- **Browser-side**: Iframe/component initialization adds overhead and can delay the page settling into a stable state.

**Why this scales poorly with ~1000 nodes**
- If the backlog payload grows large, the JSON encoding/decoding and matching against graph nodes adds additional cost. Repeated reruns multiply the expense.

**Typical Streamlit symptoms**
- Multiple reruns on first load, UI “flicker,” or inconsistent state before stabilizing.

## Best-Practice Guidance (Relevant to This Code)

1. **Stage heavy UI rendering**
   - For large datasets, avoid rendering all rows in a single pass. Streamlit best practice is to stage rendering (e.g., show top results, paginate, or render per category on demand) to reduce initial payload and keep the UI responsive.
   - Streamlit is not optimized for thousands of widgets in one view; limiting the widget count dramatically reduces initial render time and rerun cost.

2. **Cache at meaningful boundaries and minimize rerun scope**
   - `st.cache_data` is already used for input loading, but expensive derived views (e.g., `build_flat_list_view`) still happen on every rerun.
   - In large apps, caching filtered/sorted views (keyed by filters + completion/backlog state) or using `st.session_state` to store prepared views can reduce CPU work and payload changes per rerun.

3. **Reduce widget density in large lists**
   - Buttons for every row are the most expensive part of the list. A best-practice pattern is “select then act” (e.g., a single selection widget with one action button) or lazy rendering for visible rows only.

4. **Prefer incremental or lazy rendering for large UI sections**
   - Rendering 8 expanded `st.expander` blocks with all items expands the total DOM and JS workload. Streamlit’s UI performance is better when expanders are collapsed by default or when the list is paged.

5. **Avoid reruns for transient input when possible**
   - Live search is user-friendly but can cause repeated full reruns. In Streamlit, batching user input (e.g., explicit “Apply” or using `st.form` submissions) is a common pattern to reduce rerun thrash in large UIs.

## Quick Diagnostic Suggestions (Optional)

If you want to confirm which stages dominate the 10–30s delay, these low-effort measurements are likely to be high-signal:

- **Add timing logs around key blocks in `pages/Start_here.py`**
  - e.g., measure `load_inputs`, `get_models`, `validate_graph`, and `render_technology_list` separately.
- **Add a counter to detect rerun loops**
  - Increment a `st.session_state.run_count` to see if the page is rerunning multiple times due to local storage hydration or widget interactions.
- **Measure UI payload size**
  - Use browser dev tools to inspect the websocket traffic size on initial load; large payloads typically correlate with heavy widget/DOM rendering.
- **Profile the Python loop in `build_flat_list_view`**
  - Quick profiling (e.g., `cProfile` or `time.perf_counter`) can confirm whether filtering is significant or dwarfed by UI serialization.

## Brainstorming: Streamlit-Friendly Solutions (and How They Compare to React)

### Would React handle 1000 rows better?
React (or any virtual-DOM framework) can render 1000 rows more smoothly **if** it uses:
- **Virtualization** (only render visible rows).
- **Client-side state updates** without a full server rerun.

However, Streamlit’s architecture is fundamentally different: each UI change reruns Python and re-serializes UI deltas. Even if you embed a React component, you still pay the initial Python-side preparation cost unless you move more logic client-side. React helps if you:
- Replace the entire list with a **custom component** that handles filtering/sorting in the browser.
- Limit Streamlit’s role to serving a single, static payload and receiving only minimal interaction updates.

### Would Streamlit tables/dataframes help?
Yes, **if you can accept a more tabular UI** and reduce per-row widgets:
- `st.dataframe` is optimized for large tables and uses client-side rendering with fewer widget states.
- You lose per-row `st.button` actions, but you can use row selection + a single “Add to backlog” action button, which reduces widget count dramatically.
- `st.data_editor` supports selection and editing but can introduce its own overhead if heavily styled or if you rely on per-cell widgets.

### Streamlit-native approaches likely to improve responsiveness
These are “Streamlit way” patterns that reduce reruns and widget density without leaving the framework:

1. **Pagination or incremental rendering**
   - Render only one category at a time, or page results in chunks (e.g., 50–100 rows).
   - Streamlit’s rerun cost scales with visible widgets; fewer widgets = faster first render.

2. **On-demand expanders**
   - Collapse categories by default and render the list only when a category is expanded.
   - This defers work and gives the user a responsive page faster.

3. **Replace per-row buttons with selection + single action**
   - Example pattern: `st.dataframe` or `st.radio`/`st.multiselect` for selection, and one action button.
   - This reduces the widget count from ~1000 buttons to 1–2 total, dramatically reducing serialization and DOM cost.

4. **Cache filtered/sorted views**
   - Cache the `build_flat_list_view` output keyed by filters and “completed/backlog” state.
   - Even if the UI still has to render rows, this prevents repeated Python-side list building on every rerun.

5. **Staged loading with placeholders**
   - Render the header and controls immediately; render the large list only after a short “loading” phase or after filters settle.
   - This improves perceived latency by making the page usable earlier.

### Summary: Practical direction
If you want to stay fully in Streamlit, the **highest leverage fix** is reducing widget density (per-row buttons) and limiting initial render size (pagination or collapsed expanders). If you are open to a hybrid approach, a **custom React component with virtualization** could render 1000 rows smoothly while Streamlit only handles higher-level state.

## Assumptions
- Input files produce ~1000 nodes spread across ~8 categories.
- The UI lists all nodes on first load (no pagination or lazy rendering), and each node includes a button widget.
- The observed latency is dominated by initial render and rerun costs, not network or external I/O beyond local file reads.
