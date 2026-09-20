import { useRef, useState } from "react";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import {
  formatDate,
  formatInr,
  formatInrChargeableWords,
  formatInvoiceDate,
  formatQty,
  formatRupeesInWords,
  formatTime,
  stateFromGstin,
} from "../format";

const PAYMENT_LABELS = {
  cash: "Cash",
  upi: "UPI",
  card: "Card",
};

const TEMPLATES = {
  invoice: "invoice",
  tax_invoice: "tax_invoice",
  thermal: "thermal",
};

function formatGstPercent(value) {
  const amount = Number(value || 0);
  if (Number.isInteger(amount)) return String(amount);
  return amount.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

function splitCgstSgst(amount) {
  const paise = Math.round(Number(amount || 0) * 100);
  const cgst = Math.floor(paise / 2);
  return { cgst: cgst / 100, sgst: (paise - cgst) / 100 };
}

function billLines(bill) {
  const grocery = bill.grocery_items || bill.items?.filter((item) => item.item_type === "grocery") || [];
  const extras = bill.adjustment_items || bill.items?.filter((item) => item.item_type === "adjustment") || [];
  return [...grocery, ...extras];
}

function billClock(bill) {
  return bill.bill_time || bill.created_at || "";
}

function MetaPair({ label, value, strong = false }) {
  return (
    <div className="inv-meta-cell">
      <span>{label}</span>
      {strong ? <strong>{value || "\u00a0"}</strong> : <em>{value || "\u00a0"}</em>}
    </div>
  );
}

function InvoiceSheet({ bill, variant = "invoice" }) {
  const lines = billLines(bill);
  const withGst = Number(bill.gst_percent) > 0;
  const halfRate = Number(bill.gst_percent || 0) / 2;
  const { cgst, sgst } = splitCgstSgst(bill.gst_amount);
  const payment = PAYMENT_LABELS[bill.payment_mode] || "";
  const shopState = stateFromGstin(bill.gst_number);
  const buyerState = shopState;
  const isTax = variant === "tax_invoice";
  const title = isTax ? "TAX INVOICE" : "INVOICE";
  const showTaxRows = withGst;

  return (
    <article className={`receipt-paper invoice-paper ${isTax ? "tax-variant" : ""}`}>
      <h1 className="invoice-title">{title}</h1>
      <div className="invoice-grid">
        <section className="inv-party">
          <p className="inv-shop">{bill.shop_name}</p>
          <p>{bill.shop_address || "Local Market, Main Road"}</p>
          {bill.shop_phone ? <p>Ph: {bill.shop_phone}</p> : null}
          {bill.gst_number ? <p>GSTIN/UIN: {bill.gst_number}</p> : null}
          {shopState ? <p>{shopState.label}</p> : null}
        </section>
        <section className="inv-meta-grid">
          <MetaPair label="Invoice No." value={bill.bill_number} strong />
          <MetaPair label="Dated" value={formatInvoiceDate(bill.bill_date)} strong />
          <MetaPair label="Delivery Note" value="" />
          <MetaPair label="Mode/Terms of Payment" value={payment} />
          <MetaPair label="Supplier's Ref." value={bill.bill_number} />
          <MetaPair label="Other Reference(s)" value="" />
        </section>
        <section className="inv-party inv-buyer">
          <p className="inv-label">Buyer</p>
          <p className="inv-shop">{bill.customer_name}</p>
          {bill.customer_address ? <p>{bill.customer_address}</p> : null}
          {bill.customer_phone ? <p>Mob: {bill.customer_phone}</p> : null}
          {buyerState ? <p>{buyerState.label}</p> : null}
        </section>
        <section className="inv-meta-grid inv-dispatch">
          <MetaPair label="Buyer's Order No." value="" />
          <MetaPair label="Dated" value="" />
          <MetaPair label="Despatch Document No." value="" />
          <MetaPair label="Delivery Note Date" value="" />
          <MetaPair label="Despatched through" value="" />
          <MetaPair label="Destination" value="" />
          <div className="inv-meta-cell inv-terms">
            <span>Terms of Delivery</span>
            <em>&nbsp;</em>
          </div>
        </section>
      </div>

      <table className="invoice-table">
        <thead>
          <tr>
            <th className="col-sl">Sl No.</th>
            <th className="col-desc">Description of Goods</th>
            <th className="col-hsn">HSN/SAC</th>
            <th className="col-qty">Quantity</th>
            <th className="col-rate">Rate</th>
            <th className="col-per">per</th>
            <th className="col-amt">Amount</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((item, index) => (
            <tr key={item.id || `${item.name}-${index}`}>
              <td>{index + 1}</td>
              <td className="col-desc">
                <strong>{item.name}</strong>
              </td>
              <td />
              <td className="num">
                {formatQty(item.quantity)} {item.unit}
              </td>
              <td className="num">{formatInr(item.unit_price)}</td>
              <td>{item.unit}</td>
              <td className="num">{formatInr(item.total_price)}</td>
            </tr>
          ))}
          {showTaxRows ? (
            <>
              <tr className="tax-row">
                <td />
                <td className="col-desc">
                  <strong>CGST @ {formatGstPercent(halfRate)}%</strong>
                </td>
                <td />
                <td />
                <td />
                <td />
                <td className="num">{formatInr(cgst)}</td>
              </tr>
              <tr className="tax-row">
                <td />
                <td className="col-desc">
                  <strong>SGST @ {formatGstPercent(halfRate)}%</strong>
                </td>
                <td />
                <td />
                <td />
                <td />
                <td className="num">{formatInr(sgst)}</td>
              </tr>
            </>
          ) : null}
          <tr className="total-row">
            <td />
            <td className="col-desc">
              <strong>Total</strong>
            </td>
            <td />
            <td />
            <td />
            <td />
            <td className="num">
              <strong>₹ {formatInr(bill.grand_total)}</strong>
            </td>
          </tr>
        </tbody>
      </table>

      <div className="invoice-words">
        <div>
          <span>Amount Chargeable (in words)</span>
          <strong>{formatInrChargeableWords(bill.grand_total)}</strong>
        </div>
        <p className="eoe">E. &amp; O.E</p>
      </div>

      <div className="invoice-footer">
        <div className="inv-declaration">
          <p className="inv-label">Declaration</p>
          <p>
            We declare that this invoice shows the actual price of the goods described and that all
            particulars are true and correct.
          </p>
        </div>
        <div className="inv-sign">
          <p>
            for <strong>{bill.shop_name}</strong>
          </p>
          <span>Authorised Signatory</span>
        </div>
      </div>
      <p className="invoice-computer">This is computer generated invoice</p>
    </article>
  );
}

