import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import Receipt from "../components/Receipt";

function localIsoDate(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const initialForm = {
  shop_name: "Sri Lakshmi Kirana",
  gst_number: "29ABCDE1234F1Z5",
  customer_name: "",
  max_amount: "1500",
  date_mode: "fixed",
  bill_date: localIsoDate(),
  date_range_start: localIsoDate(new Date(new Date().getFullYear(), new Date().getMonth() - 2, 1)),
  date_range_end: localIsoDate(),
  product_mode: "random",
  bill_count: "1",
  apply_gst: true,
  gst_percent: "5",
  shop_address: "Local Market, Main Road",
  shop_phone: "",
  customer_address: "",
  customer_phone: "",
  payment_mode: "cash",
  receipt_template: "invoice",
};

export default function Generator() {
  const { token, logout } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [bills, setBills] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [catalog, setCatalog] = useState({ grocery: [], adjustments: [], prices_updated_at: null, units: ["kg", "g", "ltr", "ml", "pcs"] });
  const [selected, setSelected] = useState({});
  const [productQuery, setProductQuery] = useState("");
  const [refreshingPrices, setRefreshingPrices] = useState(false);
  const [savingProduct, setSavingProduct] = useState(false);
  const [newProduct, setNewProduct] = useState({ name: "", unit: "kg", unit_price: "", item_type: "grocery" });

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

  const customItems = useMemo(
    () => [...(catalog.grocery || []), ...(catalog.adjustments || [])].filter((item) => item.custom),
    [catalog.grocery, catalog.adjustments],
  );
  const selectedCount = Object.keys(selected).length;

  async function addProduct(event) {
    event.preventDefault();
    event.stopPropagation();
    setError("");
    if (!newProduct.name.trim() || !newProduct.unit_price) {
      setError("Enter a product name, unit, and price.");
      return;
    }
    setSavingProduct(true);
    try {
      const data = await api("/api/catalog/products/", {
        method: "POST",
        token,
        body: {
          name: newProduct.name.trim(),
          unit: newProduct.unit,
          unit_price: newProduct.unit_price,
          item_type: newProduct.item_type,
        },
      });
      setCatalog(data);
      setNewProduct({ name: "", unit: newProduct.unit, unit_price: "", item_type: "grocery" });
    } catch (err) {
      if (err.status === 401) {
        logout();
        return;
      }
      setError(err.message || "Could not add product.");
    } finally {
      setSavingProduct(false);
    }
  }

  async function removeProduct(name) {
    setError("");
    try {
      const data = await api("/api/catalog/products/", {
        method: "DELETE",
        token,
        body: { name },
      });
      setCatalog(data);
      setSelected((current) => {
        if (current[name] == null) return current;
        const next = { ...current };
        delete next[name];
        return next;
      });
    } catch (err) {
      if (err.status === 401) {
        logout();
        return;
      }
      setError(err.message || "Could not remove product.");
    }
  }

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
      return { ...current, [item.name]: item.qty_options?.[0] || "1" };
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
    if (form.date_mode === "monthly" && (!form.date_range_start || !form.date_range_end)) {
      setError("Choose a start range and end range for monthly bills.");
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
        receipt_template: form.receipt_template,
      };
      if (form.date_mode === "fixed") {
        payload.bill_date = form.bill_date || null;
      }
      if (form.date_mode === "monthly" || form.date_mode === "random") {
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
          <div className="span-2 product-mode">
            <span>Bill template</span>
            <div className="mode-toggle template-toggle" role="group" aria-label="Bill template">
              <button
                type="button"
                className={form.receipt_template === "invoice" ? "active" : ""}
                onClick={() => update("receipt_template", "invoice")}
              >
                Standard Invoice
              </button>
              <button
                type="button"
                className={form.receipt_template === "tax_invoice" ? "active" : ""}
                onClick={() => update("receipt_template", "tax_invoice")}
              >
                Tax Invoice
              </button>
              <button
                type="button"
                className={form.receipt_template === "thermal" ? "active" : ""}
                onClick={() => update("receipt_template", "thermal")}
              >
                Thermal Memo
              </button>
            </div>
            <p className="muted field-hint">
              Standard Invoice matches the mandatory grocery bill format. Each bill gets its own date and time.
            </p>
          </div>
          {Number(form.bill_count) > 1 || form.date_mode === "monthly" ? (
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
          {form.date_mode !== "monthly" ? (
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
          ) : (
            <p className="muted field-hint">One bill is generated for each month in the time period.</p>
          )}
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
          {(form.date_mode === "monthly" || form.date_mode === "random") && (
            <>
              <label>
                Start range
                <input
                  type="date"
                  value={form.date_range_start}
                  onChange={(e) => update("date_range_start", e.target.value)}
                  required={form.date_mode === "monthly"}
                />
              </label>
              <label>
                End range
                <input
                  type="date"
                  value={form.date_range_end}
                  onChange={(e) => update("date_range_end", e.target.value)}
                  required={form.date_mode === "monthly"}
                />
              </label>
              {form.date_mode === "monthly" ? (
                <p className="span-2 muted field-hint">
                  One grocery bill is created for each month between start range and end range.
                </p>
              ) : null}
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
            <div className="add-product">
              <p className="add-product-title">Add product price</p>
              <p className="muted field-hint">
                Save a rate per kg, g, ltr, ml, or pcs. Custom products are included when bills are generated.
              </p>
              <div className="add-product-grid">
                <label>
                  Product name
                  <input
                    value={newProduct.name}
                    onChange={(e) => setNewProduct((current) => ({ ...current, name: e.target.value }))}
                    placeholder="Ghee"
                  />
                </label>
                <label>
                  Unit
                  <select
                    value={newProduct.unit}
                    onChange={(e) => setNewProduct((current) => ({ ...current, unit: e.target.value }))}
                  >
                    {(catalog.units || ["kg", "g", "ltr", "ml", "pcs"]).map((unit) => (
                      <option key={unit} value={unit}>
                        {UNIT_LABELS[unit] || unit}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Price per {newProduct.unit}
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={newProduct.unit_price}
                    onChange={(e) => setNewProduct((current) => ({ ...current, unit_price: e.target.value }))}
                    placeholder="0.00"
                  />
                </label>
                <label>
                  Type
                  <select
                    value={newProduct.item_type}
                    onChange={(e) => setNewProduct((current) => ({ ...current, item_type: e.target.value }))}
                  >
                    <option value="grocery">Grocery</option>
                    <option value="adjustment">Extra</option>
                  </select>
                </label>
                <button type="button" className="btn secondary" onClick={addProduct} disabled={savingProduct || busy}>
                  {savingProduct ? "Saving…" : "Add product"}
                </button>
              </div>
              {customItems.length ? (
                <ul className="custom-product-list">
                  {customItems.map((item) => (
                    <li key={item.name}>
                      <span>
                        {item.name}
                        <em>
                          ₹ {item.unit_price} / {item.unit}
                        </em>
                      </span>
                      <button type="button" className="text-btn" onClick={() => removeProduct(item.name)}>
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
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
            <p className="muted field-hint">
              {form.product_mode === "random"
                ? "Each generated bill gets a different mix of products and quantities — not the same items on every bill."
                : Number(form.bill_count) > 1 || form.date_mode === "monthly"
                  ? "Selected products are the pool. Each bill randomly picks a different subset and quantity."
                  : "This bill will use the products you tick below."}
            </p>
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
                onRemove={removeProduct}
              />
              <ProductGroup
                title="Extras"
                items={filteredAdjustments}
                selected={selected}
                onToggle={toggleProduct}
                onQty={setQty}
                onRemove={removeProduct}
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
            : form.date_mode === "monthly"
              ? "Generate monthly bills"
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
          <h3>Invoice preview</h3>
          <p>Generate a bill to preview it here.</p>
        </div>
      )}
    </div>
  );
}

function ProductGroup({ title, items, selected, onToggle, onQty, onRemove }) {
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
                  {item.custom ? " · custom" : ""}
                </span>
              </label>
              {checked ? (
                <select value={selected[item.name]} onChange={(e) => onQty(item.name, e.target.value)}>
                  {(item.qty_options || ["1"]).map((qty) => (
                    <option key={qty} value={qty}>
                      {qty} {item.unit}
                    </option>
                  ))}
                </select>
              ) : item.custom ? (
                <button type="button" className="text-btn" onClick={() => onRemove(item.name)}>
                  Remove
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

const UNIT_LABELS = {
  kg: "kg",
  g: "gram (g)",
  ltr: "liter (ltr)",
  ml: "ml",
  pcs: "pcs",
};

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
