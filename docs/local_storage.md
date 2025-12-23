# Local storage usage in Streamlit

Access to `window.localStorage` in Streamlit requires running JavaScript in the
browser. Each `components.v1.html` call mounts an iframe that opens its own
channel back to the Streamlit runtime. When these iframes are created on every
rerun (or multiple times per page), the extra WebSocket chatter and background
cleanup can noticeably slow the UI and generate `WebSocketClosedError` traces
when users navigate quickly.

Best practices gathered from Streamlit community guidance and the docs:

- **Render storage bridges sparingly.** Keep a single hidden component per page
  and reuse it instead of recreating iframes on every rerun. Run storage reads
  only during initial hydration and writes only when state has actually
  changed.
- **Short-circuit unchanged values.** Track a serialized snapshot in
  `st.session_state` so the app can avoid sending redundant write requests back
  to the browser.
- **Guard against blocked storage.** Browsers in incognito or with strict
  privacy settings may throw when touching storage. Catch and surface those
  errors once rather than retrying endlessly.
- **Prefer small JSON payloads.** Serialize only the data you need (e.g.,
  backlog IDs) to keep parsing fast and avoid synchronous storage writes that
  can block the UI thread.
- **Defer heavy work until user-triggered.** Avoid coupling storage access to
  unrelated reruns; tie it to explicit user actions (like backlog edits) so the
  app remains responsive.
