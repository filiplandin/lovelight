"""SIE4 export (Swedish standard import format for Fortnox, Visma, etc.). Encode the result as cp437 (PC8)."""

from __future__ import annotations

from datetime import date

from lovelight.ledger import REPORTED_STATUSES
from lovelight.models import Voucher

ACCOUNT_NAMES = {
    "1510": "Kundfordringar", "1930": "Företagskonto", "2440": "Leverantörsskulder",
    "2611": "Utgående moms 25 %", "2640": "Ingående moms", "2099": "Årets resultat",
    "3001": "Försäljning inom Sverige 25 %", "3740": "Öres- och kronutjämning", "3960": "Valutakursvinster",
    "4010": "Inköp material och varor", "5010": "Lokalhyra", "5410": "Förbrukningsinventarier",
    "5420": "Programvaror", "5460": "Förbrukningsmaterial", "5611": "Drivmedel för personbilar",
    "5800": "Resekostnader", "5810": "Biljetter", "5831": "Kost och logi i Sverige", "5910": "Annonsering",
    "6071": "Representation, avdragsgill", "6110": "Kontorsmateriel", "6212": "Mobiltelefon",
    "6230": "Datakommunikation", "6250": "Postbefordran", "6530": "Redovisningstjänster",
    "6540": "IT-tjänster", "6550": "Konsultarvoden", "6570": "Bankkostnader", "6990": "Övriga externa kostnader",
    "7960": "Valutakursförluster",
}


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _d(d: date) -> str:
    return d.strftime("%Y%m%d")


def to_sie4(vouchers: list[Voucher], company_name: str, org_nr: str, year: int) -> str:
    posted = sorted((v for v in vouchers if v.status in REPORTED_STATUSES), key=lambda v: v.number)
    accounts = sorted({ln.account for v in posted for ln in v.lines})
    out = [
        "#FLAGGA 0",
        "#FORMAT PC8",
        "#SIETYP 4",
        _line("#PROGRAM", _q("Lovelight"), _q("0.1")),
        _line("#GEN", _d(date.today())),
        _line("#FNAMN", _q(company_name)),
        _line("#ORGNR", org_nr),
        _line("#RAR", "0", f"{year}0101", f"{year}1231"),
        "#KPTYP BAS2014",
    ]
    out += [_line("#KONTO", a, _q(ACCOUNT_NAMES.get(a, f"Konto {a}"))) for a in accounts]
    for v in posted:
        out.append(_line("#VER", "A", str(v.number), _d(v.date), _q(v.description)))
        out.append("{")
        for ln in v.lines:
            out.append(f"   #TRANS {ln.account} {{}} {ln.debit - ln.credit:.2f}")
        out.append("}")
    return "\r\n".join(out) + "\r\n"


def _line(*parts: str) -> str:
    return " ".join(parts)
