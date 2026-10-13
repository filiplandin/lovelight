// Every number the LinkedIn cut shows, with where it comes from. Re-check against a fresh replay before export.
import { DOCS, Doc, INJECTION } from "../data";

export { INJECTION };

// data/generated/bank.csv, row BT014.
export const LUMP = {
  id: "BT014",
  date: "29 sep",
  text: "LB LEVBET 3 ST",
  amount: -10863.75,
  reference: "88213456; FNX-2026-4471; 1042",
};

// data/generated/gold.json: gross and invoice_number of the three invoices BT014 pays.
export const LUMP_DOCS = [
  { vendor: "Telia Sverige AB", short: "Telia", ref: "88213456", gross: 4990, img: "telia_faktura_88213456.png" },
  { vendor: "Fortnox AB", short: "Fortnox", ref: "FNX-2026-4471", gross: 1873.75, img: "fortnox_faktura_4471.png" },
  { vendor: "Städbolaget Kvist AB", short: "Städbolaget", ref: "1042", gross: 4000, img: "faktura_stadbolaget_kvist_1042.png" },
];

// /api/state matches["m-BT014"].confidence_detail (conf-v2, gold-cache replay): components amount 1.0x0.4,
// reference 1.0x0.3, name 0.25x0.2, date 0.9x0.1 -> weighted mean 0.84; gate floor:reference+amount lifts it to
// 0.95, which is also pipeline.AUTO_APPROVE_MATCH. Paid 29 sep, all three due 30 sep.
export const WHY = {
  score: 95,
  weighted: 84,
  rows: [
    { label: "Amount", weight: 40, value: 1.0, pass: true, note: "exact to the last digit" },
    { label: "Reference", weight: 30, value: 1.0, pass: true, note: "3 of 3 quoted" },
    { label: "Vendor", weight: 20, value: 0.25, pass: false, note: "bank text has no name" },
    { label: "Date", weight: 10, value: 0.9, pass: true, note: "1 day before due" },
  ],
  rule: "All refs + exact sum → ≥ 95%",
};

// gold.json holds 26 documents. data.ts lists the original 23; the three receipts below were added later.
type LiDoc = Doc & { status: "posted" | "review" | "threat" };
const EXTRA: Doc[] = [
  { file: "kvitto_svepa_1005.pdf", img: "kvitto_svepa_1005.png", vendor: "Svepa Mobility AB", gross: 62, currency: "SEK", source: "upload" },
  { file: "kvitto_trampa_1007.pdf", img: "kvitto_trampa_1007.png", vendor: "Trampa Cykeldelning AB", gross: 45, currency: "SEK", source: "upload" },
  { file: "kvitto_nordvik_pendel_1006.pdf", img: "kvitto_nordvik_pendel_1006.png", vendor: "Nordvik Pendel AB", gross: 96, currency: "SEK", source: "upload" },
];
// Status from a gold-cache replay (/api/state): injection / iban_change / duplicate are threats (app.js THREAT_KINDS);
// the vat_mismatch receipt and the two client-entertainment photos (always routed to an accountant) are held for
// review. The other 20 are posted.
const STATUS: Record<string, LiDoc["status"]> = {
  "faktura_nordic_growth_partners_7781.pdf": "threat",
  "faktura_ringvagen_hyra_okt.pdf": "threat",
  "ljungbergs_faktura_30519.pdf": "threat",
  "kvitto_sl_30dagar_okt.pdf": "review",
  "IMG_4471.png": "review",
  "IMG_4538.png": "review",
};
export const LI_DOCS: LiDoc[] = [...DOCS, ...EXTRA].map((d) => ({ ...d, status: STATUS[d.file] ?? "posted" }));
export const DOC_COUNT = LI_DOCS.length; // 26
export const THREATS = LI_DOCS.filter((d) => d.status === "threat").length; // 3
export const REVIEW = LI_DOCS.filter((d) => d.status === "review").length; // 3
// /api/state stats.auto_posted_pct = 76.9 (20 of 26); the app header rounds it to 77%.
export const AUTO_POSTED = LI_DOCS.filter((d) => d.status === "posted").length; // 20
export const AUTO_POSTED_PCT = Math.round((100 * AUTO_POSTED) / DOC_COUNT); // 77

// /api/audit/verify on a fresh DB after one reset + replay: {ok: true, events: 758}. The chain is append-only, so
// every further reset/replay adds ~585 events; each clip was recorded on a fresh DB so all show 758.
export const AUDIT_EVENTS = 758;

// /api/state after the same fresh reset + gold-cache replay: reports.balance_sheet sums (assets 1510 + 1930;
// liabilities & equity 2440, 2611, 2614, 2640, 2645, 2099) and vouchers where sum(debit) == sum(credit).
export const BOOKS = { assets: 10833688.5, liabEquity: 10833688.5, vouchers: 169, balanced: 169 };

// Illustration of the audit chain: real SHA-256 over (prev hash + row text), first 8 hex chars.
// Row 2 tampered (4990.00 -> 9490.00) changes its own hash and every hash after it.
export const CHAIN = [
  { label: "doc.received", hash: "1f8b2c3e", bad: "1f8b2c3e" },
  { label: "doc.extracted", hash: "27a08cb1", bad: "4b9cd665" },
  { label: "voucher.posted", hash: "46edd30f", bad: "881fb8cc" },
  { label: "match.approved", hash: "9f08357c", bad: "a3617542" },
];

export const REPO_URL = "github.com/filiplandin/lovelight";
export const HACKATHON = "Built at the Light × Lovable × Grant Thornton hackathon, Stockholm";
