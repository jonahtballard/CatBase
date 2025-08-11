import { useState } from "react";
import clsx from "clsx";

export default function SectionCard({ course, sections }) {
  const [open, setOpen] = useState(false);
  const sectionCount = sections?.length ?? 0;

  return (
    <div className="card">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="card-header"
      >
        <div>
          <div className="card-sub">
            {course.subject} {course.course_number}
          </div>
          <div className="card-title">{course.title}</div>
          <div className="card-sub2">
            {sectionCount} section{sectionCount !== 1 ? "s" : ""}
          </div>
        </div>
        <div className="card-caret">{open ? "▾" : "▸"}</div>
      </button>

      {open && (
        <div className="card-body">
          {sections.map((s) => {
            const openSeat = (s.current_enrollment ?? 0) < (s.max_enrollment ?? 0);
            const term = `${s.semester} ${s.year}`;

            return (
              <div key={s.section_id} className="section-row">
                <div className="section-col small">
                  <div className="label-strong">CRN {s.crn}</div>
                  <span className={clsx("chip", openSeat ? "open" : "closed")}>
                    {openSeat ? "OPEN" : "FULL"}
                  </span>
                </div>

                <div className="section-col">
                  <div className="label">Term</div>
                  <div>{term}</div>
                </div>

                <div className="section-col">
                  <div className="label">Meetings</div>
                  <div className="prewrap">
                    {(s.meetings || []).map((m, i) => {
                      const time = m.start_time && m.end_time ? `${m.start_time}-${m.end_time}` : "";
                      const place = [m.bldg, m.room].filter(Boolean).join(" ");
                      return <div key={i}>{[m.days, time, place].filter(Boolean).join(" ")}</div>;
                    })}
                  </div>
                </div>

                <div className="section-col">
                  <div className="label">Instructors</div>
                  <div>{(s.instructors || []).map((i) => i.name).join(", ") || "TBA"}</div>
                </div>

                <div className="section-col">
                  <div className="label">Enrollment</div>
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

