import { useRef, useState } from "react";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { formatDate, formatInr, formatQty, formatRupeesInWords, formatTime } from "../format";

const PAYMENT_LABELS = {
  cash: "Cash",
  upi: "UPI",
  card: "Card",
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

export default function Receipt({ bill, hideActions = false, printLabel = "Print" }) {
  const paperRef = useRef(null);
  const [downloading, setDownloading] = useState(false);

  if (!bill) return null;

  const grocery = bill.grocery_items || bill.items?.filter((item) => item.item_type === "grocery") || [];
  const extras = bill.adjustment_items || bill.items?.filter((item) => item.item_type === "adjustment") || [];
  const lines = [...grocery, ...extras];
  const withGst = Number(bill.gst_percent) > 0;
  const halfRate = Number(bill.gst_percent || 0) / 2;
  const { cgst, sgst } = splitCgstSgst(bill.gst_amount);
  const itemsTotal = Number(bill.subtotal || 0) + Number(bill.adjustment_total || 0);
  const payment = PAYMENT_LABELS[bill.payment_mode] || "Cash";

  async function downloadPdf() {
    if (!paperRef.current) return;
    setDownloading(true);
    try {
      const canvas = await html2canvas(paperRef.current, {
        scale: 2,
        backgroundColor: "#fffef8",
      });
      const image = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const pageWidth = 190;
      const pageHeight = (canvas.height * pageWidth) / canvas.width;
      pdf.addImage(image, "PNG", 10, 10, pageWidth, Math.min(pageHeight, 277));
      pdf.save(`${bill.bill_number}.pdf`);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <section className="receipt-wrap">
      <article className="receipt-paper" ref={paperRef}>
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
          {bill.created_at ? (
            <div>
              <span>Time</span>
              <strong>{formatTime(bill.created_at)}</strong>
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
