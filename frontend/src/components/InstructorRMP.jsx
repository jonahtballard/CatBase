import { useEffect, useState } from "react";
import { getJSON } from "../lib/api";

// simple in-memory cache so we don't refetch
const cache = new Map(); // key -> { status, data }

function normalizeName(name = "") {
  return name.toLowerCase().replace(/[^a-z\s]/g, "").replace(/\s+/g, " ").trim();
}

export default function InstructorRMP({ instructor, compact = true }) {
  const name = instructor?.name || "";
  const id = instructor?.instructor_id ?? instructor?.id ?? null;
  const cacheKey = id ? `id:${id}` : `name:${normalizeName(name)}`;

  const [{ status, data }, setState] = useState(() => {
    const c = cache.get(cacheKey);
    return c || { status: "idle", data: null };
  });

  useEffect(() => {
    let aborted = false;
    async function load() {
      if (!name && !id) return;
      if (cache.has(cacheKey)) {
        setState(cache.get(cacheKey));
        return;
      }
      setState({ status: "loading", data: null });
      try {
        let payload = null;
        if (id) {
          payload = await getJSON(`/instructors/${id}/rmp`);
        } else {
          // name lookup; prefer exact match & has_rmp=1
          const list = await getJSON(`/instructors`, {
            search: name,
            include_rmp: 1,
            has_rmp: 1,
            limit: 5,
          });
          const items = Array.isArray(list) ? list : list?.items || [];
          const nn = normalizeName(name);
          for (const it of items) {
            const itName = normalizeName(it.name);
            if (itName === nn && it.rmp) {
              payload = it.rmp;
              break;
            }
          }
          if (!payload && items.length) payload = items[0].rmp || items[0];
        }
        const next = { status: "loaded", data: payload };
        cache.set(cacheKey, next);
        if (!aborted) setState(next);
      } catch {
        const next = { status: "error", data: null };
        cache.set(cacheKey, next);
        if (!aborted) setState(next);
      }
    }
    load();
    return () => { aborted = true; };
  }, [cacheKey, id, name]);

  if (!name) return null;

  if (status === "loading") return <div className="rmp-pill loading">Loading RMP…</div>;
  if (status === "error")   return <div className="rmp-pill muted">RMP unavailable</div>;
  if (!data || (!data.avg_rating && !data.num_ratings && !data.difficulty && !data.would_take_again)) {
    return <div className="rmp-pill muted">No RMP data</div>;
  }

  const avg = data.avg_rating ?? null;
  const count = data.num_ratings ?? null;
  const diff = data.difficulty ?? null;
  const wta = data.would_take_again ?? data.would_take_again_percent ?? null;
  const url = data.rmp_url || data.url;

  return (
    <div className={"rmp-pill" + (compact ? " compact" : "")}>
      {url ? <a href={url} target="_blank" rel="noreferrer" className="name-link">{name}</a> : <span className="name">{name}</span>}
      <span className="stat">★ {avg != null ? Number(avg).toFixed(1) : "—"}</span>
      <span className="sep">•</span>
      <span className="stat">{count != null ? `${count} ratings` : "—"}</span>
      <span className="sep">•</span>
      <span className="stat">Diff {diff != null ? Number(diff).toFixed(1) : "—"}</span>
      <span className="sep">•</span>
      <span className="stat">{wta != null ? `${Math.round(Number(wta))}% WTA` : "—"}</span>
    </div>
  );
}
