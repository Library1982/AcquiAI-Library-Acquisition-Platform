"""Admin-only offline selection imports and combined selection export."""
import io
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd
from docx import Document
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func

from database import SessionLocal
from models import Book, Selector, SelectionCart, SelectionItem

router = APIRouter()
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_ROWS = 15000

def clean(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip()

def norm(v):
    s = unicodedata.normalize("NFKC", clean(v)).lower()
    s = re.sub(r"[\u064b-\u065f\u0670ـ]", "", s)
    return re.sub(r"[^\w]+", "", s, flags=re.UNICODE)

ALIASES = {
    "title": ["Title", "Book Title", "عنوان الكتاب", "العنوان", "اسم الكتاب", "الكتاب"],
    "author": ["Author", "المؤلف", "اسم المؤلف", "المؤلف / المحقق"],
    "publisher": ["Publisher", "الناشر", "دار النشر", "اسم الناشر"],
    "isbn": ["ISBN", "ردمك", "الرقم الدولي"],
    "price": ["Price", "السعر"],
    "currency": ["Currency", "العملة"],
    "year": ["Publication Year", "سنة النشر", "عام النشر"],
    "subject": ["Subject", "الموضوع"],
    "language": ["Language", "اللغة"],
    "selector": ["Selected By", "اسم القائم بالاختيار", "القائم بالاختيار", "اسم المختار", "المختار"],
    "selected": ["Selected", "Selection", "اختيار", "تم الاختيار", "محدد", "selected?"],
}
def mapped(columns):
    by_key = {norm(c): c for c in columns}
    return {key: next((by_key[norm(a)] for a in names if norm(a) in by_key), None)
                 for key, names in ALIASES.items()}

def selected_flag(v):
    return norm(v) in {"yes", "y", "true", "1", "selected", "نعم", "صح", "محدد", "اختيار", "✓", "✔"}

def parse_excel(raw, ext, fallback_name):
    xls = pd.ExcelFile(io.BytesIO(raw), engine="xlrd" if ext == ".xls" else "openpyxl")
    records, issues = [], []
    for sheet in xls.sheet_names:
        if norm(sheet) in {norm(x) for x in ["Selection Summary", "Review Required", "ملخص الاختيارات"]}:
            continue
        preview = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=18, dtype=object)
        header_idx = 0
        best = -1
        for idx, row in preview.iterrows():
            m = mapped(row.tolist())
            score = sum(bool(m[k]) for k in ("title", "author", "publisher", "selector"))
            if score > best:
                header_idx, best = idx, score
        df = pd.read_excel(xls, sheet_name=sheet, header=header_idx, dtype=object).fillna("")
        if len(df) > MAX_ROWS:
            raise ValueError("Too many rows in workbook")
        m = mapped(df.columns)
        if not m["title"]:
            continue
        if not m["selector"] and not m["selected"]:
            issues.append(f"{sheet}: no selection marker/selector column; ignored to avoid importing the full catalogue")
            continue
        for index, row in df.iterrows():
            selector = clean(row[m["selector"]]) if m["selector"] else ""
            flag = selected_flag(row[m["selected"]]) if m["selected"] else False
            if not selector and not flag:
                continue
            title = clean(row[m["title"]])
            if not title:
                issues.append(f"{sheet}, row {index + header_idx + 2}: missing title")
                continue
            def val(k):
                return clean(row[m[k]]) if m[k] else ""
            records.append(dict(title=title, author=val("author"), publisher=val("publisher"),
                isbn=val("isbn"), price=val("price"), currency=val("currency"),
                year=val("year"), subject=val("subject"), language=val("language"),
                selector=selector or fallback_name, sheet=sheet))
    return records, issues

