import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import { formatDate, formatInr } from "../format";

const emptyFilters = {
  q: "",
  customer: "",
  shop: "",
  date_from: "",
  date_to: "",
  min_total: "",
  max_total: "",
  gst: "all",
};

export default function History() {
  const { token, logout } = useAuth();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState(emptyFilters);
  const [applied, setApplied] = useState(emptyFilters);
  const [data, setData] = useState({ results: [], count: 0, next: null, previous: null });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({ page: String(page) });
        Object.entries(applied).forEach(([key, value]) => {
          if (value && value !== "all") params.set(key, value);
        });
        const response = await api(`/api/bills/?${params.toString()}`, { token });
        if (!cancelled) setData(response);
      } catch (err) {
        if (err.status === 401) {
          logout();
          return;
        }
        if (!cancelled) setError(err.message || "Could not load bills.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [page, applied, token, logout]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function applyFilters(event) {
    event.preventDefault();
    setPage(1);
    setApplied({ ...filters });
  }

  function clearFilters() {
    setFilters(emptyFilters);
    setApplied(emptyFilters);
    setPage(1);
  }

  return (
    <section className="panel">
      <h2>History</h2>
      <p className="muted">Search past bills by name, date, amount, or GST.</p>
      <form className="history-filters form-grid" onSubmit={applyFilters}>
        <label className="span-2">
          Search
          <input
            type="search"
            value={filters.q}
            onChange={(e) => updateFilter("q", e.target.value)}
            placeholder="Bill no., customer, shop, address"
          />
        </label>
        <label>
          Customer
          <input value={filters.customer} onChange={(e) => updateFilter("customer", e.target.value)} />
        </label>
        <label>
          Shop
          <input value={filters.shop} onChange={(e) => updateFilter("shop", e.target.value)} />
        </label>
        <label>
          From date
          <input type="date" value={filters.date_from} onChange={(e) => updateFilter("date_from", e.target.value)} />
        </label>
        <label>
          To date
          <input type="date" value={filters.date_to} onChange={(e) => updateFilter("date_to", e.target.value)} />
        </label>
        <label>
          Min total
          <input
            type="number"
            min="0"
            step="0.01"
            value={filters.min_total}
            onChange={(e) => updateFilter("min_total", e.target.value)}
          />
        </label>
        <label>
          Max total
          <input
            type="number"
            min="0"
            step="0.01"
            value={filters.max_total}
            onChange={(e) => updateFilter("max_total", e.target.value)}
          />
        </label>
        <label>
          GST
          <select value={filters.gst} onChange={(e) => updateFilter("gst", e.target.value)}>
            <option value="all">All bills</option>
            <option value="yes">With GST</option>
            <option value="no">No GST</option>
          </select>
        </label>
        <div className="filter-actions">
          <button className="btn" type="submit">
            Apply filters
          </button>
          <button className="btn secondary" type="button" onClick={clearFilters}>
            Clear
          </button>
        </div>
      </form>
      {loading ? <p>Loading…</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {!loading && data.results.length === 0 ? <p>No bills match these filters.</p> : null}
      {data.results.length > 0 && (
        <>
          <p className="muted">{data.count} bill{data.count === 1 ? "" : "s"} found</p>
          <div className="table-wrap desktop-only">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Bill no.</th>
                  <th>Date</th>
                  <th>Customer</th>
                  <th>Shop</th>
                  <th>GST</th>
                  <th>Total</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((bill) => (
                  <tr key={bill.id}>
                    <td>{bill.bill_number}</td>
                    <td>{formatDate(bill.bill_date)}</td>
                    <td>{bill.customer_name}</td>
                    <td>{bill.shop_name}</td>
                    <td>{Number(bill.gst_percent) > 0 ? `${Number(bill.gst_percent)}%` : "No"}</td>
                    <td>₹ {formatInr(bill.grand_total)}</td>
                    <td>
                      <Link to={`/bills/${bill.id}`}>View</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="history-cards mobile-only">
            {data.results.map((bill) => (
              <article className="history-card" key={bill.id}>
                <div>
                  <strong>{bill.bill_number}</strong>
                  <p>{formatDate(bill.bill_date)}</p>
                </div>
                <p>{bill.customer_name}</p>
                <p className="muted">{bill.shop_name}</p>
                <div className="history-card-foot">
                  <span>₹ {formatInr(bill.grand_total)}</span>
                  <Link to={`/bills/${bill.id}`}>View</Link>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
      <div className="pager">
        <button className="btn secondary" type="button" disabled={!data.previous} onClick={() => setPage((p) => Math.max(1, p - 1))}>
          Previous
        </button>
        <span>Page {page}</span>
        <button className="btn secondary" type="button" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>
          Next
        </button>
      </div>
    </section>
  );
}
