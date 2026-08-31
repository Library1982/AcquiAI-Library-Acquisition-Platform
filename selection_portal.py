
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import or_, func
from urllib.parse import urlencode
from pathlib import Path
from database import SessionLocal
from models import Book, Selector, SelectionCart, SelectionItem

import io
import zipfile
import re
import pandas as pd


app = FastAPI(
    title="AcquiAI",
    version="3.8.2",
)

PAGE_SIZE = 50


# =========================================================
# LANGUAGE
# =========================================================

TEXT = {
    "en": {
        "brand": "AcquiAI",
        "tagline": "One-Click AI Library Acquisition Platform",
        "portal": "Selection Portal",
        "admin": "Admin Dashboard",
        "language_button": "العربية",
        "catalogue_title": "Book Selection Catalogue",
        "catalogue_subtitle": (
            "Search the acquisition catalogue, select the books you recommend, "
            "and submit your selection to the library."
        ),
        "search_placeholder": "Search title, author, ISBN, subject...",
        "all_publishers": "All Publishers",
        "all_languages": "All Languages",
        "all_subjects": "All Subjects",
        "search": "Search",
        "total_catalogue": "Total Catalogue",
        "showing": "Showing",
        "selected": "Selected",
        "your_information": "Your Information",
        "full_name": "Full Name *",
        "user_id": "Student / Employee ID",
        "department": "Department / Programme *",
        "email": "Email",
        "available_books": "Available Books",
        "select_page": "Select All on This Page",
        "clear": "Clear",
        "select": "Select",
        "title": "Title",
        "author": "Author",
        "publisher": "Publisher",
        "year": "Year",
        "isbn": "ISBN",
        "price": "Price",
        "subject": "Subject",
        "language": "Language",
        "books_selected": "book(s) selected",
        "submit_cart": "Submit Selection Cart",
        "previous": "Previous",
        "next": "Next",
        "page": "Page",
        "of": "of",
        "no_books": "No books matched your search.",
        "selection_submitted": "Selection Submitted",
        "thank_you": "Thank you",
        "selection_sent": "Your book selection has been sent to the AcquiAI administrator.",
        "cart_id": "Cart ID",
        "selected_books": "Selected Books",
        "status": "Status",
        "submitted": "Submitted",
        "return_catalogue": "Return to Catalogue",
        "full_name_required": "Full Name is required.",
        "department_required": "Department is required.",
        "select_one": "Please select at least one book.",
        "no_valid_books": "No valid books were selected.",
        "unable_submit": "Unable to Submit Selection",
        "admin_title": "AcquiAI Admin Dashboard",
        "admin_subtitle": (
            "Review user selections, aggregate demand, approve final quantities, "
            "and prepare publisher orders."
        ),
        "submitted_carts": "Submitted Carts",
        "users": "Users",
        "selections": "Selections",
        "pending": "Pending",
        "approved": "Approved",
        "rejected": "Rejected",
        "aggregated_demand": "Aggregated Book Demand",
        "aggregated_help": "Each title appears once. Requested By counts unique users.",
        "export_final": "Export Final Approved Excel",
        "generate_publisher_orders": "Generate Publisher Orders ZIP",
        "publisher_orders_help": "Creates one separate Excel order file for each publisher/vendor.",
        "new_cycle": "New Selection Cycle",
        "new_cycle_help": "Clear all previous user selections and admin decisions while keeping the current catalogue.",
        "reset_cycle": "Reset Selections",
        "upload_master": "Upload Publisher / Vendor Files",
        "upload_master_help": "Select multiple publisher/vendor Excel files. AcquiAI combines them into one standardized master catalogue and publishes it to users.",
        "choose_master": "Choose Publisher / Vendor Excel Files",
        "publish_master": "Generate & Publish Master Catalogue",
        "cycle_warning": "This will permanently clear all submitted carts, users and selection decisions. Continue?",
        "master_warning": "AcquiAI will combine these publisher files into a new master catalogue and clear the current selection cycle. Continue?",
        "cycle_reset_done": "New selection cycle started successfully.",
        "master_import_done": "New master catalogue published successfully.",
        "records_imported": "records imported",
        "files_processed": "Publisher Files Processed",
        "source_rows": "Source Rows",
        "unique_titles": "Unique Titles",
        "duplicates_removed": "Duplicates Consolidated",
        "skipped_files": "Skipped / Ignored Sheets",
        "download_generated_master": "Download Generated Master",
        "published_to_users": "Catalogue is now published to the Selection Portal.",
        "mapping_fixed": "Arabic/English mapping uses automatic header-row detection, safe field matching and validation.",
        "invalid_master": "The uploaded workbook does not contain a recognizable Title column.",
        "master_upload_error": "Unable to import the master catalogue.",
        "workflow": "Acquisition Workflow",
        "workflow_1": "1. Upload Master",
        "workflow_2": "2. Publish to Users",
        "workflow_3": "3. Collect Selections",
        "workflow_4": "4. Approve & Generate Orders",
        "requested_by": "Requested By",
        "total_requests": "Total Requests",
        "admin_decision": "Admin Decision / Final Qty",
        "approve": "Approve",
        "reject": "Reject",
        "reset": "Reset",
        "select_all_pending": "Select All Pending",
        "clear_selected": "Clear Selected",
        "approve_selected": "Approve Selected",
        "reject_selected": "Reject Selected",
        "bulk_default_qty": "Default Final Qty",
        "select_books_first": "Please select at least one title.",
        "cart": "Cart",
        "name": "Name",
        "id": "ID",
        "books": "Books",
        "submitted_at": "Submitted",
        "final_order": "Final Approved Order",
        "approved_titles": "Approved Titles",
        "estimated_value": "Estimated Value",
        "final_qty": "Final Qty",
        "unit_price": "Unit Price",
        "estimated_total": "Estimated Total",
        "no_carts": "No carts submitted yet.",
        "no_demand": "No book selections submitted yet.",
        "no_approved": "No books approved yet.",
        "no_approved_export_title": "No Approved Books",
        "no_approved_export_text": (
            "Approve at least one title and enter a final quantity before exporting."
        ),
        "return_admin": "Return to Admin Dashboard",
        "quick_tip": "Tip",
        "quick_tip_text": (
            "Use search and filters to narrow the catalogue. "
            "Only the 50 books on the current page are loaded for faster performance."
        ),
    },
    "ar": {
        "brand": "AcquiAI",
        "tagline": "منصة الاستحواذ الذكية للمكتبات بنقرة واحدة",
        "portal": "بوابة الاختيار",
        "admin": "لوحة تحكم المسؤول",
        "language_button": "English",
        "catalogue_title": "فهرس اختيار الكتب",
        "catalogue_subtitle": (
            "ابحث في قائمة الكتب المقترحة، اختر العناوين المناسبة، "
            "ثم أرسل اختياراتك إلى المكتبة."
        ),
        "search_placeholder": "ابحث بالعنوان أو المؤلف أو ردمك أو الموضوع...",
        "all_publishers": "جميع الناشرين",
        "all_languages": "جميع اللغات",
        "all_subjects": "جميع الموضوعات",
        "search": "بحث",
        "total_catalogue": "إجمالي العناوين",
        "showing": "المعروض",
        "selected": "المحدد",
        "your_information": "بيانات المستخدم",
        "full_name": "الاسم الكامل *",
        "user_id": "الرقم الوظيفي / الجامعي",
        "department": "القسم / البرنامج *",
        "email": "البريد الإلكتروني",
        "available_books": "الكتب المتاحة",
        "select_page": "تحديد كل ما في الصفحة",
        "clear": "مسح التحديد",
        "select": "اختيار",
        "title": "العنوان",
        "author": "المؤلف",
        "publisher": "الناشر",
        "year": "السنة",
        "isbn": "ردمك",
        "price": "السعر",
        "subject": "الموضوع",
        "language": "اللغة",
        "books_selected": "كتاب/كتب محددة",
        "submit_cart": "إرسال سلة الاختيارات",
        "previous": "السابق",
        "next": "التالي",
        "page": "الصفحة",
        "of": "من",
        "no_books": "لا توجد كتب مطابقة للبحث.",
        "selection_submitted": "تم إرسال الاختيارات",
        "thank_you": "شكراً لك",
        "selection_sent": "تم إرسال اختياراتك إلى مسؤول AcquiAI.",
        "cart_id": "رقم السلة",
        "selected_books": "عدد الكتب",
        "status": "الحالة",
        "submitted": "تم الإرسال",
        "return_catalogue": "العودة إلى الفهرس",
        "full_name_required": "الاسم الكامل مطلوب.",
        "department_required": "القسم / البرنامج مطلوب.",
        "select_one": "يرجى اختيار كتاب واحد على الأقل.",
        "no_valid_books": "لم يتم اختيار كتب صالحة.",
        "unable_submit": "تعذر إرسال الاختيارات",
        "admin_title": "لوحة تحكم AcquiAI",
        "admin_subtitle": (
            "راجع اختيارات المستخدمين، اجمع الطلبات، اعتمد الكميات النهائية، "
            "وجهز أوامر الناشرين."
        ),
        "submitted_carts": "السلال المرسلة",
        "users": "المستخدمون",
        "selections": "الاختيارات",
        "pending": "قيد المراجعة",
        "approved": "معتمد",
        "rejected": "مرفوض",
        "aggregated_demand": "الطلب المجمع على الكتب",
        "aggregated_help": "يظهر كل عنوان مرة واحدة ويحسب عدد المستخدمين المختلفين.",
        "export_final": "تصدير الطلب النهائي إلى Excel",
        "generate_publisher_orders": "إنشاء أوامر منفصلة للناشرين ZIP",
        "publisher_orders_help": "ينشئ ملف Excel منفصلاً لكل ناشر / مورد.",
        "new_cycle": "دورة اختيار جديدة",
        "new_cycle_help": "حذف جميع اختيارات المستخدمين وقرارات المسؤول السابقة مع الاحتفاظ بالفهرس الحالي.",
        "reset_cycle": "إعادة ضبط الاختيارات",
        "upload_master": "رفع ملفات الناشرين / الموردين",
        "upload_master_help": "اختر عدة ملفات Excel للناشرين أو الموردين. سيقوم AcquiAI بدمجها وتوحيدها في فهرس رئيسي واحد ثم نشره للمستخدمين.",
        "choose_master": "اختر ملفات Excel للناشرين / الموردين",
        "publish_master": "إنشاء ونشر الفهرس الرئيسي",
        "cycle_warning": "سيتم حذف جميع السلال والمستخدمين وقرارات الاختيار السابقة نهائياً. هل تريد المتابعة؟",
        "master_warning": "سيقوم AcquiAI بدمج ملفات الناشرين في فهرس رئيسي جديد وحذف دورة الاختيار الحالية. هل تريد المتابعة؟",
        "cycle_reset_done": "تم بدء دورة اختيار جديدة بنجاح.",
        "master_import_done": "تم نشر الفهرس الرئيسي الجديد بنجاح.",
        "records_imported": "سجل تم استيراده",
        "files_processed": "ملفات الناشرين المعالجة",
        "source_rows": "إجمالي الصفوف المصدرية",
        "unique_titles": "العناوين الفريدة",
        "duplicates_removed": "التكرارات المدمجة",
        "skipped_files": "الأوراق المتجاوزة / المستبعدة",
        "download_generated_master": "تنزيل الملف الرئيسي المُنشأ",
        "published_to_users": "تم نشر الفهرس الآن في بوابة الاختيار.",
        "mapping_fixed": "يستخدم الربط العربي والإنجليزي اكتشاف صف العناوين تلقائياً وربط الحقول الآمن والتحقق من البيانات.",
        "invalid_master": "لا يحتوي الملف المرفوع على عمود عنوان يمكن التعرف عليه.",
        "master_upload_error": "تعذر استيراد الفهرس الرئيسي.",
        "workflow": "سير عمل التزويد",
        "workflow_1": "1. رفع الملف الرئيسي",
        "workflow_2": "2. النشر للمستخدمين",
        "workflow_3": "3. جمع الاختيارات",
        "workflow_4": "4. الاعتماد وإنشاء الطلبات",
        "requested_by": "عدد الطالبين",
        "total_requests": "إجمالي الطلبات",
        "admin_decision": "قرار المسؤول / الكمية النهائية",
        "approve": "اعتماد",
        "reject": "رفض",
        "reset": "إعادة",
        "select_all_pending": "تحديد جميع المعلّقة",
        "clear_selected": "إلغاء التحديد",
        "approve_selected": "اعتماد المحدد",
        "reject_selected": "رفض المحدد",
        "bulk_default_qty": "الكمية النهائية الافتراضية",
        "select_books_first": "يرجى تحديد عنوان واحد على الأقل.",
        "cart": "السلة",
        "name": "الاسم",
        "id": "الرقم",
        "books": "الكتب",
        "submitted_at": "تاريخ الإرسال",
        "final_order": "الطلب النهائي المعتمد",
        "approved_titles": "العناوين المعتمدة",
        "estimated_value": "القيمة التقديرية",
        "final_qty": "الكمية النهائية",
        "unit_price": "سعر الوحدة",
        "estimated_total": "الإجمالي التقديري",
        "no_carts": "لا توجد سلال مرسلة حتى الآن.",
        "no_demand": "لا توجد اختيارات كتب مرسلة حتى الآن.",
        "no_approved": "لا توجد كتب معتمدة حتى الآن.",
        "no_approved_export_title": "لا توجد كتب معتمدة",
        "no_approved_export_text": "اعتمد كتاباً واحداً على الأقل وحدد الكمية قبل التصدير.",
        "return_admin": "العودة إلى لوحة التحكم",
        "quick_tip": "معلومة",
        "quick_tip_text": (
            "استخدم البحث والفلاتر لتضييق النتائج. "
            "يتم تحميل 50 كتاباً فقط في الصفحة لتحسين السرعة."
        ),
    },
}


