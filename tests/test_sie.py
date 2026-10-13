from datetime import date
from decimal import Decimal as D

from lovelight.models import Voucher, VoucherLine
from lovelight.sie import to_sie4


def test_sie4_has_header_accounts_and_balanced_posted_vouchers():
    lines = [VoucherLine(account="5410", debit=D("100")), VoucherLine(account="2640", debit=D("25")),
             VoucherLine(account="1930", credit=D("125"))]
    posted = Voucher(id="V1", number=1, date=date(2026, 10, 1), description='Kjell "kabel"', lines=lines, status="posted")
    draft = Voucher(id="V2", number=2, date=date(2026, 10, 2), description="x", lines=lines)
    sie = to_sie4([posted, draft], "Lovelight Design AB", "559123-4567", 2026)
    for tag in ("#FLAGGA 0", "#FORMAT PC8", "#SIETYP 4", "#ORGNR 559123-4567", "#RAR 0 20260101 20261231",
                '#VER A 1 20261001 "Kjell \\"kabel\\""', "#TRANS 1930 {} -125.00"):
        assert tag in sie
    assert "#VER A 2" not in sie and sie.count("#KONTO") == 3
    assert sum(D(ln.split()[-1]) for ln in sie.splitlines() if "#TRANS" in ln) == 0
    sie.encode("cp437")
