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
    rmpMinRating: undefined,
    rmpMinCount: undefined,
    rmpMaxDifficulty: undefined,
  });

  const [state, setState] = useState({
    items: [],
    total: 0,
    loading: false,
    error: "",
  });

  useEffect(() => {
    const params = {
      limit: 50,
      offset: filters.offset,
      subject: filters.subject || undefined,
      semester: filters.semester || undefined,
      year: filters.year,
      search: filters.search || undefined,
      // RMP filters (backend should treat NULL RMP as pass-through)
      rmp_min_rating: filters.rmpMinRating,
      rmp_min_count: filters.rmpMinCount,
      rmp_max_difficulty: filters.rmpMaxDifficulty,
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
    <div className="app">
      <Filters value={filters} onChange={setFilters} />
      <main className="main">
        {/* Header with only the CatBase logo */}
        <header
          className="header light"
          style={{
            background: "#fff",
            padding: "10px 20px",
            display: "flex",
            alignItems: "center",
            borderBottom: "1px solid #ddd"
          }}
        >
          <img
            src="/CatBase.png"
            alt="CatBase Logo"
            style={{
              height: "70px",
              width: "auto",
              objectFit: "contain"
            }}
          />
        </header>

        {state.error && <div className="error">Error: {state.error}</div>}
        {state.loading ? (
          <div className="loading">Loading…</div>
        ) : (
          <Results
            items={state.items}
            total={state.total}
            limit={50}
            offset={filters.offset}
            onPage={(newOffset) => setFilters((f) => ({ ...f, offset: newOffset }))}
          />
        )}

        {/* Footer */}
        <footer className="site-footer" style={{ marginTop: "20px", textAlign: "center", fontSize: "0.9rem", color: "#555" }}>
          <div>Created by <strong>Jonah Ballard</strong></div>
        </footer>
      </main>
    </div>
  );
}