def lang_pack(lang: str):
    lang = "ar" if lang == "ar" else "en"
    return lang, TEXT[lang]


def esc(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )




def normalize_colname(value):
    """
    Normalize English AND Arabic column names.
    v3.3 stripped Arabic letters, turning every Arabic header into the
    same empty key. That caused one Arabic column to be reused for many
    unrelated target fields. v3.4 preserves Unicode letters/numbers.
    """
    value = str(value or "").strip().lower()
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    value = value.replace("ى", "ي")
    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)  # Arabic diacritics
    value = re.sub(r"[\W_]+", "", value, flags=re.UNICODE)
    return value


def find_column(df, aliases, used_columns=None):
    used_columns = used_columns or set()

    normalized = {}
    for col in df.columns:
        key = normalize_colname(col)
        if key and key not in normalized:
            normalized[key] = col

    for alias in aliases:
        key = normalize_colname(alias)
        col = normalized.get(key)
        if col is not None and col not in used_columns:
            return col

    return None


def map_columns_safely(df, aliases):
    """
    Map each source column to at most one bibliographic target field.
    This prevents Subject/Price/ISBN/etc. from all pointing to the same
    source column.
    """
    result = {}
    used = set()

    priority = [
        "Title",
        "Author",
        "Publisher",
        "Publication Year",
        "ISBN",
        "Price",
        "Currency",
        "Subject",
        "Language",
        "Vendor",
    ]

    for standard in priority:
        col = find_column(df, aliases.get(standard, []), used)
        result[standard] = col
        if col is not None:
            used.add(col)

    return result


def valid_year(value):
    if value in (None, ""):
        return None
    match = re.search(r"\b(18|19|20|21)\d{2}\b", str(value))
    return match.group(0) if match else None


def valid_isbn(value):
    if value in (None, ""):
        return None
    raw = str(value).strip()
    compact = re.sub(r"[^0-9Xx]", "", raw)
    if len(compact) in (10, 13):
        return compact.upper()
    return None


def valid_price(value):
    if value in (None, ""):
        return None
    try:
        cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
        if not cleaned:
            return None
        number = float(cleaned)
        # Reject obvious ISBNs, years and absurd values accidentally mapped as price.
        if number < 0 or number > 100000:
            return None
        return number
    except Exception:
        return None





def is_non_catalogue_sheet(sheet_name):
    """
    Identify obvious notes/summary/instruction sheets that should not become
    catalogue records unless they independently show strong bibliographic headers.
    """
    key = normalize_colname(sheet_name)
    blocked_terms = [
        "notes", "note", "remarks", "remark", "summary", "summaries",
        "instructions", "instruction", "readme", "info", "information",
        "ملاحظات", "ملاحظة", "ملحوظات", "تعليمات", "ارشادات", "إرشادات",
        "ملخص", "ملخصات", "معلومات", "بيانات", "فهرس",
    ]
    return any(normalize_colname(term) in key for term in blocked_terms if normalize_colname(term))


def header_alias_score(values, aliases):
    """Count how many cells in a candidate row look like known bibliographic headers."""
    normalized_aliases = {
        normalize_colname(alias)
        for names in aliases.values()
        for alias in names
        if normalize_colname(alias)
    }
    score = 0
    for value in values:
        key = normalize_colname(value)
        if key and key in normalized_aliases:
            score += 1
    return score


def detect_header_row(raw_bytes, sheet_name, engine, aliases, max_rows=15):
    """
    Inspect the first rows without assuming where the header is.
    Returns the row number with the strongest bibliographic-header evidence.
    """
    preview = pd.read_excel(
        io.BytesIO(raw_bytes),
        sheet_name=sheet_name,
        engine=engine,
        dtype=object,
        header=None,
        nrows=max_rows,
    )

    best_row = 0
    best_score = -1

    for row_no in range(len(preview)):
        values = preview.iloc[row_no].tolist()
        score = header_alias_score(values, aliases)
        if score > best_score:
            best_score = score
            best_row = row_no

    return best_row, best_score


def infer_columns_from_data(df, current):
    """
    Conservative fallback for unusual publisher files.
    It fills only unmapped fields and never reuses a source column.
    """
    result = dict(current)
    used = {c for c in result.values() if c is not None}

    def sample_values(col, limit=30):
        vals = []
        for value in df[col].dropna().head(limit):
            s = str(value).strip()
            if s:
                vals.append(s)
        return vals

    # ISBN: strong structural signature.
    if not result.get("ISBN"):
        best = None
        best_ratio = 0
        for col in df.columns:
            if col in used:
                continue
            vals = sample_values(col)
            if not vals:
                continue
            ratio = sum(valid_isbn(v) is not None for v in vals) / len(vals)
            if ratio >= 0.60 and ratio > best_ratio:
                best, best_ratio = col, ratio
        if best is not None:
            result["ISBN"] = best
            used.add(best)

    # Publication year: strong 4-digit year signature.
    if not result.get("Publication Year"):
        best = None
        best_ratio = 0
        for col in df.columns:
            if col in used:
                continue
            vals = sample_values(col)
            if not vals:
                continue
            ratio = sum(valid_year(v) is not None for v in vals) / len(vals)
            if ratio >= 0.60 and ratio > best_ratio:
                best, best_ratio = col, ratio
        if best is not None:
            result["Publication Year"] = best
            used.add(best)

    # Price: numeric values in a plausible book-price range, excluding year/ISBN columns.
    if not result.get("Price"):
        best = None
        best_ratio = 0
        for col in df.columns:
            if col in used:
                continue
            vals = sample_values(col)
            if not vals:
                continue
            plausible = 0
            for v in vals:
                p = valid_price(v)
                if p is not None and 0 < p <= 10000 and valid_year(v) is None and valid_isbn(v) is None:
                    plausible += 1
            ratio = plausible / len(vals)
            if ratio >= 0.70 and ratio > best_ratio:
                best, best_ratio = col, ratio
        if best is not None:
            result["Price"] = best
            used.add(best)

    return result


def choose_title_fallback(df, current):
    """
    Last-resort title recovery for a sheet whose title header is unfamiliar.
    Chooses a text-heavy unused column, but only when evidence is strong.
    """
    used = {c for c in current.values() if c is not None}
    best = None
    best_score = 0

    for col in df.columns:
        if col in used:
            continue

        vals = [str(v).strip() for v in df[col].dropna().head(40) if str(v).strip()]
        if len(vals) < 2:
            continue

        text_like = [
            v for v in vals
            if valid_year(v) is None
            and valid_isbn(v) is None
            and valid_price(v) is None
            and len(v) >= 4
        ]

        ratio = len(text_like) / len(vals)
        avg_len = sum(len(v) for v in text_like) / max(1, len(text_like))
        score = ratio * min(avg_len, 80)

        if ratio >= 0.70 and avg_len >= 6 and score > best_score:
            best = col
            best_score = score

    return best


