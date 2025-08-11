export default function Pagination({ total, limit, offset, itemsLength, onChange }) {
  const page = Math.floor((offset || 0) / (limit || 1)) + 1;

  const looksFishy = Number.isFinite(total) && total > 0 && total <= (itemsLength || 0);
  const hasTotal = Number.isFinite(total) && total > 0 && !looksFishy;

  const pageCount = hasTotal ? Math.max(1, Math.ceil(total / (limit || 1))) : null;

  const gotoOffset = (newPage) => {
    const p = Math.max(1, newPage);
    onChange((p - 1) * limit);
  };

  const canPrev = offset > 0;
  const canNext = hasTotal ? page < pageCount : (itemsLength || 0) >= (limit || 1);

  if (!hasTotal) {
    return (
      <div className="pager">
        <button className="btn" onClick={() => gotoOffset(page - 1)} disabled={!canPrev}>‹ Prev</button>
        <div className="pager-text">Page {page}</div>
        <button className="btn" onClick={() => gotoOffset(page + 1)} disabled={!canNext}>Next ›</button>
      </div>
    );
  }

  const pages = [];
  const add = (n) => pages.push(n);
  if (pageCount <= 9) {
    for (let i = 1; i <= pageCount; i++) add(i);
  } else {
    add(1);
    if (page > 4) add("…");
    for (let i = Math.max(2, page - 2); i <= Math.min(pageCount - 1, page + 2); i++) add(i);
    if (page < pageCount - 3) add("…");
    add(pageCount);
  }

  return (
    <div className="pager">
      <button className="btn" onClick={() => gotoOffset(page - 1)} disabled={!canPrev}>‹ Prev</button>
      {pages.map((p, i) =>
        p === "…" ? (
          <span key={`dots-${i}`} className="pager-dots">…</span>
        ) : (
          <button
            key={p}
            onClick={() => gotoOffset(p)}
            disabled={p === page}
            className={`btn ${p === page ? "btn-active" : ""}`}
          >
            {p}
          </button>
        )
      )}
      <button className="btn" onClick={() => gotoOffset(page + 1)} disabled={!canNext}>Next ›</button>
    </div>
  );
}