function ThermalSheet({ bill }) {
  const lines = billLines(bill);
  const withGst = Number(bill.gst_percent) > 0;
  const halfRate = Number(bill.gst_percent || 0) / 2;
  const { cgst, sgst } = splitCgstSgst(bill.gst_amount);
  const itemsTotal = Number(bill.subtotal || 0) + Number(bill.adjustment_total || 0);
  const payment = PAYMENT_LABELS[bill.payment_mode] || "Cash";
  const clock = billClock(bill);

  return (
    <article className="receipt-paper thermal-paper">
      <div className="cut-line">--------------------------------</div>
      <header className="receipt-header">
        <p className="invoice-kind">{withGst ? "Tax Invoice" : "Cash Memo"}</p>
        <p className="copy-mark">Original for Recipient</p>
        <h1>{bill.shop_name}</h1>
        <p>{bill.shop_address || "Local Market, Main Road"}</p>
        {bill.shop_phone ? <p>Ph: {bill.shop_phone}</p> : null}
        {bill.gst_number && withGst ? <p>GSTIN: {bill.gst_number}</p> : null}
      </header>
      <div className="receipt-meta">
        <div>
          <span>Bill No.</span>
          <strong>{bill.bill_number}</strong>
        </div>
        <div>
          <span>Date</span>
          <strong>{formatDate(bill.bill_date)}</strong>
        </div>
        {clock ? (
          <div>
            <span>Time</span>
            <strong>{formatTime(clock)}</strong>
          </div>
        ) : null}
      </div>
      <div className="billed-to">
        <p>
          Billed To: <strong>{bill.customer_name}</strong>
        </p>
        {bill.customer_address ? <span className="billed-address">{bill.customer_address}</span> : null}
        {bill.customer_phone ? <span className="billed-address">Mob: {bill.customer_phone}</span> : null}
      </div>
      <table className="receipt-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Particulars</th>
            <th>Qty</th>
            <th>Rate</th>
            <th>Amt</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((item, index) => (
            <tr key={item.id || `${item.name}-${item.quantity}-${index}`}>
              <td>{index + 1}</td>
              <td>{item.name}</td>
              <td>
                {formatQty(item.quantity)} {item.unit}
              </td>
              <td>{formatInr(item.unit_price)}</td>
              <td>{formatInr(item.total_price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <dl className="receipt-totals">
        {withGst ? (
          <>
            <div>
              <dt>Item Total</dt>
              <dd>₹ {formatInr(itemsTotal)}</dd>
            </div>
            <div>
              <dt>CGST ({formatGstPercent(halfRate)}%)</dt>
              <dd>₹ {formatInr(cgst)}</dd>
            </div>
            <div>
              <dt>SGST ({formatGstPercent(halfRate)}%)</dt>
              <dd>₹ {formatInr(sgst)}</dd>
            </div>
          </>
        ) : null}
        <div className="grand">
          <dt>Grand Total</dt>
          <dd>₹ {formatInr(bill.grand_total)}</dd>
        </div>
      </dl>
      <p className="amount-words">{formatRupeesInWords(bill.grand_total)}</p>
      <p className="payment-line">
        Mode of Payment: <strong>{payment}</strong>
      </p>
      <p className="disclaimer">Goods once sold will not be taken back.</p>
      <div className="receipt-sign">
        <span>Customer</span>
        <span>
          For {bill.shop_name}
          <em>Authorised Signatory</em>
        </span>
      </div>
      <p className="thanks">Thank you! Visit again.</p>
      <div className="cut-line">--------------------------------</div>
    </article>
  );
}

export default function Receipt({ bill, hideActions = false, printLabel = "Print", templateOverride }) {
  const paperRef = useRef(null);
  const [downloading, setDownloading] = useState(false);

  if (!bill) return null;

  const template = templateOverride || bill.receipt_template || TEMPLATES.invoice;
  const isThermal = template === TEMPLATES.thermal;

  async function downloadPdf() {
    if (!paperRef.current) return;
    setDownloading(true);
    try {
      const canvas = await html2canvas(paperRef.current, {
        scale: 2,
        backgroundColor: "#ffffff",
      });
      const image = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const pageWidth = isThermal ? 190 : 190;
      const pageHeight = (canvas.height * pageWidth) / canvas.width;
      let heightLeft = pageHeight;
      let position = 10;
      pdf.addImage(image, "PNG", 10, position, pageWidth, pageHeight);
      heightLeft -= 277;
      while (heightLeft > 0) {
        position = heightLeft - pageHeight + 10;
        pdf.addPage();
        pdf.addImage(image, "PNG", 10, position, pageWidth, pageHeight);
        heightLeft -= 277;
      }
      pdf.save(`${bill.bill_number}.pdf`);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <section className={`receipt-wrap ${isThermal ? "wrap-thermal" : "wrap-invoice"}`}>
      <div ref={paperRef}>
        {template === TEMPLATES.thermal ? (
          <ThermalSheet bill={bill} />
        ) : (
          <InvoiceSheet bill={bill} variant={template === TEMPLATES.tax_invoice ? "tax_invoice" : "invoice"} />
        )}
      </div>
      {!hideActions ? (
        <div className="receipt-actions no-print">
          <button type="button" className="btn secondary" onClick={() => window.print()}>
            {printLabel}
          </button>
          <button type="button" className="btn" onClick={downloadPdf} disabled={downloading}>
            {downloading ? "Preparing PDF…" : "Download PDF"}
          </button>
        </div>
      ) : null}
    </section>
  );
}
