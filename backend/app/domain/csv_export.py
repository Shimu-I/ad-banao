"""Safe CSV writing. A cell that starts with = + - @ can run as a formula when the file is
opened in a spreadsheet, so such cells get a leading apostrophe. Names and emails are typed
by users, so every text cell goes through this."""

import csv
import io
from collections.abc import Iterable, Sequence

_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(_DANGEROUS):
        return "'" + text
    return text


def to_csv(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([csv_safe(v) for v in row])
    return buf.getvalue()