def parse_docx(raw, fallback_name):
    doc = Document(io.BytesIO(raw))
    records, issues = [], []
    for ti, table in enumerate(doc.tables):
        if not table.rows:
            continue
        headers = [c.text.strip() for c in table.rows[0].cells]
        m = mapped(headers)
        if not m["title"]:
            continue
        indexes = {k: headers.index(v) for k, v in m.items() if v is not None}
        for row_no, row in enumerate(table.rows[1:], 2):
            cells = [c.text.strip() for c in row.cells]
            def val(k):
                i = indexes.get(k, -1)
                return cells[i] if 0 <= i < len(cells) else ""
            title = val("title")
            if not title:
                if any(cells):
                    issues.append(f"Word table {ti+1}, row {row_no}: missing title")
                continue
            records.append(dict(title=title, author=val("author"), publisher=val("publisher"),
                isbn=val("isbn"), price=val("price"), currency=val("currency"),
                year=val("year"), subject=val("subject"), language=val("language"),
                selector=val("selector") or fallback_name, sheet=f"Word table {ti+1}"))
    if not records and not issues:
        issues.append("Word file has no recognized book table; use columns Title/عنوان الكتاب")
    return records, issues

def price_float(value):
    try:
        return float(clean(value).replace(",", ""))
    except (TypeError, ValueError):
        return None

def match_book(db, record):
    isbn = norm(record["isbn"])
    if isbn:
        for b in db.query(Book).filter(Book.isbn.isnot(None)).all():
            if norm(b.isbn) == isbn:
                return b
    title = norm(record["title"])
    candidates = db.query(Book).filter(Book.title.isnot(None)).all()
    for b in candidates:
        if norm(b.title) == title and (
            not record["author"] or not b.author or norm(b.author) == norm(record["author"])
        ):
            return b
    return None

@router.post("/admin/import-offline-selections")
async def import_offline_selections(request: Request):
    from selection_portal import require_admin, lang_of, page_template, esc
    admin, redirect = require_admin(request)
    if redirect:
        return redirect
    form = await request.form()
    lang = lang_of(request)
    fallback = clean(form.get("selector_name"))
    department = clean(form.get("department")) or "Offline selections"
    uploads = [f for f in form.getlist("selection_files") if getattr(f, "filename", "")]
    if not uploads or not fallback:
        return HTMLResponse("Selector name and files are required", status_code=400)
    parsed, issues = [], []
    for upload in uploads:
        filename = Path(upload.filename).name
        ext = Path(filename).suffix.lower()
        if ext not in {".xlsx", ".xls", ".docx"}:
            issues.append(f"{filename}: unsupported format (convert legacy .doc to .docx)")
            continue
        raw = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            issues.append(f"{filename}: exceeds 12 MB")
            continue
        try:
            rows, warnings = parse_docx(raw, fallback) if ext == ".docx" else parse_excel(raw, ext, fallback)
            for row in rows:
                row["file"] = filename
            parsed.extend(rows)
            issues.extend(f"{filename}: {w}" for w in warnings)
        except Exception as exc:
            issues.append(f"{filename}: invalid or unreadable file ({type(exc).__name__})")
    # Preview is mandatory: nothing is committed until administrator confirms.
    if not parsed:
        return HTMLResponse(page_template(
            '<div class="card"><h2>No selected books found</h2><p>' +
            esc("; ".join(issues) or "No rows were marked selected") +
            '</p><a href="/admin?lang='+lang+'">Back</a></div>', lang=lang, admin=True), status_code=400)
    # Save a compact, signed session preview; never put full file contents in cookie.
    # Instead require confirmation in the same POST using a checkbox and show a
    # dry-run when not confirmed. The admin re-uploads for the confirmed request.
    confirmed = str(form.get("confirm_import", "")) == "yes"
    if not confirmed:
        sample = "".join("<tr><td>"+esc(r["title"])+"</td><td>"+esc(r["selector"])+"</td><td>"+esc(r["file"])+"</td></tr>" for r in parsed[:30])
        return HTMLResponse(page_template(
            '<div class="card"><h2>Upload preview / معاينة الملفات</h2><p>'+
            str(len(parsed))+' selected rows detected. No changes saved.</p>'+
            '<table><tr><th>Title</th><th>Selected by</th><th>Source</th></tr>'+sample+
            '</table><p>'+esc("; ".join(issues[:30]))+'</p>'+
            '<p>To import, upload the same files again and check Confirm Import.</p>'+
            '<a href="/admin?lang='+lang+'">Back to Admin</a></div>',lang=lang,admin=True))
    db = SessionLocal()
    created, reused, skipped = 0, 0, 0
    try:
        # Deduplicate within this upload, preserving different selectors.
        seen = set()
        grouped = {}
        for row in parsed:
            key = (norm(row["selector"]), norm(row["isbn"]) or norm(row["title"]))
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            grouped.setdefault(row["selector"], []).append(row)
        for selector_name, rows in grouped.items():
            selector = Selector(full_name=selector_name, department=department)
            db.add(selector)
            db.flush()
            cart = SelectionCart(selector_id=selector.id, status="Submitted")
            db.add(cart)
            db.flush()
            for row in rows:
                book = match_book(db, row)
                if book:
                    reused += 1
                else:
                    book = Book(title=row["title"], author=row["author"] or None,
                        publisher=row["publisher"] or None,
                        source_publisher=row["publisher"] or None,
                        publication_year=row["year"] or None, isbn=row["isbn"] or None,
                        price=price_float(row["price"]), currency=row["currency"] or None,
                        subject=row["subject"] or None, language=row["language"] or None,
                        source_file=row["file"], source_sheet=row["sheet"],
                        validation_status="Offline selection: review metadata")
                    db.add(book)
                    db.flush()
                    created += 1
                # A repeat upload for the same selector + book should not add demand.
                existing = (db.query(SelectionItem).join(SelectionCart).join(Selector)
                    .filter(SelectionItem.book_id == book.id, Selector.full_name == selector_name).first())
                if existing:
                    skipped += 1
                    continue
                db.add(SelectionItem(cart_id=cart.id, book_id=book.id,
                    requested_quantity=1, admin_approved_quantity=0, admin_status="Pending"))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    message = (f"Imported pending selections. New titles: {created}; matched titles: {reused}; "
               f"duplicate selections skipped: {skipped}. " + "; ".join(issues[:20]))
    return HTMLResponse(page_template(
        '<div class="card"><h2>Offline selections imported / تم استيراد الاختيارات</h2><p>'+
        esc(message)+'</p><a href="/admin/export-selected-master?lang='+lang+
        '">Download combined master / تنزيل القائمة الموحدة</a><p><a href="/admin?lang='+
        lang+'">Admin Dashboard</a></p></div>', lang=lang, admin=True))

