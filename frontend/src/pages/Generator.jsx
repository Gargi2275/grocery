import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Receipt from "../components/Receipt";

const initialForm = {
  shop_name: "Sri Lakshmi Kirana",
  gst_number: "29ABCDE1234F1Z5",
  customer_name: "",
  max_amount: "1500",
  date_mode: "fixed",
  bill_date: new Date().toISOString().slice(0, 10),
  date_range_start: "",
  date_range_end: "",
  product_mode: "random",
  bill_count: "1",
  apply_gst: true,
  gst_percent: "5",
  shop_address: "Local Market, Main Road",
  shop_phone: "",
  customer_address: "",
  customer_phone: "",
  payment_mode: "cash",
};

export default function Generator() {
  const { token, logout } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [bills, setBills] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [catalog, setCatalog] = useState({ grocery: [], adjustments: [], prices_updated_at: null });
  const [selected, setSelected] = useState({});
  const [productQuery, setProductQuery] = useState("");
  const [refreshingPrices, setRefreshingPrices] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadCatalog() {
      try {
        const data = await api("/api/catalog/", { token });
        if (!cancelled) setCatalog(data);
      } catch (err) {
        if (err.status === 401) {
          logout();
        }
      }
    }
    loadCatalog();
    return () => {
      cancelled = true;
    };
  }, [token, logout]);

  async function refreshPrices() {
    setError("");
    setRefreshingPrices(true);
    try {
      const data = await api("/api/catalog/refresh-prices/", { method: "POST", token });
      setCatalog(data);
    } catch (err) {
      if (err.status === 401) {
        logout();
        return;
      }
      setError(err.message || "Could not update prices.");
    } finally {
      setRefreshingPrices(false);
    }
  }

  const selectedCount = Object.keys(selected).length;

  const filteredGrocery = useMemo(
    () => filterCatalog(catalog.grocery, productQuery),
    [catalog.grocery, productQuery],
  );
  const filteredAdjustments = useMemo(
    () => filterCatalog(catalog.adjustments, productQuery),
    [catalog.adjustments, productQuery],
  );

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function toggleProduct(item) {
    setSelected((current) => {
      if (current[item.name] != null) {
        const next = { ...current };
        delete next[item.name];
        return next;
      }
      return { ...current, [item.name]: item.qty_options[0] };
    });
  }

  function setQty(name, quantity) {
    setSelected((current) => ({ ...current, [name]: quantity }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const groceryNames = new Set(catalog.grocery.map((item) => item.name));
    const grocerySelected = Object.keys(selected).some((name) => groceryNames.has(name));
    const count = Math.max(1, Math.min(25, Number(form.bill_count) || 1));
    if (form.product_mode === "select" && !grocerySelected) {
      setError("Select at least one grocery product, or switch to random.");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        shop_name: form.shop_name,
        gst_number: form.apply_gst ? form.gst_number : "",
        customer_name: form.customer_name,
        max_amount: form.max_amount,
        date_mode: form.date_mode,
        product_mode: form.product_mode,
        count,
        apply_gst: form.apply_gst,
        gst_percent: form.apply_gst ? form.gst_percent || "0" : "0",
        shop_address: form.shop_address,
        shop_phone: form.shop_phone,
        customer_address: form.customer_address,
        customer_phone: form.customer_phone,
        payment_mode: form.payment_mode,
      };
      if (form.date_mode === "fixed" || (form.date_mode === "monthly" && form.bill_date)) {
        payload.bill_date = form.bill_date || null;
      }
      if (form.date_mode === "random") {
        if (form.date_range_start) payload.date_range_start = form.date_range_start;
        if (form.date_range_end) payload.date_range_end = form.date_range_end;
      }
      if (form.product_mode === "select") {
        payload.selected_products = Object.entries(selected).map(([name, quantity]) => ({
          name,
          quantity,
        }));
      }
      const data = await api("/api/generate-bill/", {
        method: "POST",
        body: payload,
        token,
      });
      const nextBills = data.bills || (data.id ? [data] : []);
      setBills(nextBills);
      setActiveIndex(0);
    } catch (err) {
      if (err.status === 401) {
        logout();
        return;
      }
      setError(err.message || "Could not generate bill.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-grid">
      <form className="panel no-print" onSubmit={handleSubmit}>
        <h2>New bill</h2>
        <p className="muted">Enter shop details and a maximum amount.</p>
        <div className="form-grid">
          <label>
            Shop name
            <input value={form.shop_name} onChange={(e) => update("shop_name", e.target.value)} required />
          </label>
          <label>
            Shop address
            <input
              value={form.shop_address}
              onChange={(e) => update("shop_address", e.target.value)}
              placeholder="Street, area, city"
            />
          </label>
          <label>
            Shop phone
            <input
              value={form.shop_phone}
              onChange={(e) => update("shop_phone", e.target.value)}
              placeholder="Optional"
            />
          </label>
          <div className="product-mode">
            <span>GST</span>
            <div className="mode-toggle" role="group" aria-label="GST option">
              <button
                type="button"
                className={form.apply_gst ? "active" : ""}
                onClick={() => update("apply_gst", true)}
              >
                Include GST
              </button>
              <button
                type="button"
                className={!form.apply_gst ? "active" : ""}
                onClick={() => update("apply_gst", false)}
              >
                No GST
              </button>
            </div>
          </div>
          {form.apply_gst ? (
            <>
              <label>
                GST rate (%)
                <input
                  type="number"
                  min="0"
                  max="40"
                  step="0.01"
                  value={form.gst_percent}
                  onChange={(e) => update("gst_percent", e.target.value)}
                  required
                />
              </label>
              <label>
                GST number
                <input
                  value={form.gst_number}
                  onChange={(e) => update("gst_number", e.target.value)}
                  placeholder="Optional GSTIN"
                />
              </label>
            </>
          ) : (
            <p className="span-2 muted field-hint">GST will be left off this bill.</p>
          )}
          <label className="span-2">
            Customer name
            <input
              value={form.customer_name}
              onChange={(e) => update("customer_name", e.target.value)}
              placeholder={Number(form.bill_count) > 1 ? "Ravi, Sita, Mohan" : ""}
              required
            />
          </label>
          <label className="span-2">
            Customer address
            <textarea
              rows={2}
              value={form.customer_address}
              onChange={(e) => update("customer_address", e.target.value)}
              placeholder="House / street, area, city"
            />
          </label>
          <label>
            Customer mobile
            <input
              value={form.customer_phone}
              onChange={(e) => update("customer_phone", e.target.value)}
              placeholder="Optional"
            />
          </label>
          <label>
            Payment
            <select value={form.payment_mode} onChange={(e) => update("payment_mode", e.target.value)}>
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="card">Card</option>
            </select>
          </label>
          {Number(form.bill_count) > 1 ? (
            <p className="span-2 muted field-hint">
              Separate several customer names with commas. One name is reused on every bill.
            </p>
          ) : null}
          <label>
            Max amount
            <input
              type="number"
              min="1"
              step="0.01"
              value={form.max_amount}
              onChange={(e) => update("max_amount", e.target.value)}
              required
            />
          </label>
          <label>
            Number of bills
            <input
              type="number"
              min="1"
              max="25"
              step="1"
              value={form.bill_count}
              onChange={(e) => update("bill_count", e.target.value)}
              required
            />
          </label>
          <label>
            Date mode
            <select value={form.date_mode} onChange={(e) => update("date_mode", e.target.value)}>
              <option value="fixed">Fixed date</option>
              <option value="monthly">Monthly</option>
              <option value="random">Random</option>
            </select>
          </label>
          {form.date_mode === "fixed" && (
            <label className="span-2">
              Bill date
              <input type="date" value={form.bill_date} onChange={(e) => update("bill_date", e.target.value)} required />
            </label>
          )}
          {form.date_mode === "monthly" && (
            <label className="span-2">
              Day of month
              <input type="date" value={form.bill_date} onChange={(e) => update("bill_date", e.target.value)} />
            </label>
          )}
          {form.date_mode === "random" && (
            <>
              <label>
                Range start
                <input
                  type="date"
                  value={form.date_range_start}
                  onChange={(e) => update("date_range_start", e.target.value)}
                />
              </label>
              <label>
                Range end
                <input
                  type="date"
                  value={form.date_range_end}
                  onChange={(e) => update("date_range_end", e.target.value)}
                />
              </label>
            </>
          )}
          <div className="span-2 price-bar">
            <p className="muted">
              {catalog.prices_updated_at
                ? `Live unit prices updated ${formatPriceTime(catalog.prices_updated_at)}. Google is tried first; official all-India retail rates fill in when Google blocks bots.`
                : "Unit prices are the last saved market rates. Update them from Google before generating."}
            </p>
            <button
              type="button"
              className="btn secondary"
              onClick={refreshPrices}
              disabled={refreshingPrices || busy}
            >
              {refreshingPrices ? "Updating prices…" : "Update prices from Google"}
            </button>
          </div>
          <div className="span-2 product-mode">
            <span>Products</span>
            <div className="mode-toggle" role="group" aria-label="Product selection mode">
              <button
                type="button"
                className={form.product_mode === "random" ? "active" : ""}
                onClick={() => update("product_mode", "random")}
              >
                Random
              </button>
              <button
                type="button"
                className={form.product_mode === "select" ? "active" : ""}
                onClick={() => update("product_mode", "select")}
              >
                Select products
              </button>
            </div>
          </div>
          {form.product_mode === "select" && (
            <div className="span-2 product-picker">
              <div className="product-picker-toolbar">
                <input
                  type="search"
                  placeholder="Search products"
                  value={productQuery}
                  onChange={(e) => setProductQuery(e.target.value)}
                />
                <p className="muted product-count">
                  {selectedCount} selected
                  {selectedCount > 0 ? (
                    <button type="button" className="text-btn" onClick={() => setSelected({})}>
                      Clear
                    </button>
                  ) : null}
                </p>
              </div>
              <ProductGroup
                title="Grocery"
                items={filteredGrocery}
                selected={selected}
                onToggle={toggleProduct}
                onQty={setQty}
              />
              <ProductGroup
                title="Extras"
                items={filteredAdjustments}
                selected={selected}
                onToggle={toggleProduct}
                onQty={setQty}
              />
              {!filteredGrocery.length && !filteredAdjustments.length ? (
                <p className="muted">No products match that search.</p>
              ) : null}
            </div>
          )}
        </div>
        {error ? <p className="form-error">{error}</p> : null}
        <button className="btn" type="submit" disabled={busy}>
          {busy
            ? "Generating…"
            : Number(form.bill_count) > 1
              ? `Generate ${form.bill_count} bills`
              : "Generate bill"}
        </button>
      </form>
      {bills.length > 0 ? (
        <div className="receipt-stack">
          {bills.length > 1 ? (
            <div className="bill-switcher no-print">
              <button
                type="button"
                className="btn secondary"
                onClick={() => setActiveIndex((index) => Math.max(0, index - 1))}
                disabled={activeIndex === 0}
              >
                Previous
              </button>
              <p>
                Bill {activeIndex + 1} of {bills.length}
                <span className="muted"> {bills[activeIndex].bill_number}</span>
              </p>
              <button
                type="button"
                className="btn secondary"
                onClick={() => setActiveIndex((index) => Math.min(bills.length - 1, index + 1))}
                disabled={activeIndex === bills.length - 1}
              >
                Next
              </button>
            </div>
          ) : null}
          <div className="receipt-preview">
            <Receipt bill={bills[activeIndex]} printLabel={bills.length > 1 ? "Print all" : "Print"} />
          </div>
          {bills.length > 1 ? (
            <div className="receipt-print-all">
              {bills.map((item) => (
                <Receipt key={item.id} bill={item} hideActions />
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="empty-receipt no-print">
          <h3>Receipt</h3>
          <p>Generate a bill to preview it here.</p>
        </div>
      )}
    </div>
  );
}

function ProductGroup({ title, items, selected, onToggle, onQty }) {
  if (!items.length) return null;
  return (
    <section className="product-group">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => {
          const checked = selected[item.name] != null;
          return (
            <li key={item.name} className={checked ? "selected" : ""}>
              <label>
                <input type="checkbox" checked={checked} onChange={() => onToggle(item)} />
                <span className="product-name">{item.name}</span>
                <span className="product-meta">
                  ₹ {item.unit_price} / {item.unit}
                </span>
              </label>
              {checked ? (
                <select value={selected[item.name]} onChange={(e) => onQty(item.name, e.target.value)}>
                  {item.qty_options.map((qty) => (
                    <option key={qty} value={qty}>
                      {qty} {item.unit}
                    </option>
                  ))}
                </select>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function filterCatalog(items, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return items;
  return items.filter((item) => item.name.toLowerCase().includes(needle));
}

function formatPriceTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
