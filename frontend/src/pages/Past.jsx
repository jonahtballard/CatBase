// frontend/src/pages/Past.jsx
import { useEffect, useMemo, useState } from "react";
import { getJSON } from "../lib/api";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, AreaChart, Area
} from "recharts";

function Panel({ title, children }) {
  return (
    <section style={{ background: "#fff", border: "1px solid #eee", borderRadius: 12, padding: 16 }}>
      <h3 style={{ margin: 0, marginBottom: 12 }}>{title}</h3>
      {children}
    </section>
  );
}

export default function Past() {
  const [subjects, setSubjects] = useState([]);
  const [terms, setTerms] = useState([]);

  // Filters
  const [selectedSubjects, setSelectedSubjects] = useState([]);
  const [levels, setLevels] = useState([]);
  const [range, setRange] = useState([null, null]);

  // Data
  const [enrollTS, setEnrollTS] = useState([]);
  const [sectionsTS, setSectionsTS] = useState([]);
  const [birthDeath, setBirthDeath] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [credits, setCredits] = useState([]);

  useEffect(() => {
    getJSON("/subjects").then(setSubjects);
    getJSON("/terms").then((t) => {
      setTerms(t);
      if (t.length) {
        const ys = t.map(x => x.year);
        setRange([Math.min(...ys), Math.max(...ys)]);
      }
    });
  }, []);

  const params = useMemo(() => {
    const p = {};
    if (selectedSubjects.length) p.subjects = selectedSubjects.join(",");
    if (levels.length) p.level = levels.join(",");
    if (range[0] != null) p.start_year = range[0];
    if (range[1] != null) p.end_year = range[1];
    return p;
  }, [selectedSubjects, levels, range]);

  useEffect(() => {
    const calls = [
      ["/analytics/enrollment_over_time", setEnrollTS],
      ["/analytics/sections_over_time", setSectionsTS],
      ["/analytics/course_birth_death", setBirthDeath],
      ["/analytics/meeting_heatmap", setHeatmap],
      ["/analytics/credits_distribution", setCredits],
    ];
    Promise.all(calls.map(([url]) => getJSON(url, params)))
      .then((arr) => arr.forEach((d, i) => calls[i][1](d)))
      .catch(console.error);
  }, [params]);

  const termLabel = (d) => `${d.semester} ${d.year}`;

  // Heatmap grid prep
  const HM_DAYS = ["M","T","W","R","F"];
  const HM_HOURS = Array.from({length: 15}, (_,i) => i + 7); // 7..21
  const heatGrid = useMemo(() => {
    const map = new Map();
    heatmap.forEach((r) => {
      const days = (r.days || "").split("").filter(Boolean);
      days.forEach((d) => {
        const key = `${d}|${r.hour}`;
        map.set(key, (map.get(key) || 0) + (r.n || 0));
      });
    });
    return HM_HOURS.map((h) => {
      const row = { hour: h };
      HM_DAYS.forEach((d) => { row[d] = map.get(`${d}|${h}`) || 0; });
      return row;
    });
  }, [heatmap]);

  const toggle = (arr, val) => arr.includes(val) ? arr.filter(x=>x!==val) : [...arr, val];

  return (
    <div style={{ maxWidth: 1200, margin: "24px auto", padding: "0 16px" }}>
      <h1 style={{ marginBottom: 8 }}>Past Courses Explorer</h1>
      <p style={{ marginTop: 0, color: "#555" }}>
        Explore historical trends: enrollment, sections, course births/deaths, time-of-day patterns, and credit distributions.
      </p>

      {/* Filters */}
      <section style={{
        display: "grid", gap: 12, gridTemplateColumns: "2fr 1fr 1fr",
        background: "#fafafa", border: "1px solid #eee", borderRadius: 12, padding: 16,
        marginBottom: 16
      }}>
        <div>
          <label style={{ fontSize: 12, color: "#666" }}>Subjects</label>
          <select multiple size={8} value={selectedSubjects}
                  onChange={(e)=> setSelectedSubjects(Array.from(e.target.selectedOptions).map(o=>o.value))}
                  style={{ width: "100%", padding: 8 }}>
            {subjects.map((s) => (
              <option key={s.subject_id} value={s.code}>{s.code}</option>
            ))}
          </select>
          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={()=>setSelectedSubjects([])}>Clear</button>
            <button onClick={()=>setSelectedSubjects(subjects.slice(0,5).map(s=>s.code))}>Top 5</button>
          </div>
        </div>

        <div>
          <label style={{ fontSize: 12, color: "#666" }}>Levels</label>
          {["100","200","300","400","500"].map((lvl) => (
            <div key={lvl}>
              <label>
                <input type="checkbox" checked={levels.includes(lvl)}
                       onChange={()=> setLevels(toggle(levels, lvl))} /> {lvl}
              </label>
            </div>
          ))}
          <div style={{ marginTop: 8 }}>
            <button onClick={()=>setLevels([])}>All</button>
          </div>
        </div>

        <div>
          <label style={{ fontSize: 12, color: "#666" }}>Year range</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input type="number" value={range[0] ?? ''} onChange={(e)=>setRange([Number(e.target.value||0), range[1]])} />
            <span>to</span>
            <input type="number" value={range[1] ?? ''} onChange={(e)=>setRange([range[0], Number(e.target.value||0)])} />
          </div>
          <div style={{ marginTop: 8 }}>
            <button onClick={() => {
              if (!terms.length) return;
              const ys = terms.map(t=>t.year);
              setRange([Math.min(...ys), Math.max(...ys)]);
            }}>Full range</button>
          </div>
        </div>
      </section>

      <div style={{ display: "grid", gap: 16 }}>
        {/* Enrollment over time */}
        <Panel title="Enrollment Over Time (Sum)">
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={enrollTS.map(d=>({ ...d, term: termLabel(d) }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="term" angle={-35} textAnchor="end" height={60} />
              <YAxis />
              <Tooltip />
              <Legend />
              {(() => {
                const map = new Map();
                enrollTS.forEach((d) => {
                  const key = d.subject || "All";
                  if (!map.has(key)) map.set(key, []);
                  map.get(key).push({ ...d, term: termLabel(d) });
                });
                return Array.from(map.keys()).map((k) => (
                  <Area key={k} type="monotone" dataKey="cur_enroll" name={`${k} current`}
                        data={map.get(k)} fillOpacity={0.2} />
                ));
              })()}
            </AreaChart>
          </ResponsiveContainer>
        </Panel>

        {/* Sections over time */}
        <Panel title="Sections Offered Over Time">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={sectionsTS.map(d=>({ ...d, term: termLabel(d) }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="term" angle={-35} textAnchor="end" height={60} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="sections" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Panel>

        {/* Course births vs deaths */}
        <Panel title="Course Births vs. Deaths by Term">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={birthDeath.map(d=>({ ...d, term: termLabel(d) }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="term" angle={-35} textAnchor="end" height={60} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="births" stackId="x" />
              <Bar dataKey="deaths" stackId="x" />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        {/* Time-of-day heatmap (table-based) */}
        <Panel title="Meeting Time Heatmap (count of sections)">
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ddd" }}>Hour</th>
                  {["M","T","W","R","F"].map((d) => (
                    <th key={d} style={{ padding: 6, borderBottom: "1px solid #ddd" }}>{d}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatGrid.map((row) => (
                  <tr key={row.hour}>
                    <td style={{ padding: 6, borderBottom: "1px solid #f0f0f0" }}>{row.hour}:00</td>
                    {["M","T","W","R","F"].map((d) => (
                      <td key={d} title={`${row[d]} sections`}
                          style={{
                            padding: 6,
                            borderBottom: "1px solid #f0f0f0",
                            background: `rgba(0,0,0,${Math.min(0.1 + (row[d]/50), 0.9)})`,
                            color: "#fff",
                            textAlign: "center"
                          }}>
                        {row[d]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        {/* Credits distribution */}
        <Panel title="Credits Distribution by Term (avg credits per section)">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={credits.map(d=>({ ...d, term: termLabel(d) }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="term" angle={-35} textAnchor="end" height={60} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="n" />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <div style={{ marginTop: 16, color: "#777", fontSize: 12 }}>
        Tip: Select multiple subjects and levels, then narrow the year range to compare eras.
      </div>
    </div>
  );
}