def publisher_from_filename(filename):
    name = str(filename or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = re.sub(r"\.(xlsx|xls)$", "", name, flags=re.I)
    name = re.sub(r"\s*\(\d+\)\s*$", "", name)
    name = re.sub(r"\s*[-_ ]*(copy|نسخة)\s*$", "", name, flags=re.I)
    name = name.replace("_", " ").strip(" -_")
    return name or "Unknown Publisher"


def book_dedupe_key(record):
    isbn = re.sub(r"[^0-9Xx]", "", str(record.get("ISBN") or ""))
    if isbn:
        return ("isbn", isbn.upper())

    title = normalize_colname(record.get("Title"))
    author = normalize_colname(record.get("Author"))
    year = normalize_colname(record.get("Publication Year"))
    publisher = normalize_colname(record.get("Publisher") or record.get("Source Publisher"))
    return ("meta", title, author, year, publisher)


def safe_filename(value):
    value = str(value or "Unknown Publisher").strip()
    value = re.sub(r'[\\/:*?"<>|]+', "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:120] or "Unknown Publisher"


def build_url(path, lang="en", **params):
    values = {"lang": lang}
    for key, value in params.items():
        if value not in (None, ""):
            values[key] = value
    return path + "?" + urlencode(values)


def page_template(content, title="AcquiAI", lang="en", admin=False):
    lang, t = lang_pack(lang)

    direction = "rtl" if lang == "ar" else "ltr"
    align = "right" if lang == "ar" else "left"

    switch_lang = "en" if lang == "ar" else "ar"
    switch_url = build_url("/admin" if admin else "/", switch_lang)

    portal_url = build_url("/", lang)
    admin_url = build_url("/admin", lang)

    admin_badge = (
        '<span class="admin-badge">ADMIN</span>'
        if admin
        else ""
    )

    return f"""
<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>

<style>
:root {{
    --brand: #0b6f61;
    --brand-dark: #063f39;
    --brand-deep: #042f2b;
    --brand-soft: #eaf8f4;
    --brand-soft-2: #f4fbf9;
    --gold: #d7a429;
    --gold-soft: #fff6d9;
    --text: #12332d;
    --muted: #70827d;
    --border: #dce9e5;
    --bg: #f3f8f6;
    --danger: #c64f4f;
    --success: #2f956f;
    --surface: rgba(255,255,255,.94);
    --shadow: 0 16px 44px rgba(13, 75, 65, .10);
    --shadow-soft: 0 8px 24px rgba(13, 75, 65, .07);
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: "Segoe UI", Tahoma, Arial, sans-serif;
    background:
        radial-gradient(circle at 85% 0%, rgba(11,111,97,.12), transparent 28%),
        radial-gradient(circle at 10% 20%, rgba(215,164,41,.07), transparent 18%),
        linear-gradient(180deg, #f8fbfa 0%, var(--bg) 100%);
    color: var(--text);
    text-align: {align};
}}

header {{
    background:
        linear-gradient(115deg, var(--brand-deep) 0%, var(--brand-dark) 48%, var(--brand) 100%);
    color: white;
    padding: 18px 34px;
    box-shadow: 0 8px 25px rgba(3,59,50,.18);
    position: sticky;
    top: 0;
    z-index: 50;
}}

.header-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
}}

.brand-wrap {{
    display: flex;
    align-items: center;
    gap: 14px;
}}

.logo-mark {{
    width: 52px;
    height: 52px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    background: linear-gradient(145deg, rgba(255,255,255,.20), rgba(255,255,255,.08));
    border: 1px solid rgba(255,255,255,.24);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 8px 20px rgba(0,0,0,.12);
    font-size: 23px;
    font-weight: 900;
}}

.brand {{
    font-size: 31px;
    font-weight: 900;
    letter-spacing: -.5px;
}}

.tagline {{
    margin-top: 3px;
    opacity: .88;
    font-size: 14px;
}}

.nav {{
    display: flex;
    gap: 9px;
    align-items: center;
    flex-wrap: wrap;
}}

.nav-link {{
    color: white;
    text-decoration: none;
    background: rgba(255,255,255,.10);
    backdrop-filter: blur(8px);
    padding: 10px 14px;
    border-radius: 12px;
    font-weight: 700;
    border: 1px solid rgba(255,255,255,.10);
}}

.nav-link:hover {{
    background: rgba(255,255,255,.20);
}}

.lang-link {{
    background: white;
    color: var(--brand-dark);
}}

.admin-badge {{
    background: linear-gradient(135deg, var(--gold), #e5b437);
    color: white;
    padding: 8px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 900;
}}

.container {{
    width: min(96%, 1580px);
    margin: 26px auto 50px;
}}

.hero {{
    background:
        linear-gradient(135deg, rgba(6,63,57,.99), rgba(11,111,97,.95));
    color: white;
    border-radius: 26px;
    padding: 34px;
    box-shadow: var(--shadow-soft);
    margin-bottom: 20px;
}}

.hero h1 {{
    margin: 0 0 8px;
    font-size: 31px;
}}

.hero p {{
    margin: 0;
    opacity: .9;
    max-width: 900px;
    line-height: 1.7;
}}

.card {{
    background: var(--surface);
    backdrop-filter: blur(8px);
    border-radius: 22px;
    padding: 22px;
    margin-bottom: 20px;
    box-shadow: var(--shadow-soft);
    border: 1px solid rgba(220,233,229,.92);
}}

.section-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 16px;
}}

.section-icon {{
    width: 36px;
    height: 36px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    background: linear-gradient(135deg, var(--brand-soft), #e1f4ef);
    color: var(--brand);
    font-weight: 900;
}}

.filters {{
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr auto;
    gap: 12px;
}}

input,
select,
textarea {{
    width: 100%;
    padding: 12px 13px;
    border: 1px solid var(--border);
    border-radius: 13px;
    font-size: 14px;
    background: white;
    color: var(--text);
    outline: none;
}}

input:focus,
select:focus,
textarea:focus {{
    border-color: #57a893;
    box-shadow: 0 0 0 4px rgba(11,111,97,.09);
}}

button {{
    border: none;
    border-radius: 13px;
    padding: 11px 18px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 800;
    transition: transform .18s ease, box-shadow .18s ease, opacity .18s ease;
}}

button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 18px rgba(7,63,57,.12);
}}

button:active {{
    transform: translateY(0);
}}

.primary {{
    background: linear-gradient(135deg, var(--brand), #118d7b);
    color: white;
}}

.secondary {{
    background: linear-gradient(135deg, var(--brand-soft), #e1f4ef);
    color: var(--brand-dark);
}}

.warning {{
    background: linear-gradient(135deg, var(--gold), #e5b437);
    color: white;
}}

.danger {{
    background: var(--danger);
    color: white;
}}

.success-btn {{
    background: var(--success);
    color: white;
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(3, minmax(180px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
}}

.stat {{
    background: linear-gradient(180deg, #ffffff, #fbfdfc);
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: var(--shadow-soft);
    border: 1px solid rgba(220,233,229,.92);
}}

.stat-label {{
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
}}

.stat-value {{
    display: block;
    font-size: 25px;
    font-weight: 900;
    color: var(--brand-dark);
    margin-top: 4px;
}}

.user-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}}

.tip {{
    background: #fff9e8;
    border: 1px solid #f0dfac;
    border-radius: 14px;
    padding: 13px 15px;
    margin-top: 14px;
    color: #6a5720;
    line-height: 1.6;
}}

.table-wrap {{
    overflow-x: auto;
    border-radius: 14px;
    border: 1px solid var(--border);
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 1080px;
    background: white;
}}

th {{
    background: linear-gradient(90deg, var(--brand-deep), var(--brand-dark));
    color: white;
    padding: 12px 10px;
    text-align: {align};
    position: sticky;
    top: 0;
    z-index: 2;
    white-space: nowrap;
}}

td {{
    border-bottom: 1px solid #edf2f0;
    padding: 11px 10px;
    vertical-align: top;
}}

tr:hover td {{
    background: #f2faf7;
}}

.title {{
    min-width: 260px;
    font-weight: 800;
}}

.arabic {{
    direction: rtl;
    text-align: right;
}}

.price {{
    white-space: nowrap;
    font-weight: 800;
    color: var(--brand-dark);
}}

.checkbox {{
    width: 18px;
    height: 18px;
    accent-color: var(--brand);
}}

.action-bar {{
    position: sticky;
    bottom: 14px;
    background: var(--surface);
    backdrop-filter: blur(8px);
    backdrop-filter: blur(10px);
    border: 1px solid var(--border);
    padding: 14px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-radius: 16px;
    box-shadow: 0 12px 35px rgba(0,0,0,.13);
    z-index: 8;
    margin-top: 18px;
}}

.selected-count {{
    font-size: 17px;
    font-weight: 900;
}}

.pagination {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 7px;
    flex-wrap: wrap;
    margin-top: 20px;
}}

.pagination a {{
    text-decoration: none;
}}

.page-info {{
    margin-inline-start: 10px;
    color: var(--muted);
    font-weight: 700;
}}

.success {{
    text-align: center;
    padding: 55px 25px;
}}

.success-icon {{
    width: 86px;
    height: 86px;
    margin: 0 auto 18px;
    border-radius: 50%;
    background: #e3f5ed;
    color: var(--success);
    display: grid;
    place-items: center;
    font-size: 48px;
    font-weight: 900;
}}

.status {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 900;
}}

.status-pending {{
    background: #fff3cd;
    color: #7a5c00;
}}

.status-approved {{
    background: #d8f3e5;
    color: #17613c;
}}

.status-rejected {{
    background: #f8d7da;
    color: #842029;
}}

.admin-kpis {{
    display: grid;
    grid-template-columns: repeat(7, minmax(130px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
}}

.admin-kpis .stat {{
    min-width: 0;
}}

.admin-grid {{
    display: grid;
    grid-template-columns: 1.25fr .75fr;
    gap: 20px;
}}

.inline-form {{
    display: flex;
    gap: 7px;
    align-items: center;
    flex-wrap: wrap;
}}

.inline-form input {{
    width: 75px;
}}

.small {{
    font-size: 12px;
    color: var(--muted);
}}


.workflow-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 16px;
}}

.workflow-step {{
    background: linear-gradient(135deg, var(--brand-soft), #e1f4ef);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px;
    font-weight: 800;
    color: var(--brand-dark);
    text-align: center;
}}

.admin-actions {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}}

.upload-box {{
    border: 2px dashed var(--border);
    border-radius: 14px;
    padding: 18px;
    background: #fbfdfc;
}}

@media(max-width: 900px) {{
    .workflow-grid,
    .admin-actions {{
        grid-template-columns: 1fr;
    }}
}}

.toolbar {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 16px;
}}


.brand-subline {{
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 4px;
    font-size: 12px;
    opacity: .82;
}}

.brand-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--gold);
    display: inline-block;
}}

.credit-chip {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,.10);
    border: 1px solid rgba(255,255,255,.14);
    color: white;
    padding: 8px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}}

.footer {{
    width: min(96%, 1580px);
    margin: 0 auto 24px;
    padding: 18px 20px;
    border-radius: 18px;
    background: linear-gradient(135deg, #ffffff, #f2faf7);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-soft);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    color: var(--muted);
    font-size: 13px;
}}

.footer strong {{
    color: var(--brand-dark);
}}

.workflow-step {{
    position: relative;
    overflow: hidden;
}}

.workflow-step::after {{
    content: "";
    position: absolute;
    inset: auto 0 0 0;
    height: 3px;
    background: linear-gradient(90deg, var(--gold), transparent);
}}

.table-wrap {{
    box-shadow: inset 0 1px 0 rgba(255,255,255,.8);
}}

.hero {{
    position: relative;
    overflow: hidden;
}}

.hero::after {{
    content: "";
    position: absolute;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    right: -60px;
    top: -80px;
    background: rgba(255,255,255,.06);
}}

.hero::before {{
    content: "";
    position: absolute;
    width: 140px;
    height: 140px;
    border-radius: 50%;
    right: 90px;
    bottom: -90px;
    background: rgba(215,164,41,.10);
}}

@media(max-width: 1100px) {{
    .filters,
    .user-grid,
    .admin-grid {{
        grid-template-columns: 1fr;
    }}

    .admin-kpis {{
        grid-template-columns: repeat(2, 1fr);
    }}
}}

@media(max-width: 700px) {{
    header {{
        padding: 18px;
    }}

    .container {{
        width: 94%;
    }}

    .stats {{
        grid-template-columns: 1fr;
    }}

    .admin-kpis {{
        grid-template-columns: 1fr 1fr;
    }}

    .action-bar {{
        align-items: stretch;
        flex-direction: column;
    }}

    .action-bar button {{
        width: 100%;
    }}
}}
</style>
</head>

<body>
<header>
<div class="header-row">

<div class="brand-wrap">
    <div class="logo-mark">A+</div>
    <div>
        <div class="brand">{esc(t["brand"])}</div>
        <div class="tagline">{esc(t["tagline"])}</div>
        <div class="brand-subline">
            <span class="brand-dot"></span>
            <span>Smart • Bilingual • End-to-End Acquisition</span>
        </div>
    </div>
</div>

<div class="nav">
    <a href="{portal_url}" class="nav-link">{esc(t["portal"])}</a>
    <a href="{admin_url}" class="nav-link">{esc(t["admin"])}</a>
    <a href="{switch_url}" class="nav-link lang-link">{esc(t["language_button"])}</a>
    <span class="credit-chip">Designed by Yameen Abdullah</span>
    {admin_badge}
</div>

</div>
</header>

<div class="container">
{content}
</div>

<div class="footer">
    <div><strong>AcquiAI</strong> — AI Library Acquisition Platform</div>
    <div>Designed & Developed by <strong>Yameen Abdullah</strong> • Version 3.8.2</div>
</div>
</body>
</html>
"""


# =========================================================
# USER SELECTION PORTAL
# =========================================================

@app.get("/", response_class=HTMLResponse)
def selection_page(
    q: str = "",
    publisher: str = "",
    language: str = "",
    subject: str = "",
    page: int = 1,
    lang: str = "en",
):
    lang, t = lang_pack(lang)
    db = SessionLocal()

    try:
        query = db.query(Book)

        if q:
            search = f"%{q}%"
            query = query.filter(
                or_(
                    Book.title.ilike(search),
                    Book.author.ilike(search),
                    Book.isbn.ilike(search),
                    Book.subject.ilike(search),
                    Book.publisher.ilike(search),
                )
            )

        if publisher:
            query = query.filter(Book.source_publisher == publisher)

        if language:
            query = query.filter(Book.language == language)

        if subject:
            query = query.filter(Book.subject == subject)

        if page < 1:
            page = 1

        filtered_total = query.count()

        total_pages = max(
            1,
            (filtered_total + PAGE_SIZE - 1) // PAGE_SIZE,
        )

        if page > total_pages:
            page = total_pages

        offset_value = (page - 1) * PAGE_SIZE

        books = (
            query
            .order_by(Book.id.asc())
            .offset(offset_value)
            .limit(PAGE_SIZE)
            .all()
        )

        total_books = db.query(Book).count()

        publishers = [
            r[0]
            for r in (
                db.query(Book.source_publisher)
                .filter(Book.source_publisher.isnot(None))
                .distinct()
                .order_by(Book.source_publisher)
                .all()
            )
        ]

        languages = [
            r[0]
            for r in (
                db.query(Book.language)
                .filter(Book.language.isnot(None))
                .distinct()
                .order_by(Book.language)
                .all()
            )
        ]

        subjects = [
            r[0]
            for r in (
                db.query(Book.subject)
                .filter(Book.subject.isnot(None))
                .distinct()
                .order_by(Book.subject)
                .limit(150)
                .all()
            )
        ]

        publisher_options = f'<option value="">{esc(t["all_publishers"])}</option>'
        for item in publishers:
            selected = "selected" if item == publisher else ""
            publisher_options += (
                f'<option value="{esc(item)}" {selected}>{esc(item)}</option>'
            )

        language_options = f'<option value="">{esc(t["all_languages"])}</option>'
        for item in languages:
            selected = "selected" if item == language else ""
            language_options += (
                f'<option value="{esc(item)}" {selected}>{esc(item)}</option>'
            )

        subject_options = f'<option value="">{esc(t["all_subjects"])}</option>'
        for item in subjects:
            selected = "selected" if item == subject else ""
            subject_options += (
                f'<option value="{esc(item)}" {selected}>{esc(item)}</option>'
            )

        rows = ""

        for book in books:
            price_text = (
                f"{book.price:g} {book.currency or ''}"
                if book.price is not None
                else ""
            )

            title_class = (
                "title arabic"
                if book.language == "Arabic"
                else "title"
            )

            rows += f"""
<tr>
<td>
<input
    class="checkbox book-check"
    type="checkbox"
    name="book_ids"
    value="{book.id}"
    onchange="updateCount()"
>
</td>
<td class="{title_class}">{esc(book.title)}</td>
<td>{esc(book.author)}</td>
<td>{esc(book.source_publisher)}</td>
<td>{esc(book.publication_year)}</td>
<td>{esc(book.isbn)}</td>
<td class="price">{esc(price_text)}</td>
<td>{esc(book.subject)}</td>
<td>{esc(book.language)}</td>
</tr>
"""

        if not rows:
            rows = f"""
<tr>
<td colspan="9">{esc(t["no_books"])}</td>
</tr>
"""

        base_params = {
            "q": q,
            "publisher": publisher,
            "language": language,
            "subject": subject,
        }

        base_params = {
            key: value
            for key, value in base_params.items()
            if value
        }

        pagination_html = '<div class="pagination">'

        if page > 1:
            params = dict(base_params)
            params["page"] = page - 1
            url = build_url("/", lang, **params)

            pagination_html += f"""
<a href="{url}">
<button type="button" class="secondary">← {esc(t["previous"])}</button>
</a>
"""

        start_page = max(1, page - 3)
        end_page = min(total_pages, page + 3)

        for page_number in range(start_page, end_page + 1):
            params = dict(base_params)
            params["page"] = page_number
            url = build_url("/", lang, **params)

            button_class = (
                "primary"
                if page_number == page
                else "secondary"
            )

            pagination_html += f"""
<a href="{url}">
<button type="button" class="{button_class}">{page_number}</button>
</a>
"""

        if page < total_pages:
            params = dict(base_params)
            params["page"] = page + 1
            url = build_url("/", lang, **params)

            pagination_html += f"""
<a href="{url}">
<button type="button" class="secondary">{esc(t["next"])} →</button>
</a>
"""

        pagination_html += (
            f'<span class="page-info">'
            f'{esc(t["page"])} {page} {esc(t["of"])} {total_pages}'
            f'</span></div>'
        )

        start_record = (
            offset_value + 1
            if filtered_total
            else 0
        )

        end_record = min(
            offset_value + len(books),
            filtered_total,
        )

        content = f"""
<div class="hero">
    <h1>{esc(t["catalogue_title"])}</h1>
    <p>{esc(t["catalogue_subtitle"])}</p>
</div>

<div class="card">

<form method="get">

<input type="hidden" name="lang" value="{lang}">

<div class="filters">

<input
    type="text"
    name="q"
    value="{esc(q)}"
    placeholder="{esc(t["search_placeholder"])}"
>

<select name="publisher">
{publisher_options}
</select>

<select name="language">
{language_options}
</select>

<select name="subject">
{subject_options}
</select>

<button class="primary" type="submit">
{esc(t["search"])}
</button>

</div>

<div class="tip">
<strong>{esc(t["quick_tip"])}:</strong>
{esc(t["quick_tip_text"])}
</div>

</form>
</div>

<div class="stats">

<div class="stat">
<span class="stat-label">{esc(t["total_catalogue"])}</span>
<span class="stat-value">{total_books}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["showing"])}</span>
<span class="stat-value">{start_record}-{end_record} / {filtered_total}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["selected"])}</span>
<span class="stat-value" id="topSelectedCount">0</span>
</div>

</div>

<form
    method="post"
    action="/submit-selection"
    onsubmit="return validateSelection();"
>

<input type="hidden" name="lang" value="{lang}">

<div class="card">

<h3 class="section-title">
<span class="section-icon">01</span>
{esc(t["your_information"])}
</h3>

<div class="user-grid">

<input
    type="text"
    name="full_name"
    placeholder="{esc(t["full_name"])}"
    required
>

<input
    type="text"
    name="user_id"
    placeholder="{esc(t["user_id"])}"
>

<input
    type="text"
    name="department"
    placeholder="{esc(t["department"])}"
    required
>

<input
    type="email"
    name="email"
    placeholder="{esc(t["email"])}"
>

</div>
</div>

<div class="card">

<div class="toolbar">

<h3 class="section-title" style="margin:0;">
<span class="section-icon">02</span>
{esc(t["available_books"])}
</h3>

<div>
<button
    type="button"
    class="secondary"
    onclick="selectAllVisible()"
>
{esc(t["select_page"])}
</button>

<button
    type="button"
    class="secondary"
    onclick="clearAll()"
>
{esc(t["clear"])}
</button>
</div>

</div>

<div class="table-wrap">
<table>

<thead>
<tr>
<th>{esc(t["select"])}</th>
<th>{esc(t["title"])}</th>
<th>{esc(t["author"])}</th>
<th>{esc(t["publisher"])}</th>
<th>{esc(t["year"])}</th>
<th>{esc(t["isbn"])}</th>
<th>{esc(t["price"])}</th>
<th>{esc(t["subject"])}</th>
<th>{esc(t["language"])}</th>
</tr>
</thead>

<tbody>
{rows}
</tbody>

</table>
</div>

{pagination_html}

</div>

<div class="action-bar">

<div class="selected-count">
<span id="selectedCount">0</span>
{esc(t["books_selected"])}
</div>

<button class="warning" type="submit">
{esc(t["submit_cart"])}
</button>

</div>

</form>

<script>
function getChecks() {{
    return Array.from(
        document.querySelectorAll(".book-check")
    );
}}

function updateCount() {{
    const count = getChecks()
        .filter(item => item.checked)
        .length;

    document.getElementById("selectedCount").innerText = count;
    document.getElementById("topSelectedCount").innerText = count;
}}

function selectAllVisible() {{
    getChecks().forEach(item => item.checked = true);
    updateCount();
}}

function clearAll() {{
    getChecks().forEach(item => item.checked = false);
    updateCount();
}}

function validateSelection() {{
    const count = getChecks()
        .filter(item => item.checked)
        .length;

    if (count === 0) {{
        alert({repr(t["select_one"])});
        return false;
    }}

    return true;
}}
</script>
"""

        return page_template(
            content,
            t["catalogue_title"],
            lang=lang,
        )

    finally:
        db.close()


# =========================================================
# SUBMIT USER SELECTION
# =========================================================

@app.post(
    "/submit-selection",
    response_class=HTMLResponse,
)
async def submit_selection(request: Request):
    form = await request.form()

    lang, t = lang_pack(str(form.get("lang", "en")))

    full_name = str(form.get("full_name", "")).strip()
    user_id = str(form.get("user_id", "")).strip()
    department = str(form.get("department", "")).strip()
    email = str(form.get("email", "")).strip()
    raw_book_ids = form.getlist("book_ids")

    if not full_name:
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["full_name_required"])}</div>',
                lang=lang,
            ),
            status_code=400,
        )

    if not department:
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["department_required"])}</div>',
                lang=lang,
            ),
            status_code=400,
        )

    if not raw_book_ids:
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["select_one"])}</div>',
                lang=lang,
            ),
            status_code=400,
        )

    book_ids = []

    for value in raw_book_ids:
        try:
            book_ids.append(int(value))
        except Exception:
            pass

    book_ids = list(dict.fromkeys(book_ids))

    db = SessionLocal()

    try:
        books = (
            db.query(Book)
            .filter(Book.id.in_(book_ids))
            .all()
        )

        if not books:
            return HTMLResponse(
                page_template(
                    f'<div class="card">{esc(t["no_valid_books"])}</div>',
                    lang=lang,
                ),
                status_code=400,
            )

        selector = Selector(
            full_name=full_name,
            user_id=user_id or None,
            department=department,
            email=email or None,
        )

        db.add(selector)
        db.flush()

        cart = SelectionCart(
            selector_id=selector.id,
            status="Submitted",
        )

        db.add(cart)
        db.flush()

        for book in books:
            db.add(
                SelectionItem(
                    cart_id=cart.id,
                    book_id=book.id,
                    requested_quantity=1,
                    admin_approved_quantity=0,
                    admin_status="Pending",
                )
            )

        db.commit()

        return_url = build_url("/", lang)

        content = f"""
<div class="card success">

<div class="success-icon">✓</div>

<h1>{esc(t["selection_submitted"])}</h1>

<p>
{esc(t["thank_you"])},
<strong>{esc(full_name)}</strong>.
</p>

<p>{esc(t["selection_sent"])}</p>

<div class="stats" style="max-width:760px;margin:25px auto;">

<div class="stat">
<span class="stat-label">{esc(t["cart_id"])}</span>
<span class="stat-value">{cart.id}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["selected_books"])}</span>
<span class="stat-value">{len(books)}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["status"])}</span>
<span class="stat-value" style="font-size:18px;">{esc(t["submitted"])}</span>
</div>

</div>

<a href="{return_url}">
<button class="primary">{esc(t["return_catalogue"])}</button>
</a>

</div>
"""

        return page_template(
            content,
            t["selection_submitted"],
            lang=lang,
        )

    except Exception as error:
        db.rollback()

        return HTMLResponse(
            page_template(
                f"""
<div class="card">
<h2>{esc(t["unable_submit"])}</h2>
<p>{esc(error)}</p>
</div>
""",
                lang=lang,
            ),
            status_code=500,
        )

    finally:
        db.close()


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.get(
    "/admin",
    response_class=HTMLResponse,
)
def admin_dashboard(
    lang: str = "en",
):
    lang, t = lang_pack(lang)
    db = SessionLocal()

    try:
        total_books = db.query(Book).count()
        total_carts = db.query(SelectionCart).count()
        total_users = db.query(Selector).count()
        total_items = db.query(SelectionItem).count()

        pending_items = (
            db.query(SelectionItem)
            .filter(SelectionItem.admin_status == "Pending")
            .count()
        )

        approved_items = (
            db.query(SelectionItem)
            .filter(SelectionItem.admin_status == "Approved")
            .count()
        )

        rejected_items = (
            db.query(SelectionItem)
            .filter(SelectionItem.admin_status == "Rejected")
            .count()
        )

        carts = (
            db.query(SelectionCart)
            .order_by(SelectionCart.id.desc())
            .all()
        )

        cart_rows = ""

        for cart in carts:
            selector = cart.selector

            book_count = (
                db.query(SelectionItem)
                .filter(SelectionItem.cart_id == cart.id)
                .count()
            )

            submitted = (
                cart.submitted_at.strftime("%d/%m/%Y %H:%M")
                if cart.submitted_at
                else ""
            )

            cart_rows += f"""
<tr>
<td>{cart.id}</td>
<td>{esc(selector.full_name if selector else "")}</td>
<td>{esc(selector.user_id if selector else "")}</td>
<td>{esc(selector.department if selector else "")}</td>
<td>{esc(selector.email if selector else "")}</td>
<td>{book_count}</td>
<td>{esc(submitted)}</td>
<td>{esc(cart.status)}</td>
</tr>
"""

        if not cart_rows:
            cart_rows = f"""
<tr>
<td colspan="8">{esc(t["no_carts"])}</td>
</tr>
"""

        demand = (
            db.query(
                Book.id.label("book_id"),
                Book.title,
                Book.author,
                Book.source_publisher,
                Book.price,
                Book.currency,
                func.count(
                    func.distinct(
                        SelectionCart.selector_id
                    )
                ).label("user_count"),
                func.count(
                    SelectionItem.id
                ).label("request_count"),
            )
            .join(
                SelectionItem,
                SelectionItem.book_id == Book.id,
            )
            .join(
                SelectionCart,
                SelectionCart.id == SelectionItem.cart_id,
            )
            .group_by(
                Book.id,
                Book.title,
                Book.author,
                Book.source_publisher,
                Book.price,
                Book.currency,
            )
            .order_by(
                func.count(
                    func.distinct(
                        SelectionCart.selector_id
                    )
                ).desc(),
                Book.title.asc(),
            )
            .all()
        )

        demand_rows = ""

        for row in demand:
            items = (
                db.query(SelectionItem)
                .filter(SelectionItem.book_id == row.book_id)
                .all()
            )

            statuses = [
                item.admin_status
                for item in items
                if item.admin_status
            ]

            approved_qty = max(
                [
                    item.admin_approved_quantity or 0
                    for item in items
                ]
                or [0]
            )

            if "Approved" in statuses:
                status = t["approved"]
                status_value = "Approved"
                status_class = "status-approved"

            elif statuses and all(
                s == "Rejected"
                for s in statuses
            ):
                status = t["rejected"]
                status_value = "Rejected"
                status_class = "status-rejected"

            else:
                status = t["pending"]
                status_value = "Pending"
                status_class = "status-pending"

            price_text = (
                f"{row.price:g} {row.currency or ''}"
                if row.price is not None
                else ""
            )

            title_class = (
                "arabic"
                if row.title
                and any(
                    "\u0600" <= ch <= "\u06FF"
                    for ch in row.title
                )
                else ""
            )

            demand_rows += f"""
<tr>

<td>
<input
    type="checkbox"
    class="bulk-book"
    name="book_ids"
    value="{row.book_id}"
    data-status="{status_value}"
    form="bulkDecisionForm"
>
</td>

<td class="title {title_class}">
{esc(row.title)}
</td>

<td>{esc(row.author)}</td>
<td>{esc(row.source_publisher)}</td>
<td><strong>{row.user_count}</strong></td>
<td>{row.request_count}</td>
<td class="price">{esc(price_text)}</td>

<td>
<span class="status {status_class}">
{esc(status)}
</span>
</td>

<td>
<form
    method="post"
    action="/admin/book/{row.book_id}/decision"
    class="inline-form"
>

<input type="hidden" name="lang" value="{lang}">

<input
    type="number"
    name="quantity"
    min="0"
    value="{approved_qty}"
>

<button
    type="submit"
    name="decision"
    value="Approved"
    class="success-btn"
>
{esc(t["approve"])}
</button>

<button
    type="submit"
    name="decision"
    value="Rejected"
    class="danger"
>
{esc(t["reject"])}
</button>

<button
    type="submit"
    name="decision"
    value="Pending"
    class="secondary"
>
{esc(t["reset"])}
</button>

</form>
</td>

</tr>
"""

        if not demand_rows:
            demand_rows = f"""
<tr>
<td colspan="9">{esc(t["no_demand"])}</td>
</tr>
"""

        final_rows = ""
        approved_count = 0
        total_estimated = 0.0

        approved_book_ids = [
            r[0]
            for r in (
                db.query(SelectionItem.book_id)
                .filter(
                    SelectionItem.admin_status
                    == "Approved"
                )
                .distinct()
                .all()
            )
        ]

        if approved_book_ids:
            approved_books = (
                db.query(Book)
                .filter(Book.id.in_(approved_book_ids))
                .all()
            )
        else:
            approved_books = []

        for book in approved_books:
            approved_selection_items = (
                db.query(SelectionItem)
                .filter(
                    SelectionItem.book_id == book.id,
                    SelectionItem.admin_status == "Approved",
                )
                .all()
            )

            final_qty = max(
                [
                    item.admin_approved_quantity or 0
                    for item in approved_selection_items
                ]
                or [0]
            )

            if final_qty <= 0:
                continue

            approved_count += 1

            line_total = 0.0

            if book.price is not None:
                line_total = float(book.price) * final_qty
                total_estimated += line_total

            price_text = (
                f"{book.price:g} {book.currency or ''}"
                if book.price is not None
                else ""
            )

            total_text = (
                f"{line_total:,.2f} {book.currency or ''}"
                if book.price is not None
                else ""
            )

            final_rows += f"""
<tr>
<td>{esc(book.title)}</td>
<td>{esc(book.author)}</td>
<td>{esc(book.source_publisher)}</td>
<td>{final_qty}</td>
<td>{esc(price_text)}</td>
<td>{esc(total_text)}</td>
</tr>
"""

        if not final_rows:
            final_rows = f"""
<tr>
<td colspan="6">{esc(t["no_approved"])}</td>
</tr>
"""

        export_url = build_url("/admin/export-final", lang)
        publisher_orders_url = build_url("/admin/export-publisher-orders", lang)

        content = f"""
<div class="hero">
<h1>{esc(t["admin_title"])}</h1>
<p>{esc(t["admin_subtitle"])}</p>
</div>

<div class="card">
<h2 class="section-title">
<span class="section-icon">01</span>
{esc(t["workflow"])}
</h2>

<div class="workflow-grid">
<div class="workflow-step">{esc(t["workflow_1"])}</div>
<div class="workflow-step">{esc(t["workflow_2"])}</div>
<div class="workflow-step">{esc(t["workflow_3"])}</div>
<div class="workflow-step">{esc(t["workflow_4"])}</div>
</div>
</div>

<div class="admin-actions">

<div class="card">
<h2>{esc(t["upload_master"])}</h2>
<p class="small">{esc(t["upload_master_help"])}</p>

<form
    method="post"
    action="/admin/generate-master"
    enctype="multipart/form-data"
    onsubmit="return confirm({repr(t["master_warning"])});"
>
<input type="hidden" name="lang" value="{lang}">

<div class="upload-box">
<input
    type="file"
    name="publisher_files"
    accept=".xlsx,.xls"
    multiple
    required
>
</div>

<div style="margin-top:12px;">
<button class="primary" type="submit">
{esc(t["publish_master"])}
</button>
</div>
</form>
</div>

<div class="card">
<h2>{esc(t["new_cycle"])}</h2>
<p class="small">{esc(t["new_cycle_help"])}</p>

<form
    method="post"
    action="/admin/reset-selections"
    onsubmit="return confirm({repr(t["cycle_warning"])});"
>
<input type="hidden" name="lang" value="{lang}">
<button class="danger" type="submit">
{esc(t["reset_cycle"])}
</button>
</form>
</div>

</div>

<div class="admin-kpis">

<div class="stat">
<span class="stat-label">{esc(t["total_catalogue"])}</span>
<span class="stat-value">{total_books}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["submitted_carts"])}</span>
<span class="stat-value">{total_carts}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["users"])}</span>
<span class="stat-value">{total_users}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["selections"])}</span>
<span class="stat-value">{total_items}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["pending"])}</span>
<span class="stat-value">{pending_items}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["approved"])}</span>
<span class="stat-value">{approved_items}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["rejected"])}</span>
<span class="stat-value">{rejected_items}</span>
</div>

</div>

<div class="card">

<div class="toolbar">

<div>
<h2 style="margin:0 0 5px;">
{esc(t["aggregated_demand"])}
</h2>

<div class="small">
{esc(t["aggregated_help"])}
</div>
</div>

<div style="display:flex;gap:8px;flex-wrap:wrap;">
<a href="{export_url}">
<button class="primary">
{esc(t["export_final"])}
</button>
</a>

<a href="{publisher_orders_url}">
<button class="warning">
{esc(t["generate_publisher_orders"])}
</button>
</a>
</div>

</div>

<form method="post" action="/admin/bulk-decision" id="bulkDecisionForm">
<input type="hidden" name="lang" value="{lang}">

<div class="toolbar" style="margin:14px 0;justify-content:flex-start;">
<div>
<label class="small"><strong>{esc(t["bulk_default_qty"])}</strong></label><br>
<input type="number" name="final_quantity" value="1" min="1" style="width:110px;">
</div>

<button type="button" class="secondary" onclick="selectPending()">
{esc(t["select_all_pending"])}
</button>

<button type="button" class="secondary" onclick="clearBulk()">
{esc(t["clear_selected"])}
</button>

<button type="submit" name="decision" value="Approved" class="primary" onclick="return validateBulk();">
{esc(t["approve_selected"])}
</button>

<button type="submit" name="decision" value="Rejected" class="danger" onclick="return validateBulk();">
{esc(t["reject_selected"])}
</button>
</div>
</form>

<script>
function selectPending() {{
    document.querySelectorAll('.bulk-book').forEach(function(cb) {{
        cb.checked = (cb.dataset.status || '').toLowerCase() === 'pending';
    }});
}}
function clearBulk() {{
    document.querySelectorAll('.bulk-book').forEach(function(cb) {{
        cb.checked = false;
    }});
}}
function validateBulk() {{
    var checked = document.querySelectorAll('.bulk-book:checked').length;
    if (!checked) {{
        alert({repr(t["select_books_first"])});
        return false;
    }}
    return true;
}}
</script>

<div class="table-wrap">
<table>

<thead>
<tr>
<th style="width:48px;">✓</th>
<th>{esc(t["title"])}</th>
<th>{esc(t["author"])}</th>
<th>{esc(t["publisher"])}</th>
<th>{esc(t["requested_by"])}</th>
<th>{esc(t["total_requests"])}</th>
<th>{esc(t["price"])}</th>
<th>{esc(t["status"])}</th>
<th>{esc(t["admin_decision"])}</th>
</tr>
</thead>

<tbody>
{demand_rows}
</tbody>

</table>
</div>
</div>

<div class="admin-grid">

<div class="card">

<h2 class="section-title">
<span class="section-icon">03</span>
{esc(t["submitted_carts"])}
</h2>

<div class="table-wrap">
<table>

<thead>
<tr>
<th>{esc(t["cart"])}</th>
<th>{esc(t["name"])}</th>
<th>{esc(t["id"])}</th>
<th>{esc(t["department"])}</th>
<th>{esc(t["email"])}</th>
<th>{esc(t["books"])}</th>
<th>{esc(t["submitted_at"])}</th>
<th>{esc(t["status"])}</th>
</tr>
</thead>

<tbody>
{cart_rows}
</tbody>

</table>
</div>
</div>

<div class="card">

<h2 class="section-title">
<span class="section-icon">04</span>
{esc(t["final_order"])}
</h2>

<div class="stats" style="grid-template-columns:1fr 1fr;">

<div class="stat">
<span class="stat-label">{esc(t["approved_titles"])}</span>
<span class="stat-value">{approved_count}</span>
</div>

<div class="stat">
<span class="stat-label">{esc(t["estimated_value"])}</span>
<span class="stat-value">{total_estimated:,.2f}</span>
</div>

</div>

<div class="table-wrap">
<table>

<thead>
<tr>
<th>{esc(t["title"])}</th>
<th>{esc(t["author"])}</th>
<th>{esc(t["publisher"])}</th>
<th>{esc(t["final_qty"])}</th>
<th>{esc(t["unit_price"])}</th>
<th>{esc(t["estimated_total"])}</th>
</tr>
</thead>

<tbody>
{final_rows}
</tbody>

</table>
</div>
</div>

</div>
"""

        return page_template(
            content,
            t["admin_title"],
            lang=lang,
            admin=True,
        )

    finally:
        db.close()



