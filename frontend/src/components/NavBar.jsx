// frontend/src/components/NavBar.jsx
import { Link, useLocation } from "react-router-dom";

export default function NavBar() {
  const { pathname } = useLocation();
  const link = (to, label) => (
    <Link
      to={to}
      className={
        "px-4 py-2 rounded " + (pathname === to ? "bg-black text-white" : "bg-white text-black border")
      }
      style={{ textDecoration: "none", marginRight: 8 }}
    >
      {label}
    </Link>
  );

  return (
    <header style={{
      position: "sticky", top: 0, zIndex: 50,
      backdropFilter: "blur(4px)", background: "rgba(255,255,255,0.9)",
      borderBottom: "1px solid #eee"
    }}>
      <div style={{
        maxWidth: 1200, margin: "0 auto", padding: "10px 16px",
        display: "flex", alignItems: "center", justifyContent: "space-between"
      }}>
        <div style={{ fontWeight: 700 }}>CatBase</div>
        <nav>
          {link("/", "Home")}
          {link("/past", "Past")}
        </nav>
      </div>
    </header>
  );
}
