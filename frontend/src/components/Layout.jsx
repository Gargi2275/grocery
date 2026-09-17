import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Layout() {
  const { logout } = useAuth();
  const { pathname } = useLocation();
  const scene = pathname === "/" ? "generate" : "ledger";

  return (
    <div className={`app-shell scene-${scene}`}>
      <header className="app-nav no-print">
        <p className="wordmark">Grocery Bill</p>
        <nav>
          <NavLink to="/" end>
            Generate
          </NavLink>
          <NavLink to="/history">History</NavLink>
          <button type="button" className="link-btn" onClick={logout}>
            Sign out
          </button>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
