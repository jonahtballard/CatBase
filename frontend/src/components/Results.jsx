import SectionCard from "./SectionCard";
import Pagination from "./Pagination";

export default function Results({ items, total, limit, offset, onPage }) {
  // group by course (subject+number+title)
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

  const shown = (offset || 0) + (items?.length || 0);
  const totalText = Number.isFinite(total) && total > 0 ? total : shown;

  return (
    <section style={{ flex: 1, padding: 16 }}>
      <div style={{ marginBottom: 12, opacity: 0.8 }}>
        Showing <b>{Math.min(totalText, shown)}</b> of <b>{totalText}</b> results
      </div>

      {groups.map(({ course, sections }) => (
        <SectionCard
          key={`${course.subject}-${course.course_number}-${course.title}`}
          course={course}
          sections={sections}
        />
      ))}

      <Pagination
        total={total}
        limit={limit}
        offset={offset}
        itemsLength={items?.length || 0}
        onChange={onPage}
      />
    </section>
  );
}