# =========================================================
# ADMIN — START NEW SELECTION CYCLE
# =========================================================

@app.post("/admin/reset-selections", response_class=HTMLResponse)
async def reset_selections(request: Request):
    form = await request.form()
    lang, t = lang_pack(str(form.get("lang", "en")))
    db = SessionLocal()

    try:
        db.query(SelectionItem).delete(synchronize_session=False)
        db.query(SelectionCart).delete(synchronize_session=False)
        db.query(Selector).delete(synchronize_session=False)
        db.commit()

        return HTMLResponse(
            page_template(
                f"""
<div class="card success">
<div class="success-icon">✓</div>
<h2>{esc(t["cycle_reset_done"])}</h2>
<p>{esc(t["new_cycle_help"])}</p>
<a href="{build_url("/admin", lang)}">
<button class="primary">{esc(t["return_admin"])}</button>
</a>
</div>
""",
                t["new_cycle"],
                lang=lang,
                admin=True,
            )
        )

    except Exception as error:
        db.rollback()
        return HTMLResponse(
            page_template(
                f"""
<div class="card">
<h2>{esc(t["unable_submit"])}</h2>
<p>{esc(error)}</p>
</div>
""",
                lang=lang,
                admin=True,
            ),
            status_code=500,
        )

    finally:
        db.close()



