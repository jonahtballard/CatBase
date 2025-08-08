import { useState } from "react";
import clsx from "clsx";

export default function SectionCard({ course, sections }) {
  const [open, setOpen] = useState(false);
  const sectionCount = sections?.length ?? 0;

  return (
    <div style={{ border: "1px solid #333", borderRadius: 8, marginBottom: 12, background: "#151515" }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        style={{
          width: "100%",
          textAlign: "left",
          padding: 12,
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "transparent",
          border: 0,
          color: "inherit",
        }}
      >
        <div>
          <div style={{ fontSize: 14, opacity: 0.85 }}>
            {course.subject} {course.course_number}
          </div>
          <div style={{ fontWeight: 600 }}>{course.title}</div>
          <div style={{ fontSize: 12, opacity: 0.65 }}>
            {sectionCount} section{sectionCount !== 1 ? "s" : ""}
          </div>
        </div>
        <div style={{ fontSize: 20, lineHeight: 1 }}>{open ? "▾" : "▸"}</div>
      </button>

      {open && (
        <div style={{ borderTop: "1px solid #333", padding: 12 }}>
          {sections.map((s) => {
            const openSeat = (s.current_enrollment ?? 0) < (s.max_enrollment ?? 0);
            const term = `${s.semester} ${s.year}`;

            return (
              <div
                key={s.section_id}
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "120px minmax(140px, 1fr) minmax(220px, 1.2fr) minmax(220px, 1.2fr) minmax(120px, 0.8fr)",
                  gap: 8,
                  padding: "10px 0",
                  borderBottom: "1px dashed #333",
                }}
              >
                <div style={{ fontSize: 12 }}>
                  <div style={{ marginBottom: 6, fontWeight: 600 }}>CRN {s.crn}</div>
                  <span className={clsx("chip", openSeat ? "open" : "closed")}>
                    {openSeat ? "OPEN" : "FULL"}
                  </span>
                </div>

                <div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Term</div>
                  <div>{term}</div>
                </div>

                <div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Meetings</div>
                  <div style={{ whiteSpace: "pre-wrap" }}>
                    {(s.meetings || []).map((m, i) => {
                      const time = m.start_time && m.end_time ? `${m.start_time}-${m.end_time}` : "";
                      const place = [m.bldg, m.room].filter(Boolean).join(" ");
                      return <div key={i}>{[m.days, time, place].filter(Boolean).join(" ")}</div>;
                    })}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Instructors</div>
                  <div>{(s.instructors || []).map((i) => i.name).join(", ") || "TBA"}</div>
                </div>

                <div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Enrollment</div>
                  <div>{s.current_enrollment}/{s.max_enrollment ?? "?"}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
