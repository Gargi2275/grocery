import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Receipt from "../components/Receipt";

export default function BillDetail() {
  const { id } = useParams();
  const { token, logout } = useAuth();
  const [bill, setBill] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api(`/api/bills/${id}/`, { token });
        if (!cancelled) setBill(data);
      } catch (err) {
        if (err.status === 401) {
          logout();
          return;
        }
        if (!cancelled) setError(err.message || "Bill not found.");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id, token, logout]);

  return (
    <div>
      <p className="no-print back-link">
        <Link to="/history">Back to history</Link>
      </p>
      {error ? <p className="form-error">{error}</p> : null}
      {bill ? <Receipt bill={bill} /> : !error ? <p>Loading receipt…</p> : null}
    </div>
  );
}