# =========================================================
# ADMIN — MULTI PUBLISHER FILES -> MASTER -> PUBLISH
# =========================================================

@app.post("/admin/generate-master", response_class=HTMLResponse)
async def generate_and_publish_master(request: Request):
    form = await request.form()
    lang, t = lang_pack(str(form.get("lang", "en")))
    uploads = form.getlist("publisher_files")

    uploads = [
        item for item in uploads
        if getattr(item, "filename", "")
    ]

    if not uploads:
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["master_upload_error"])}</div>',
                lang=lang,
                admin=True,
            ),
            status_code=400,
        )

    aliases = {
        "Title": [
            "Title", "Book Title", "Book Name",
            "العنوان", "عنوان", "عنوان الكتاب", "اسم الكتاب", "اسم الكتاب / العنوان",
            "عنوان المؤلف", "الكتاب", "الكتب", "اسم المؤلف / الكتاب"
        ],
        "Author": [
            "Author", "Authors", "Author Name",
            "المؤلف", "المؤلفون", "اسم المؤلف", "اسم المؤلفين", "المؤلف / المحقق",
            "المؤلف/المحقق", "المؤلف والمحقق", "المؤلف/المترجم", "المؤلف / المترجم"
        ],
        "Publisher": [
            "Publisher", "Publishing House",
            "الناشر", "دار النشر", "جهة النشر", "اسم الناشر", "دار النشر / الناشر"
        ],
        "Publication Year": [
            "Publication Year", "Year", "Pub Year", "Publishing Year",
            "سنة النشر", "عام النشر", "السنة", "تاريخ النشر", "سنه النشر",
            "سنة الاصدار", "سنة الإصدار", "عام الاصدار", "عام الإصدار"
        ],
        "ISBN": [
            "ISBN", "ISBN-13", "ISBN13", "ISBN 13",
            "ردمك", "الرقم الدولي", "الرقم الدولي للكتاب", "الترقيم الدولي للكتاب",
            "الرقم الدولى", "الرقم الدولى للكتاب", "رقم دولي", "رقم دولى"
        ],
        "Price": [
            "Price", "Unit Price", "AED Price", "Price AED", "Dollar Price",
            "السعر", "سعر", "السعر بالدرهم", "سعر بالدرهم", "درهم", "السعر درهم",
            "السعر بالدولار", "سعر بالدولار", "دولار", "السعر دولار", "price usd", "price aed"
        ],
        "Currency": [
            "Currency", "العملة", "نوع العملة"
        ],
        "Subject": [
            "Subject", "Subjects", "Category", "Specialization",
            "الموضوع", "الموضوعات", "التخصص", "التصنيف", "القسم", "المجال",
            "التخصص العام", "التخصص الدقيق"
        ],
        "Language": [
            "Language", "Book Language", "اللغة", "لغة الكتاب"
        ],
        "Vendor": [
            "Vendor", "Supplier", "Bookseller",
            "المورد", "اسم المورد"
        ],
    }

    all_records = []
    mapping_rows = []
    skipped = []
    source_rows = 0
    processed_files = 0

    for upload in uploads:
        filename = getattr(upload, "filename", "") or ""
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        if extension not in {"xlsx", "xls"}:
            skipped.append({"File": filename, "Reason": "Unsupported file type"})
            continue

        try:
            raw = await upload.read()
            engine = "openpyxl" if extension == "xlsx" else "xlrd"
            excel_file = pd.ExcelFile(io.BytesIO(raw), engine=engine)
            source_publisher = publisher_from_filename(filename)
            file_had_records = False

            for sheet_name in excel_file.sheet_names:
                try:
                    header_row, header_score = detect_header_row(
                        raw,
                        sheet_name,
                        engine,
                        aliases,
                        max_rows=15,
                    )

                    # Notes/summary/instruction sheets are ignored unless they
                    # clearly contain a real bibliographic table.
                    if is_non_catalogue_sheet(sheet_name) and header_score < 3:
                        skipped.append({
                            "File": filename,
                            "Reason": (
                                f"Ignored non-catalogue sheet {sheet_name}; "
                                f"bibliographic header score={header_score}"
                            ),
                        })
                        continue

                    df = pd.read_excel(
                        io.BytesIO(raw),
                        sheet_name=sheet_name,
                        engine=engine,
                        dtype=object,
                        header=header_row,
                    )
                except Exception as error:
                    skipped.append({
                        "File": filename,
                        "Reason": f"Sheet {sheet_name}: {error}",
                    })
                    continue

                if df.empty:
                    continue

                cols = map_columns_safely(df, aliases)
                cols = infer_columns_from_data(df, cols)

                recovery_method = "Exact header mapping"

                if not cols["Title"]:
                    fallback_title = (
                        None
                        if is_non_catalogue_sheet(sheet_name)
                        else choose_title_fallback(df, cols)
                    )
                    if fallback_title is not None:
                        cols["Title"] = fallback_title
                        recovery_method = "Data-assisted title recovery"
                    else:
                        skipped.append({
                            "File": filename,
                            "Reason": (
                                f"No safe Title column found in sheet {sheet_name}; "
                                f"best header row={header_row + 1}, header score={header_score}"
                            ),
                        })
                        continue

                mapping_rows.append({
                    "Source File": filename,
                    "Source Sheet": sheet_name,
                    "Detected Header Row": header_row + 1,
                    "Header Match Score": header_score,
                    "Recovery Method": recovery_method,
                    **{
                        f"{standard} Column": cols.get(standard) or ""
                        for standard in aliases
                    },
                })

                for _, row in df.iterrows():
                    def get_value(standard):
                        col = cols.get(standard)
                        if not col:
                            return None
                        value = row.get(col)
                        if pd.isna(value):
                            return None
                        value = str(value).strip()
                        return value if value else None

                    title = get_value("Title")
                    author = get_value("Author")
                    isbn = valid_isbn(get_value("ISBN"))

                    # Ignore blank/non-bibliographic rows.
                    if not title and not author and not isbn:
                        continue
                    if not title:
                        continue

                    source_rows += 1
                    file_had_records = True

                    publisher = get_value("Publisher") or source_publisher
                    vendor = get_value("Vendor") or source_publisher

                    price_number = valid_price(get_value("Price"))

                    language = get_value("Language")
                    if not language:
                        sample = " ".join(
                            str(v or "")
                            for v in [title, author, get_value("Subject")]
                        )
                        language = (
                            "Arabic"
                            if any("\u0600" <= ch <= "\u06FF" for ch in sample)
                            else "English"
                        )

                    currency = get_value("Currency")
                    if not currency and price_number is not None:
                        price_header = str(cols.get("Price") or "").lower()
                        if "دولار" in price_header or "dollar" in price_header or "usd" in price_header:
                            currency = "USD"
                        else:
                            currency = "AED"

                    all_records.append({
                        "Title": title,
                        "Author": author,
                        "Publisher": publisher,
                        "Source Publisher": source_publisher,
                        "Publication Year": valid_year(get_value("Publication Year")),
                        "ISBN": isbn,
                        "Price": price_number,
                        "Currency": currency,
                        "Subject": get_value("Subject"),
                        "Language": language,
                        "Vendor": vendor,
                        "Source File": filename,
                        "Source Sheet": sheet_name,
                        "Validation Status": "; ".join(
                            issue for issue in [
                                "Missing Author" if not author else "",
                                "Missing Year" if not valid_year(get_value("Publication Year")) else "",
                                "Missing ISBN" if not isbn else "",
                                "Missing Price" if price_number is None else "",
                                "Missing Subject" if not get_value("Subject") else "",
                            ]
                            if issue
                        ) or "OK",
                    })

            if file_had_records:
                processed_files += 1

        except Exception as error:
            skipped.append({"File": filename, "Reason": str(error)})

    if not all_records:
        return HTMLResponse(
            page_template(
                f"""
<div class="card">
<h2>{esc(t["master_upload_error"])}</h2>
<p>No bibliographic records could be extracted from the uploaded files.</p>
</div>
""",
                lang=lang,
                admin=True,
            ),
            status_code=400,
        )

    # Consolidate true duplicates. Prefer the more complete version of a record.
    unique = {}
    duplicate_count = 0

    for record in all_records:
        key = book_dedupe_key(record)

        if key not in unique:
            unique[key] = record
            continue

        duplicate_count += 1
        existing = unique[key]

        for field, value in record.items():
            if existing.get(field) in (None, "") and value not in (None, ""):
                existing[field] = value

    master_records = list(unique.values())
    master_df = pd.DataFrame(master_records)

    preferred_columns = [
        "Title",
        "Author",
        "Publisher",
        "Source Publisher",
        "Publication Year",
        "ISBN",
        "Price",
        "Currency",
        "Subject",
        "Language",
        "Vendor",
        "Source File",
        "Source Sheet",
        "Validation Status",
    ]
    master_df = master_df[
        [c for c in preferred_columns if c in master_df.columns]
    ]

    # Generate the downloadable master workbook on disk.
    generated_dir = Path("generated")
    generated_dir.mkdir(exist_ok=True)
    generated_path = generated_dir / "AcquiAI_Master_Acquisition.xlsx"

    with pd.ExcelWriter(generated_path, engine="openpyxl") as writer:
        master_df.to_excel(
            writer,
            index=False,
            sheet_name="Master Acquisition",
        )

        publisher_summary = (
            master_df.groupby("Source Publisher", dropna=False)
            .agg(
                Titles=("Title", "count"),
                Total_Value=("Price", "sum"),
            )
            .reset_index()
        )
        publisher_summary.to_excel(
            writer,
            index=False,
            sheet_name="Publisher Summary",
        )

        if mapping_rows:
            pd.DataFrame(mapping_rows).to_excel(
                writer,
                index=False,
                sheet_name="Mapping Report",
            )

        if skipped:
            pd.DataFrame(skipped).to_excel(
                writer,
                index=False,
                sheet_name="Skipped Files",
            )

        for sheet_name in writer.book.sheetnames:
            ws = writer.book[sheet_name]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for column_cells in ws.columns:
                max_length = max(
                    (
                        len(str(cell.value))
                        if cell.value is not None
                        else 0
                    )
                    for cell in column_cells
                )
                ws.column_dimensions[
                    column_cells[0].column_letter
                ].width = min(max_length + 2, 50)

    # Publish the generated master directly to the portal database.
    db = SessionLocal()

    try:
        db.query(SelectionItem).delete(synchronize_session=False)
        db.query(SelectionCart).delete(synchronize_session=False)
        db.query(Selector).delete(synchronize_session=False)
        db.query(Book).delete(synchronize_session=False)

        for record in master_records:
            db.add(
                Book(
                    title=record.get("Title"),
                    author=record.get("Author"),
                    publisher=record.get("Publisher"),
                    source_publisher=record.get("Source Publisher"),
                    publication_year=record.get("Publication Year"),
                    isbn=record.get("ISBN"),
                    price=record.get("Price"),
                    currency=record.get("Currency"),
                    subject=record.get("Subject"),
                    language=record.get("Language"),
                )
            )

        db.commit()

    except Exception as error:
        db.rollback()
        return HTMLResponse(
            page_template(
                f"""
<div class="card">
<h2>{esc(t["master_upload_error"])}</h2>
<p>{esc(error)}</p>
</div>
""",
                lang=lang,
                admin=True,
            ),
            status_code=500,
        )
    finally:
        db.close()

    skipped_count = len(skipped)

    return HTMLResponse(
        page_template(
            f"""
<div class="card success">
<div class="success-icon">✓</div>
<h1>{esc(t["master_import_done"])}</h1>
<p>{esc(t["published_to_users"])}</p>
<p class="small"><strong>✓</strong> {esc(t["mapping_fixed"])}</p>

<div class="stats" style="grid-template-columns:repeat(4,1fr);max-width:1000px;margin:24px auto;">
<div class="stat">
<span class="stat-label">{esc(t["files_processed"])}</span>
<span class="stat-value">{processed_files}</span>
</div>
<div class="stat">
<span class="stat-label">{esc(t["source_rows"])}</span>
<span class="stat-value">{source_rows}</span>
</div>
<div class="stat">
<span class="stat-label">{esc(t["unique_titles"])}</span>
<span class="stat-value">{len(master_records)}</span>
</div>
<div class="stat">
<span class="stat-label">{esc(t["duplicates_removed"])}</span>
<span class="stat-value">{duplicate_count}</span>
</div>
</div>

<p>{esc(t["skipped_files"])}: <strong>{skipped_count}</strong></p>

<a href="{build_url("/admin/download-generated-master", lang)}">
<button class="warning">{esc(t["download_generated_master"])}</button>
</a>

<a href="{build_url("/", lang)}">
<button class="primary">{esc(t["portal"])}</button>
</a>

<a href="{build_url("/admin", lang)}">
<button class="secondary">{esc(t["return_admin"])}</button>
</a>
</div>
""",
            t["master_import_done"],
            lang=lang,
            admin=True,
        )
    )


