import { useEffect, useMemo, useState } from "react";
import { getJSON } from "../lib/api";

export default function Filters({ value, onChange }) {
  const [subjects, setSubjects] = useState([]);
  const [terms, setTerms] = useState([]);

  useEffect(() => {
    getJSON("/subjects").then(setSubjects);
    getJSON("/terms").then(setTerms);
  }, []);

  const years = useMemo(
    () => Array.from(new Set(terms.map((t) => t.year))).sort((a, b) => b - a),
    [terms]
  );
  const semesters = useMemo(() => ["Spring", "Summer", "Fall", "Winter"], []);

  const v = value;

  function update(patch) {
    onChange({ ...v, ...patch, offset: 0 }); // reset page when filters change
  }

  return (
    <aside style={{ width: 300, padding: 16, borderRight: "1px solid #222" }}>
      <h3 style={{ margin: "8px 0 12px" }}>Search & Filters</h3>

      <label style={{ display: "block", marginBottom: 8 }}>
        Search Courses
        <input
          value={v.search || ""}
          onChange={(e) => update({ search: e.target.value })}
          placeholder="e.g., MATH 1010, Smith"
          style={{ width: "100%", marginTop: 6, padding: 8 }}
        />
      </label>

      <label style={{ display: "block", margin: "12px 0 8px" }}>
        Subject
        <select
          value={v.subject || ""}
          onChange={(e) => update({ subject: e.target.value || undefined })}
          style={{ width: "100%", marginTop: 6, padding: 8 }}
        >
        <option value="">Any subject</option>
        {subjects.map((s) => (
          <option key={s.subject_id} value={s.code}>
            {s.code}
          </option>
        ))}
        </select>
      </label>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <label>
          Semester
          <select
            value={v.semester || ""}
            onChange={(e) => update({ semester: e.target.value || undefined })}
            style={{ width: "100%", marginTop: 6, padding: 8 }}
          >
            <option value="">Any</option>
            {semesters.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Year
          <select
            value={v.year || ""}
            onChange={(e) =>
              update({ year: e.target.value ? Number(e.target.value) : undefined })
            }
            style={{ width: "100%", marginTop: 6, padding: 8 }}
          >
            <option value="">Any</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 12 }}>
        <label>
          Min Credits
          <input
            type="number"
            min="0"
            step="0.5"
            value={v.minCredits ?? ""}
            onChange={(e) =>
              update({
                minCredits: e.target.value === "" ? undefined : Number(e.target.value),
              })
            }
            style={{ width: "100%", marginTop: 6, padding: 8 }}
          />
        </label>
        <label>
          Max Credits
          <input
            type="number"
            min="0"
            step="0.5"
            value={v.maxCredits ?? ""}
            onChange={(e) =>
              update({
                maxCredits: e.target.value === "" ? undefined : Number(e.target.value),
              })
            }
            style={{ width: "100%", marginTop: 6, padding: 8 }}
          />
        </label>
      </div>

      <label style={{ display: "block", marginTop: 12 }}>
        Status
        <select
          value={v.status || ""}
          onChange={(e) => update({ status: e.target.value || undefined })}
          style={{ width: "100%", marginTop: 6, padding: 8 }}
        >
          <option value="">Any status</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
      </label>

      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <button onClick={() => onChange({ ...v })} style={{ padding: "8px 12px" }}>
          Search Courses
        </button>
        <button
          onClick={() =>
            onChange({
              limit: 50,      // keep fixed
              offset: 0,
              search: "",
              subject: "",
              semester: "",
              year: undefined,
              minCredits: undefined,
              maxCredits: undefined,
              status: "",
            })
          }
          style={{ padding: "8px 12px" }}
        >
          Reset Filters
        </button>
      </div>
    </aside>
  );
}


