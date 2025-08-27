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
    onChange({ ...v, ...patch, offset: 0 });
  }

  return (
    <aside className="sidebar">
      <h3 className="sidebar-title">Search & Filters</h3>

      {/* Search */}
      <label className="field">
        <span>Search Courses</span>
        <input
          className="input"
          value={v.search || ""}
          onChange={(e) => update({ search: e.target.value })}
          placeholder="e.g., MATH 1010, Smith"
        />
      </label>

      {/* Subject */}
      <label className="field">
        <span>Subject</span>
        <select
          className="select"
          value={v.subject || ""}
          onChange={(e) => update({ subject: e.target.value || undefined })}
        >
          <option value="">Any subject</option>
          {subjects.map((s) => (
            <option key={s.subject_id} value={s.code}>
              {s.code}
            </option>
          ))}
        </select>
      </label>

      {/* Semester / Year */}
      <div className="grid2">
        <label className="field">
          <span>Semester</span>
          <select
            className="select"
            value={v.semester || ""}
            onChange={(e) => update({ semester: e.target.value || undefined })}
          >
            <option value="">Any</option>
            {semesters.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Year</span>
          <select
            className="select"
            value={v.year || ""}
            onChange={(e) =>
              update({ year: e.target.value ? Number(e.target.value) : undefined })
            }
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

      {/* Min/Max credits */}
      <div className="grid2">
        <label className="field">
          <span>Min Credits</span>
          <input
            className="input"
            type="number"
            min="0"
            step="0.5"
            value={v.minCredits ?? ""}
            onChange={(e) =>
              update({
                minCredits: e.target.value === "" ? undefined : Number(e.target.value),
              })
            }
          />
        </label>

        <label className="field">
          <span>Max Credits</span>
          <input
            className="input"
            type="number"
            min="0"
            step="0.5"
            value={v.maxCredits ?? ""}
            onChange={(e) =>
              update({
                maxCredits: e.target.value === "" ? undefined : Number(e.target.value),
              })
            }
          />
        </label>
      </div>

      {/* Status */}
      <label className="field">
        <span>Status</span>
        <select
          className="select"
          value={v.status || ""}
          onChange={(e) => update({ status: e.target.value || undefined })}
        >
          <option value="">Any status</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
      </label>

      {/* ---- RMP filters block (clean + stacked) ---- */}
      <div className="divider"></div>

      <label className="field">
        <span>Min RMP Rating</span>
        <input
          className="input"
          type="number"
          min="0"
          max="5"
          step="0.1"
          value={v.rmpMinRating ?? ""}
          onChange={(e) =>
            update({
              rmpMinRating:
                e.target.value === "" ? undefined : Number(e.target.value),
            })
          }
          placeholder="e.g., 3.5"
        />
      </label>

      <label className="field">
        <span>Min # Ratings</span>
        <input
          className="input"
          type="number"
          min="0"
          step="1"
          value={v.rmpMinCount ?? ""}
          onChange={(e) =>
            update({
              rmpMinCount:
                e.target.value === "" ? undefined : Number(e.target.value),
            })
          }
          placeholder="e.g., 10"
        />
      </label>

      <label className="field">
        <span>Max Difficulty</span>
        <input
          className="input"
          type="number"
          min="0"
          max="5"
          step="0.1"
          value={v.rmpMaxDifficulty ?? ""}
          onChange={(e) =>
            update({
              rmpMaxDifficulty:
                e.target.value === "" ? undefined : Number(e.target.value),
            })
          }
          placeholder="e.g., 3.0"
        />
      </label>

      <p className="hint">
        Note: instructors with no RMP data are never filtered out.
      </p>

      {/* Actions */}
      <div className="row gap">
        <button className="btn btn-primary" onClick={() => onChange({ ...v })}>
          Search Courses
        </button>
        <button
          className="btn btn-outline"
          onClick={() =>
            onChange({
              limit: 50,
              offset: 0,
              search: "",
              subject: "",
              semester: "",
              year: undefined,
              minCredits: undefined,
              maxCredits: undefined,
              status: "",
              rmpMinRating: undefined,
              rmpMinCount: undefined,
              rmpMaxDifficulty: undefined,
            })
          }
        >
          Reset
        </button>
      </div>
    </aside>
  );
}