@app.get("/admin/download-generated-master")
def download_generated_master(lang: str = "en"):
    path = Path("generated") / "AcquiAI_Master_Acquisition.xlsx"

    if not path.exists():
        lang, t = lang_pack(lang)
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["master_upload_error"])}</div>',
                lang=lang,
                admin=True,
            ),
            status_code=404,
        )

    from fastapi.responses import FileResponse

    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="AcquiAI_Master_Acquisition.xlsx",
    )


# =========================================================
# ADMIN — UPLOAD / REPLACE MASTER CATALOGUE
# =========================================================

@app.post("/admin/import-master", response_class=HTMLResponse)
async def import_master_catalogue(request: Request):
    form = await request.form()
    lang, t = lang_pack(str(form.get("lang", "en")))
    upload = form.get("master_file")

    if upload is None:
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["master_upload_error"])}</div>',
                lang=lang,
                admin=True,
            ),
            status_code=400,
        )

    filename = getattr(upload, "filename", "") or ""
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if extension not in {"xlsx", "xls"}:
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["master_upload_error"])}</div>',
                lang=lang,
                admin=True,
            ),
            status_code=400,
        )

    try:
        raw = await upload.read()

        excel_file = pd.ExcelFile(
            io.BytesIO(raw),
            engine="openpyxl" if extension == "xlsx" else "xlrd",
        )

        preferred = None
        for sheet_name in excel_file.sheet_names:
            if normalize_colname(sheet_name) in {
                "masteracquisition",
                "finalpurchasemaster",
                "mastercatalogue",
                "catalogue",
            }:
                preferred = sheet_name
                break

        sheet_name = preferred or excel_file.sheet_names[0]

        df = pd.read_excel(
            io.BytesIO(raw),
            sheet_name=sheet_name,
            engine="openpyxl" if extension == "xlsx" else "xlrd",
            dtype=object,
        )

    except Exception as error:
        return HTMLResponse(
            page_template(
                f"""
<div class="card">
<h2>{esc(t["master_upload_error"])}</h2>
<p>{esc(error)}</p>
</div>
""",
                lang=lang,
                admin=True,
            ),
            status_code=400,
        )

    aliases = {
        "title": ["Title", "العنوان", "Book Title"],
        "author": ["Author", "Authors", "المؤلف", "المؤلفون"],
        "publisher": ["Publisher", "الناشر"],
        "source_publisher": [
            "Source Publisher",
            "Source Publisher / Vendor",
            "Vendor",
            "المورد",
            "الناشر المصدر",
        ],
        "publication_year": [
            "Publication Year",
            "Year",
            "Pub Year",
            "سنة النشر",
            "السنة",
        ],
        "isbn": ["ISBN", "ISBN-13", "ISBN13", "ردمك"],
        "price": ["Price", "Unit Price", "السعر"],
        "currency": ["Currency", "العملة"],
        "subject": ["Subject", "Subjects", "الموضوع"],
        "language": ["Language", "اللغة"],
    }

    cols = {
        key: find_column(df, names)
        for key, names in aliases.items()
    }

    if not cols["title"]:
        return HTMLResponse(
            page_template(
                f'<div class="card">{esc(t["invalid_master"])}</div>',
                lang=lang,
                admin=True,
            ),
            status_code=400,
        )

    db = SessionLocal()

    try:
        # A new master starts a completely new acquisition cycle.
        db.query(SelectionItem).delete(synchronize_session=False)
        db.query(SelectionCart).delete(synchronize_session=False)
        db.query(Selector).delete(synchronize_session=False)
        db.query(Book).delete(synchronize_session=False)

        imported = 0

        for _, row in df.iterrows():
            def value(field):
                col = cols.get(field)
                if not col:
                    return None
                v = row.get(col)
                if pd.isna(v):
                    return None
                return str(v).strip()

            title = value("title")
            if not title:
                continue

            year_value = value("publication_year")
            isbn_value = value("isbn")
            price_value = value("price")

            price_number = None
            if price_value:
                try:
                    cleaned = re.sub(r"[^0-9.\-]", "", price_value)
                    price_number = float(cleaned) if cleaned else None
                except Exception:
                    price_number = None

            source_publisher = (
                value("source_publisher")
                or value("publisher")
            )

            book = Book(
                title=title,
                author=value("author"),
                publisher=value("publisher"),
                source_publisher=source_publisher,
                publication_year=year_value,
                isbn=isbn_value,
                price=price_number,
                currency=value("currency"),
                subject=value("subject"),
                language=value("language"),
            )

            db.add(book)
            imported += 1

        db.commit()

        return HTMLResponse(
            page_template(
                f"""
<div class="card success">
<div class="success-icon">✓</div>
<h2>{esc(t["master_import_done"])}</h2>

<div class="stat" style="max-width:320px;margin:20px auto;">
<span class="stat-label">{esc(t["total_catalogue"])}</span>
<span class="stat-value">{imported}</span>
</div>

<p>{imported} {esc(t["records_imported"])}</p>

<a href="{build_url("/", lang)}">
<button class="warning">{esc(t["portal"])}</button>
</a>

<a href="{build_url("/admin", lang)}">
<button class="primary">{esc(t["return_admin"])}</button>
</a>
</div>
""",
                t["master_import_done"],
                lang=lang,
                admin=True,
            )
        )

    except Exception as error:
        db.rollback()
        return HTMLResponse(
            page_template(
                f"""
<div class="card">
<h2>{esc(t["master_upload_error"])}</h2>
<p>{esc(error)}</p>
</div>
""",
                lang=lang,
                admin=True,
            ),
            status_code=500,
        )

    finally:
        db.close()



