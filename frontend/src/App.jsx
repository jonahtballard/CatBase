import { useEffect, useState } from "react";
import Filters from "./components/Filters";
import Results from "./components/Results";
import { getJSON } from "./lib/api";

export default function App() {
  // Server-side pagination size: 50
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

  // Ensure Home always uses the latest term on load
  useEffect(() => {
    let mounted = true;
    getJSON("/terms").then((ts) => {
      if (!mounted || !ts.length) return;
      const t = ts[0]; // assuming API returns newest first
      // Adjust these keys to match your state shape:
      setFilters((f) => ({ ...f, semester: t.semester, year: t.year }));
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const params = {
      limit: 50,
      offset: filters.offset,
      subject: filters.subject || undefined,
      semester: filters.semester || undefined,
      year: filters.year,
      search: filters.search || undefined,

      // PUSH ALL FILTERS SERVER-SIDE (fixes pagination)
      min_credits: filters.minCredits,
      max_credits: filters.maxCredits,
      status: filters.status || undefined,

      // RMP filters (NULL should pass)
      rmp_min_rating: filters.rmpMinRating,
      rmp_min_count: filters.rmpMinCount,
      rmp_max_difficulty: filters.rmpMaxDifficulty,
    };

    setState((s) => ({ ...s, loading: true, error: "" }));

    getJSON("/sections", params)
      .then((data) => {
        setState({
          items: data.items || [],
          total: data.total || 0,
          loading: false,
          error: "",
        });
      })
      .catch((e) =>
        setState({ items: [], total: 0, loading: false, error: e.message })
      );
  }, [
    filters.offset,
    filters.subject,
    filters.semester,
    filters.year,
    filters.search,
    filters.minCredits,
    filters.maxCredits,
    filters.status,
    filters.rmpMinRating,
    filters.rmpMinCount,
    filters.rmpMaxDifficulty,
  ]);

  return (
    <div className="app">
      <Filters value={filters} onChange={setFilters} mode="current" />
      <main className="main">
        {/* Header with only the CatBase logo */}
        <header
          className="header light"
          style={{
            background: "#fff",
            padding: "10px 20px",
            display: "flex",
            alignItems: "center",
            borderBottom: "1px solid #ddd",
          }}
        >
          <img
            src="/CatBase.png"
            alt="CatBase Logo"
            style={{ height: "70px", width: "auto", objectFit: "contain" }}
          />
        </header>

        {state.error && (
          <div className="error" role="alert">
            {state.error}
          </div>
        )}

        {/* Results */}
        <Results
          items={state.items}
          total={state.total}
          limit={50}
          offset={filters.offset}
          onPage={(newOffset) =>
            setFilters((f) => ({ ...f, offset: newOffset }))
          }
        />

        {/* Footer */}
        <footer
          className="site-footer"
          style={{
            marginTop: "20px",
            textAlign: "center",
            fontSize: "0.9rem",
            color: "#555",
          }}
        >
          <div>
            Created by <strong>Jonah Ballard</strong>
          </div>
        </footer>
      </main>
    </div>
  );
}
