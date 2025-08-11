import SectionCard from "./SectionCard";
import Pagination from "./Pagination";

export default function Results({ items, total, limit, offset, onPage }) {
  // Group by course (subject+number+title)
  const byCourse = items.reduce((acc, s) => {
    const key = `${s.subject}:${s.course_number}:${s.title}`;
    if (!acc[key]) {
      acc[key] = {
        course: { subject: s.subject, course_number: s.course_number, title: s.title },
        sections: [],
      };
    }
    acc[key].sections.push(s);
    return acc;
  }, {});
  const groups = Object.values(byCourse);

  // Range display
  const pageSize = limit || 50;
  const rawEnd = (offset || 0) + (items?.length || 0);
  const start = (items?.length || 0) === 0 ? 0 : (offset || 0) + 1;

  // If backend total looks "fishy" (e.g., equals just this page length), fall back to end
  const looksFishy = Number.isFinite(total) && total > 0 && total <= (items?.length || 0);
  const hasTotal = Number.isFinite(total) && total > 0 && !looksFishy;

  const end = hasTotal ? Math.min(rawEnd, total) : rawEnd;
  const totalText = hasTotal ? total : end;

  return (
    <section style={{ flex: 1, padding: 16 }}>
      <div style={{ marginBottom: 12, color: "#6b7280" }}>
        {totalText === 0
          ? "No results found"
          : `Showing ${start} – ${end} of ${totalText} results`}
      </div>

      {groups.map(({ course, sections }) => (
        <SectionCard
          key={`${course.subject}-${course.course_number}-${course.title}`}
          course={course}
          sections={sections}
        />
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