# =========================================================
# ADMIN — BULK APPROVE / REJECT UNIQUE TITLES
# =========================================================

@app.post("/admin/bulk-decision")
async def admin_bulk_decision(request: Request):
    form = await request.form()
    lang, _ = lang_pack(str(form.get("lang", "en")))
    decision = str(form.get("decision", "")).strip()

    book_ids = []
    for raw_id in form.getlist("book_ids"):
        try:
            book_ids.append(int(raw_id))
        except (TypeError, ValueError):
            pass

    if decision not in {"Approved", "Rejected"} or not book_ids:
        return RedirectResponse(
            url=build_url("/admin", lang),
            status_code=303,
        )

    try:
        final_quantity = max(
            1,
            int(str(form.get("final_quantity", "1")).strip() or "1"),
        )
    except Exception:
        final_quantity = 1

    db = SessionLocal()

    try:
        items = (
            db.query(SelectionItem)
            .filter(SelectionItem.book_id.in_(book_ids))
            .all()
        )

        for item in items:
            item.admin_status = decision
            item.admin_approved_quantity = (
                final_quantity if decision == "Approved" else 0
            )

        db.commit()

        return RedirectResponse(
            url=build_url("/admin", lang),
            status_code=303,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# =========================================================
# ADMIN DECISION
# =========================================================

@app.post("/admin/book/{book_id}/decision")
async def admin_book_decision(
    book_id: int,
    request: Request,
):
    form = await request.form()

    lang, _ = lang_pack(str(form.get("lang", "en")))

    decision = str(
        form.get("decision", "Pending")
    ).strip()

    quantity_raw = str(
        form.get("quantity", "0")
    ).strip()

    try:
        quantity = max(0, int(quantity_raw))
    except Exception:
        quantity = 0

    if decision not in {
        "Approved",
        "Rejected",
        "Pending",
    }:
        decision = "Pending"

    if decision != "Approved":
        quantity = 0

    db = SessionLocal()

    try:
        items = (
            db.query(SelectionItem)
            .filter(SelectionItem.book_id == book_id)
            .all()
        )

        for item in items:
            item.admin_status = decision

            item.admin_approved_quantity = (
                quantity
                if decision == "Approved"
                else 0
            )

        db.commit()

        return RedirectResponse(
            url=build_url("/admin", lang),
            status_code=303,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# =========================================================
# EXPORT FINAL APPROVED EXCEL
# =========================================================

@app.get("/admin/export-final")
def export_final_approved(
    lang: str = "en",
):
    lang, t = lang_pack(lang)
    db = SessionLocal()

    try:
        records = []

        approved_book_ids = [
            r[0]
            for r in (
                db.query(SelectionItem.book_id)
                .filter(
                    SelectionItem.admin_status
                    == "Approved"
                )
                .distinct()
                .all()
            )
        ]

        if approved_book_ids:
            books = (
                db.query(Book)
                .filter(Book.id.in_(approved_book_ids))
                .all()
            )
        else:
            books = []

        for book in books:
            approved_items = (
                db.query(SelectionItem)
                .filter(
                    SelectionItem.book_id == book.id,
                    SelectionItem.admin_status == "Approved",
                )
                .all()
            )

            final_qty = max(
                [
                    item.admin_approved_quantity or 0
                    for item in approved_items
                ]
                or [0]
            )

            if final_qty <= 0:
                continue

            all_items = (
                db.query(SelectionItem)
                .filter(SelectionItem.book_id == book.id)
                .all()
            )

            selector_ids = set()

            for item in all_items:
                if item.cart:
                    selector_ids.add(
                        item.cart.selector_id
                    )

            line_total = None

            if book.price is not None:
                line_total = (
                    float(book.price)
                    * final_qty
                )

            records.append(
                {
                    "Title": book.title,
                    "Author": book.author,
                    "Publisher": book.publisher,
                    "Source Publisher": book.source_publisher,
                    "Publication Year": book.publication_year,
                    "ISBN": book.isbn,
                    "Price": book.price,
                    "Currency": book.currency,
                    "Subject": book.subject,
                    "Language": book.language,
                    "Requested By Users": len(selector_ids),
                    "Final Approved Quantity": final_qty,
                    "Estimated Line Total": line_total,
                    "Admin Status": "Approved",
                }
            )

        if not records:
            return HTMLResponse(
                page_template(
                    f"""
<div class="card success">
<h2>{esc(t["no_approved_export_title"])}</h2>
<p>{esc(t["no_approved_export_text"])}</p>

<a href="{build_url("/admin", lang)}">
<button class="primary">
{esc(t["return_admin"])}
</button>
</a>
</div>
""",
                    lang=lang,
                    admin=True,
                ),
                status_code=404,
            )

        df = pd.DataFrame(records)

        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl",
        ) as writer:

            df.to_excel(
                writer,
                index=False,
                sheet_name="Final Approved Order",
            )

            publisher_summary = (
                df.groupby(
                    "Source Publisher",
                    dropna=False,
                )
                .agg(
                    Titles=(
                        "Title",
                        "count",
                    ),
                    Total_Quantity=(
                        "Final Approved Quantity",
                        "sum",
                    ),
                    Estimated_Value=(
                        "Estimated Line Total",
                        "sum",
                    ),
                )
                .reset_index()
            )

            publisher_summary.to_excel(
                writer,
                index=False,
                sheet_name="Publisher Summary",
            )

            for sheet_name in writer.book.sheetnames:
                ws = writer.book[sheet_name]
                ws.freeze_panes = "A2"
                ws.auto_filter.ref = ws.dimensions

                for column_cells in ws.columns:
                    max_length = max(
                        (
                            len(str(cell.value))
                            if cell.value is not None
                            else 0
                        )
                        for cell in column_cells
                    )

                    column_letter = (
                        column_cells[0].column_letter
                    )

                    ws.column_dimensions[
                        column_letter
                    ].width = min(
                        max_length + 2,
                        50,
                    )

        output.seek(0)

        return StreamingResponse(
            output,
            media_type=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    'attachment; '
                    'filename="'
                    'AcquiAI_Final_Approved_Order.xlsx'
                    '"'
                )
            },
        )

    finally:
        db.close()



