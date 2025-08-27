import SectionCard from "./SectionCard";
import Pagination from "./Pagination";

export default function Results({ items, total, limit, offset, onPage }) {
  const pageSize = limit || 50;

  // Group by course (subject + number + title)
  const byCourse = items.reduce((acc, s) => {
    const key = `${s.subject}:${s.course_number}:${s.title}`;
    if (!acc[key]) {
      acc[key] = {
        course: {
          subject: s.subject,
          course_number: s.course_number,
          title: s.title,
        },
        sections: [],
      };
    }
    acc[key].sections.push(s);
    return acc;
  }, {});

  const grouped = Object.values(byCourse);

  // Header range text: “1–50 of 123”, “1–9 of 9”, “51–100 of 137”, etc.
  const hasTotal = Number.isFinite(total) && total >= 0;
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = hasTotal
    ? Math.min(offset + pageSize, total)
    : offset + (items?.length || 0);

  return (
    <section>
      <div
        className="results-meta"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          margin: "10px 0 16px",
        }}
      >
        <h2 style={{ margin: 0 }}>
          {hasTotal
            ? `${pageStart}–${pageEnd} of ${total} results`
            : `${pageStart}–${pageEnd} results`}
        </h2>
      </div>

      {grouped.map(({ course, sections }, idx) => (
        <SectionCard key={`${course.subject}:${course.course_number}:${idx}`} course={course} sections={sections} />
      ))}

      <Pagination
        total={hasTotal ? total : undefined}
        limit={pageSize}
        offset={offset}
        itemsLength={items?.length || 0}
        onChange={onPage}
      />
    </section>
  );
}
