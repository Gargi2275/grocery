import { useState, useEffect, useMemo } from "react";
import { api } from "../api";

const UNIT_INFO = {
  kg: { label: "kg (Kilogram)", presets: "0.25, 0.5, 1, 2, 5 kg" },
  g: { label: "g (Gram)", presets: "50, 100, 200, 250, 500 g" },
  ltr: { label: "ltr (Liter)", presets: "0.25, 0.5, 1, 2 ltr" },
  ml: { label: "ml (Milliliter)", presets: "100, 200, 500, 1000 ml" },
  pcs: { label: "pcs (Pieces / Units)", presets: "1, 2, 3, 6 pcs" },
};

export default function ProductModal({
  isOpen,
  onClose,
  catalog,
  onCatalogChange,
  token,
  onProductDeleted,
  initialEditItem = null,
}) {
  const [activeTab, setActiveTab] = useState("form"); // 'form' or 'list'
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    unit: "kg",
    unit_price: "",
    item_type: "grocery",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("all"); // 'all', 'custom', 'grocery', 'adjustment'

  // Initialize or reset when initialEditItem changes or modal opens
  useEffect(() => {
    if (initialEditItem) {
      setEditingItem(initialEditItem);
      setFormData({
        name: initialEditItem.name,
        unit: initialEditItem.unit || "kg",
        unit_price: initialEditItem.unit_price || "",
        item_type: initialEditItem.item_type || (catalog.adjustments?.some((i) => i.name === initialEditItem.name) ? "adjustment" : "grocery"),
      });
      setActiveTab("form");
      setError("");
      setSuccess("");
    } else if (isOpen) {
      resetForm();
    }
  }, [initialEditItem, isOpen]);

  // Handle escape key
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  function resetForm() {
    setEditingItem(null);
    setFormData({
      name: "",
      unit: "kg",
      unit_price: "",
      item_type: "grocery",
    });
    setError("");
    setSuccess("");
  }

  function handleStartEdit(item) {
    const isAdjustment = catalog.adjustments?.some((i) => i.name === item.name);
    setEditingItem(item);
    setFormData({
      name: item.name,
      unit: item.unit,
      unit_price: item.unit_price,
      item_type: item.item_type || (isAdjustment ? "adjustment" : "grocery"),
    });
    setActiveTab("form");
    setError("");
    setSuccess("");
  }

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    const name = formData.name.trim();
    const price = parseFloat(formData.unit_price);

    if (!name) {
      setError("Please provide a product name.");
      return;
    }
    if (isNaN(price) || price <= 0) {
      setError("Please enter a valid price greater than 0.");
      return;
    }

    setBusy(true);
    try {
      const payload = {
        name,
        unit: formData.unit,
        unit_price: formData.unit_price,
        item_type: formData.item_type,
      };

      if (editingItem) {
        payload.original_name = editingItem.name;
      }

      const updatedCatalog = await api("/api/catalog/products/", {
        method: editingItem ? "PUT" : "POST",
        token,
        body: payload,
      });

      onCatalogChange(updatedCatalog);
      setSuccess(
        editingItem
          ? `Product "${name}" updated successfully.`
          : `Product "${name}" added to catalog.`
      );

      if (editingItem) {
        setEditingItem(null);
      }
      setFormData({
        name: "",
        unit: formData.unit,
        unit_price: "",
        item_type: formData.item_type,
      });
    } catch (err) {
      setError(err.message || "Failed to save product.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(name) {
    if (!window.confirm(`Are you sure you want to remove "${name}" from the product list?`)) {
      return;
    }

    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const updatedCatalog = await api("/api/catalog/products/", {
        method: "DELETE",
        token,
        body: { name },
      });
      onCatalogChange(updatedCatalog);
      if (onProductDeleted) {
        onProductDeleted(name);
      }
      setSuccess(`Removed "${name}".`);
      if (editingItem && editingItem.name.toLowerCase() === name.toLowerCase()) {
        resetForm();
      }
    } catch (err) {
      setError(err.message || "Failed to delete product.");
    } finally {
      setBusy(false);
    }
  }

  const allItems = [
    ...(catalog.grocery || []).map((i) => ({ ...i, item_type: "grocery" })),
    ...(catalog.adjustments || []).map((i) => ({ ...i, item_type: "adjustment" })),
  ];

  const customItems = allItems.filter((i) => i.custom);

  const filteredItems = allItems.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.trim().toLowerCase());
    if (!matchesSearch) return false;
    if (filterType === "custom") return item.custom;
    if (filterType === "grocery") return item.item_type === "grocery";
    if (filterType === "adjustment") return item.item_type === "adjustment";
    return true;
  });

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2 className="modal-title">Product Catalog & Rates</h2>
            <p className="muted modal-subtitle">
              Add new custom items, update rates, or manage product catalogue.
            </p>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        <div className="modal-tabs">
          <button
            type="button"
            className={`modal-tab ${activeTab === "form" ? "active" : ""}`}
            onClick={() => setActiveTab("form")}
          >
            {editingItem ? "✏️ Edit Product" : "＋ Add Product"}
          </button>
          <button
            type="button"
            className={`modal-tab ${activeTab === "list" ? "active" : ""}`}
            onClick={() => setActiveTab("list")}
          >
            📋 Manage Products ({allItems.length})
            {customItems.length > 0 && <span className="tab-pill">{customItems.length} custom</span>}
          </button>
        </div>

        {error && <div className="modal-alert error">{error}</div>}
        {success && <div className="modal-alert success">{success}</div>}

        <div className="modal-body">
          {activeTab === "form" ? (
            <form onSubmit={handleSave} className="product-modal-form">
              {editingItem && (
                <div className="edit-banner">
                  <span>
                    Editing <strong>{editingItem.name}</strong>
                  </span>
                  <button type="button" className="text-btn cancel-edit-btn" onClick={resetForm}>
                    Cancel Edit (Create New Instead)
                  </button>
                </div>
              )}

              <div className="form-group-row">
                <label className="span-full">
                  <span>Product Name <strong className="req">*</strong></span>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Pure Ghee, Aashirvaad Atta, Surf Excel"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    autoFocus
                  />
                </label>
              </div>

              <div className="form-group-row two-col">
                <label>
                  <span>Category / Purpose</span>
                  <select
                    value={formData.item_type}
                    onChange={(e) => setFormData({ ...formData, item_type: e.target.value })}
                  >
                    <option value="grocery">🌾 Grocery Item (Main invoice staple)</option>
                    <option value="adjustment">🍬 Extra / Adjustment (Small add-ons)</option>
                  </select>
                </label>

                <label>
                  <span>Measurement Unit</span>
                  <select
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                  >
                    {(catalog.units || ["kg", "g", "ltr", "ml", "pcs"]).map((unit) => (
                      <option key={unit} value={unit}>
                        {UNIT_INFO[unit]?.label || unit}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="form-group-row two-col">
                <label>
                  <span>Price per {formData.unit} (₹) <strong className="req">*</strong></span>
                  <div className="price-input-wrap">
                    <span className="currency-symbol">₹</span>
                    <input
                      type="number"
                      required
                      min="0.01"
                      step="0.01"
                      placeholder="0.00"
                      value={formData.unit_price}
                      onChange={(e) => setFormData({ ...formData, unit_price: e.target.value })}
                    />
                  </div>
                </label>

                <div className="unit-preview-box">
                  <span className="unit-preview-title">Suggested Purchase Sizes</span>
                  <span className="unit-preview-text">
                    {UNIT_INFO[formData.unit]?.presets || "1, 2, 5 units"}
                  </span>
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn secondary" onClick={onClose} disabled={busy}>
                  Close
                </button>
                <button type="submit" className="btn primary" disabled={busy}>
                  {busy ? "Saving…" : editingItem ? "Save Changes" : "＋ Add Product to Catalog"}
                </button>
              </div>
            </form>
          ) : (
            <div className="product-manager-list">
              <div className="manager-toolbar">
                <input
                  type="search"
                  placeholder="Search products by name…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="manager-search"
                />
                <div className="filter-chips">
                  <button
                    type="button"
                    className={`filter-chip ${filterType === "all" ? "active" : ""}`}
                    onClick={() => setFilterType("all")}
                  >
                    All ({allItems.length})
                  </button>
                  <button
                    type="button"
                    className={`filter-chip ${filterType === "custom" ? "active" : ""}`}
                    onClick={() => setFilterType("custom")}
                  >
                    Custom ({customItems.length})
                  </button>
                  <button
                    type="button"
                    className={`filter-chip ${filterType === "grocery" ? "active" : ""}`}
                    onClick={() => setFilterType("grocery")}
                  >
                    Grocery ({catalog.grocery?.length || 0})
                  </button>
                  <button
                    type="button"
                    className={`filter-chip ${filterType === "adjustment" ? "active" : ""}`}
                    onClick={() => setFilterType("adjustment")}
                  >
                    Extras ({catalog.adjustments?.length || 0})
                  </button>
                </div>
              </div>

              <div className="products-table-wrap">
                {filteredItems.length === 0 ? (
                  <div className="empty-catalog-state">
                    <p>No products match your search or filter.</p>
                    <button
                      type="button"
                      className="btn secondary"
                      onClick={() => {
                        setSearchQuery("");
                        setFilterType("all");
                      }}
                    >
                      Clear Filters
                    </button>
                  </div>
                ) : (
                  <table className="products-table">
                    <thead>
                      <tr>
                        <th>Product Name</th>
                        <th>Type</th>
                        <th>Unit Rate</th>
                        <th style={{ textAlign: "right" }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredItems.map((item) => (
                        <tr key={item.name} className={item.custom ? "custom-row" : ""}>
                          <td>
                            <span className="product-cell-name">{item.name}</span>
                            {item.custom && <span className="badge-custom">Custom</span>}
                          </td>
                          <td>
                            <span className={`badge-type ${item.item_type}`}>
                              {item.item_type === "grocery" ? "Grocery" : "Extra"}
                            </span>
                          </td>
                          <td className="product-price-cell">
                            <strong>₹ {item.unit_price}</strong> / {item.unit}
                          </td>
                          <td style={{ textAlign: "right" }}>
                            <div className="row-actions">
                              <button
                                type="button"
                                className="action-btn edit"
                                title="Edit product rate or details"
                                onClick={() => handleStartEdit(item)}
                              >
                                ✏️ Edit
                              </button>
                              <button
                                type="button"
                                className="action-btn delete"
                                title="Delete or remove product"
                                onClick={() => handleDelete(item.name)}
                              >
                                🗑️ Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
