import { useEffect, useState } from "react";
import Filters from "./components/Filters";
import Results from "./components/Results";
import { getJSON } from "./lib/api";

export default function App() {
  // Fixed page size: 50
  const [filters, setFilters] = useState({
    limit: 50,
    offset: 0,
    search: "",
    subject: "",
    semester: "",
    year: undefined,
    minCredits: undefined,
    maxCredits: undefined,
    status: "", // "open" | "closed" | ""
  });

  const [state, setState] = useState({
    items: [],
    total: 0,
    loading: false,
    error: "",
  });

  useEffect(() => {
    const params = {
      limit: 50, // ensure request always uses 50 even if state changes elsewhere
      offset: filters.offset,
      subject: filters.subject || undefined,
      semester: filters.semester || undefined,
      year: filters.year,
      search: filters.search || undefined,
    };

    setState((s) => ({ ...s, loading: true, error: "" }));

    getJSON("/sections", params)
      .then((data) => {
        let items = data.items || [];

        // client-side extras
        if (filters.minCredits != null) {
          items = items.filter((s) => (s.credits_min ?? 0) >= filters.minCredits);
        }
        if (filters.maxCredits != null) {
          items = items.filter((s) => (s.credits_max ?? s.credits_min ?? 0) <= filters.maxCredits);
        }
        if (filters.status === "open") {
          items = items.filter((s) => (s.current_enrollment ?? 0) < (s.max_enrollment ?? 0));
        }
        if (filters.status === "closed") {
          items = items.filter((s) => (s.current_enrollment ?? 0) >= (s.max_enrollment ?? 0));
        }

        setState({
          items,
          total: data.total ?? items.length,
          loading: false,
          error: "",
        });
      })
      .catch((e) =>
        setState({ items: [], total: 0, loading: false, error: e.message })
      );
  }, [filters]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", color: "#eee", background: "#111" }}>
      <Filters value={filters} onChange={setFilters} />
      <main style={{ flex: 1 }}>
        <header style={{ padding: 16, borderBottom: "1px solid #222" }}>
          <h1 style={{ margin: 0 }}>CatBase</h1>
          <div style={{ opacity: 0.7, fontSize: 12 }}>
            Backend: <code>{import.meta.env.VITE_API_URL}</code>
          </div>
        </header>

        {state.error && <div style={{ color: "tomato", padding: 16 }}>Error: {state.error}</div>}

        {state.loading ? (
          <div style={{ padding: 16 }}>Loading…</div>
        ) : (
          <Results
            items={state.items}
            total={state.total}
            limit={50} // pass fixed page size to pagination
            offset={filters.offset}
            onPage={(newOffset) => setFilters((f) => ({ ...f, offset: newOffset }))}
          />
        )}
      </main>
    </div>
  );
}