# =========================================================
# EXPORT SEPARATE PUBLISHER / VENDOR ORDERS AS ZIP
# =========================================================

@app.get("/admin/export-publisher-orders")
def export_publisher_orders(
    lang: str = "en",
):
    lang, t = lang_pack(lang)
    db = SessionLocal()

    try:
        approved_book_ids = [
            r[0]
            for r in (
                db.query(SelectionItem.book_id)
                .filter(
                    SelectionItem.admin_status == "Approved"
                )
                .distinct()
                .all()
            )
        ]

        if not approved_book_ids:
            return HTMLResponse(
                page_template(
                    f"""
<div class="card success">
<h2>{esc(t["no_approved_export_title"])}</h2>
<p>{esc(t["no_approved_export_text"])}</p>
<a href="{build_url("/admin", lang)}">
<button class="primary">{esc(t["return_admin"])}</button>
</a>
</div>
""",
                    lang=lang,
                    admin=True,
                ),
                status_code=404,
            )

        books = (
            db.query(Book)
            .filter(Book.id.in_(approved_book_ids))
            .all()
        )

        records = []

        for book in books:
            approved_items = (
                db.query(SelectionItem)
                .filter(
                    SelectionItem.book_id == book.id,
                    SelectionItem.admin_status == "Approved",
                )
                .all()
            )

            final_qty = max(
                [
                    item.admin_approved_quantity or 0
                    for item in approved_items
                ]
                or [0]
            )

            if final_qty <= 0:
                continue

            selector_ids = set()

            all_items = (
                db.query(SelectionItem)
                .filter(
                    SelectionItem.book_id == book.id
                )
                .all()
            )

            for item in all_items:
                if item.cart:
                    selector_ids.add(
                        item.cart.selector_id
                    )

            unit_price = (
                float(book.price)
                if book.price is not None
                else None
            )

            line_total = (
                unit_price * final_qty
                if unit_price is not None
                else None
            )

            vendor = (
                book.source_publisher
                or book.publisher
                or getattr(book, "vendor", None)
                or "Unknown Publisher"
            )

            records.append(
                {
                    "Title": book.title,
                    "Author": book.author,
                    "Publication Year": book.publication_year,
                    "ISBN": book.isbn,
                    "Publisher": book.publisher,
                    "Source Publisher / Vendor": vendor,
                    "Price": unit_price,
                    "Currency": book.currency,
                    "Subject": book.subject,
                    "Language": book.language,
                    "Requested By Users": len(selector_ids),
                    "Final Approved Quantity": final_qty,
                    "Estimated Line Total": line_total,
                }
            )

        if not records:
            return HTMLResponse(
                page_template(
                    f"""
<div class="card success">
<h2>{esc(t["no_approved_export_title"])}</h2>
<p>{esc(t["no_approved_export_text"])}</p>
<a href="{build_url("/admin", lang)}">
<button class="primary">{esc(t["return_admin"])}</button>
</a>
</div>
""",
                    lang=lang,
                    admin=True,
                ),
                status_code=404,
            )

        df = pd.DataFrame(records)

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zip_file:

            # One Excel file per publisher/vendor
            for vendor, vendor_df in df.groupby(
                "Source Publisher / Vendor",
                dropna=False,
            ):
                vendor_name = (
                    vendor
                    if vendor not in (None, "", float("nan"))
                    else "Unknown Publisher"
                )

                excel_buffer = io.BytesIO()

                with pd.ExcelWriter(
                    excel_buffer,
                    engine="openpyxl",
                ) as writer:

                    vendor_df.to_excel(
                        writer,
                        index=False,
                        sheet_name="Purchase Order",
                    )

                    summary_df = pd.DataFrame(
                        [
                            {
                                "Publisher / Vendor": vendor_name,
                                "Unique Titles": len(vendor_df),
                                "Total Quantity": int(
                                    vendor_df[
                                        "Final Approved Quantity"
                                    ].sum()
                                ),
                                "Estimated Value": (
                                    vendor_df[
                                        "Estimated Line Total"
                                    ]
                                    .fillna(0)
                                    .sum()
                                ),
                            }
                        ]
                    )

                    summary_df.to_excel(
                        writer,
                        index=False,
                        sheet_name="Summary",
                    )

                    for sheet_name in writer.book.sheetnames:
                        ws = writer.book[sheet_name]
                        ws.freeze_panes = "A2"
                        ws.auto_filter.ref = ws.dimensions

                        for column_cells in ws.columns:
                            max_length = max(
                                (
                                    len(str(cell.value))
                                    if cell.value is not None
                                    else 0
                                )
                                for cell in column_cells
                            )

                            ws.column_dimensions[
                                column_cells[0].column_letter
                            ].width = min(
                                max_length + 2,
                                50,
                            )

                excel_buffer.seek(0)

                filename = (
                    f"{safe_filename(vendor_name)}_Purchase_Order.xlsx"
                )

                zip_file.writestr(
                    filename,
                    excel_buffer.getvalue(),
                )

            # Also include consolidated master order
            master_buffer = io.BytesIO()

            with pd.ExcelWriter(
                master_buffer,
                engine="openpyxl",
            ) as writer:
                df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Final Purchase Master",
                )

                publisher_summary = (
                    df.groupby(
                        "Source Publisher / Vendor",
                        dropna=False,
                    )
                    .agg(
                        Unique_Titles=("Title", "count"),
                        Total_Quantity=(
                            "Final Approved Quantity",
                            "sum",
                        ),
                        Estimated_Value=(
                            "Estimated Line Total",
                            "sum",
                        ),
                    )
                    .reset_index()
                )

                publisher_summary.to_excel(
                    writer,
                    index=False,
                    sheet_name="Publisher Summary",
                )

                for sheet_name in writer.book.sheetnames:
                    ws = writer.book[sheet_name]
                    ws.freeze_panes = "A2"
                    ws.auto_filter.ref = ws.dimensions

                    for column_cells in ws.columns:
                        max_length = max(
                            (
                                len(str(cell.value))
                                if cell.value is not None
                                else 0
                            )
                            for cell in column_cells
                        )

                        ws.column_dimensions[
                            column_cells[0].column_letter
                        ].width = min(
                            max_length + 2,
                            50,
                        )

            master_buffer.seek(0)

            zip_file.writestr(
                "AcquiAI_Final_Purchase_Master.xlsx",
                master_buffer.getvalue(),
            )

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": (
                    'attachment; '
                    'filename="AcquiAI_Publisher_Orders.zip"'
                )
            },
        )

    finally:
        db.close()


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    db = SessionLocal()

    try:
        return {
            "status": "ok",
            "application": "AcquiAI",
            "version": "3.8.2",
            "page_size": PAGE_SIZE,
            "books": db.query(Book).count(),
            "submitted_carts": (
                db.query(SelectionCart).count()
            ),
            "selections": (
                db.query(SelectionItem).count()
            ),
            "approved": (
                db.query(SelectionItem)
                .filter(
                    SelectionItem.admin_status
                    == "Approved"
                )
                .count()
            ),
            "pending": (
                db.query(SelectionItem)
                .filter(
                    SelectionItem.admin_status
                    == "Pending"
                )
                .count()
            ),
        }

    finally:
        db.close()


# =========================================================
# RUN DIRECTLY
# =========================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "selection_portal:app",
        host="127.0.0.1",
        port=8002,
        reload=False,
    )