@router.get("/admin/export-selected-master")
def export_selected_master(request: Request):
    from selection_portal import require_admin
    _, redirect = require_admin(request)
    if redirect:
        return redirect
    db = SessionLocal()
    try:
        entries = (db.query(SelectionItem, Book, Selector)
            .join(Book, SelectionItem.book_id == Book.id)
            .join(SelectionCart, SelectionItem.cart_id == SelectionCart.id)
            .join(Selector, SelectionCart.selector_id == Selector.id)
            .all())
        records = []
        for item, book, selector in entries:
            records.append({"Title":book.title, "Author":book.author,
                "Publisher":book.publisher, "Source Publisher":book.source_publisher,
                "Publication Year":book.publication_year, "ISBN":book.isbn,
                "Price":book.price, "Currency":book.currency, "Subject":book.subject,
                "Language":book.language, "Selected By":selector.full_name,
                "Department":selector.department, "Selection Source":book.source_file or "Online portal",
                "Status":item.admin_status, "Source File":book.source_file})
    finally:
        db.close()
    fields = ["Title","Author","Publisher","Source Publisher","Publication Year","ISBN",
              "Price","Currency","Subject","Language","Selected By","Department",
              "Selection Source","Status","Source File"]
    df = pd.DataFrame(records, columns=fields)
    summary = (df.groupby("Selected By", dropna=False).size().reset_index(name="Selected Books")
               if len(df) else pd.DataFrame(columns=["Selected By","Selected Books"]))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Selected Books", index=False)
        summary.to_excel(writer, sheet_name="Selection Summary", index=False)
        for ws in writer.book.worksheets:
            ws.sheet_view.rightToLeft = True
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.fill = PatternFill("solid", fgColor="164D43")
                cell.font = Font(color="FFFFFF", bold=True)
            for col in ws.columns:
                letter = col[0].column_letter
                ws.column_dimensions[letter].width = min(48, max(16, max(len(str(c.value or "")) for c in list(col)[:300]) + 2))
                for cell in col:
                    cell.alignment = Alignment(horizontal="right")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="AcquiAI_Master_Selected_Books_RTL.xlsx"'})
