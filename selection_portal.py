import os
import secrets

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import or_, func
from urllib.parse import urlencode
from dotenv import load_dotenv
from supabase import create_client
from database import SessionLocal
from models import Book, Selector, SelectionCart, SelectionItem

import io
import pandas as pd

load_dotenv()

app = FastAPI(
    title="AcquiAI",
    version="4.1.1",
)

SESSION_SECRET = os.environ.get("SESSION_SECRET", "acquiai-local-development-secret")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False,
)


PAGE_SIZE = 50



# =========================================================
# ACQUIAI v4.1 — SUPABASE AUTHENTICATION & ADMIN APPROVAL
# =========================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8002").rstrip("/")


def _supabase_public():
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_PUBLISHABLE_KEY in .env."
        )
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


def _supabase_admin():
    admin_key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY

    if not SUPABASE_URL or not admin_key:
        raise RuntimeError(
            "Supabase admin access is not configured. "
            "Set SUPABASE_SERVICE_ROLE_KEY in .env. Keep it server-side only."
        )

    return create_client(SUPABASE_URL, admin_key)


def lang_of(request: Request):
    lang = request.query_params.get("lang") or request.session.get("lang") or "en"
    lang = "ar" if lang == "ar" else "en"
    request.session["lang"] = lang
    return lang


def tr(lang, en, ar):
    return ar if lang == "ar" else en


def auth_user(request: Request):
    """Validate the Supabase session and return the matching profile."""
    access_token = request.session.get("sb_access_token")
    refresh_token = request.session.get("sb_refresh_token")

    if not access_token:
        return None

    try:
        client = _supabase_public()
        response = client.auth.get_user(access_token)
        sb_user = getattr(response, "user", None)

        if not sb_user:
            raise RuntimeError("No Supabase user")

    except Exception:
        if not refresh_token:
            request.session.clear()
            return None

        try:
            client = _supabase_public()
            refreshed = client.auth.refresh_session(refresh_token)
            session = getattr(refreshed, "session", None)

            if not session:
                request.session.clear()
                return None

            request.session["sb_access_token"] = session.access_token
            request.session["sb_refresh_token"] = session.refresh_token

            user_response = client.auth.get_user(session.access_token)
            sb_user = getattr(user_response, "user", None)

            if not sb_user:
                request.session.clear()
                return None

        except Exception:
            request.session.clear()
            return None

    try:
        admin = _supabase_admin()
        result = (
            admin.table("profiles")
            .select(
                "id,email,full_name,employee_student_id,"
                "department,role,approval_status"
            )
            .eq("id", str(sb_user.id))
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        return dict(rows[0])
    except Exception:
        return None


def require_approved_user(request: Request):
    user = auth_user(request)
    if not user:
        return None, RedirectResponse(
            f"/login?lang={lang_of(request)}",
            status_code=303,
        )
    if user.get("approval_status") != "approved":
        return user, RedirectResponse(
            f"/account-status?lang={lang_of(request)}",
            status_code=303,
        )
    return user, None


def require_admin(request: Request):
    user, redirect = require_approved_user(request)
    if redirect:
        return user, redirect
    if not user or user.get("role") != "admin":
        return user, RedirectResponse(
            f"/catalogue?lang={lang_of(request)}",
            status_code=303,
        )
    return user, None


def simple_page(title, content, lang="en", user=None):
    rtl = lang == "ar"
    direction = "rtl" if rtl else "ltr"
    other = "en" if rtl else "ar"
    switch = "English" if rtl else "العربية"
    home = tr(lang, "Home", "الرئيسية")
    login = tr(lang, "Sign In", "تسجيل الدخول")
    access = tr(lang, "Request Access", "طلب الوصول")
    logout_text = tr(lang, "Sign Out", "تسجيل الخروج")
    catalogue_text = tr(lang, "Selection Portal", "بوابة الاختيار")
    admin_text = tr(lang, "Admin Dashboard", "لوحة تحكم المسؤول")

    if user:
        nav = (
            f'<a href="/?lang={lang}">{home}</a>'
            f'<a href="/catalogue?lang={lang}">{catalogue_text}</a>'
        )
        if user.get("role") == "admin":
            nav += f'<a href="/admin?lang={lang}">{admin_text}</a>'
        nav += (
            f'<a href="/logout">{logout_text}</a>'
            f'<a href="?lang={other}">{switch}</a>'
        )
    else:
        nav = (
            f'<a href="/?lang={lang}">{home}</a>'
            f'<a href="/login?lang={lang}">{login}</a>'
            f'<a href="/register?lang={lang}">{access}</a>'
            f'<a href="?lang={other}">{switch}</a>'
        )

    return HTMLResponse(f"""<!doctype html>
<html lang="{lang}" dir="{direction}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | AcquiAI</title>
<style>
body{{margin:0;font-family:Segoe UI,Tahoma,Arial,sans-serif;background:#f3f8f6;color:#12332d}}
header{{background:linear-gradient(115deg,#042f2b,#0b6f61);color:white;padding:18px 6%;display:flex;justify-content:space-between;align-items:center;gap:14px}}
header b{{font-size:27px}} header a{{color:white;text-decoration:none;margin-inline-start:12px}}
main{{width:min(1050px,92%);margin:42px auto}} .hero{{background:linear-gradient(135deg,#063f39,#0b6f61);color:white;padding:44px;border-radius:28px}}
.card{{background:white;padding:28px;border-radius:22px;margin:20px auto;max-width:680px;box-shadow:0 12px 35px #0b6f6115}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:22px}} .grid .card{{margin:0}}
input{{width:100%;padding:12px;margin:6px 0 13px;border:1px solid #dce9e5;border-radius:11px;box-sizing:border-box;font-size:15px}}
button,.btn{{display:inline-block;padding:11px 17px;border:0;border-radius:11px;background:#0b6f61;color:white;font-weight:700;text-decoration:none;cursor:pointer}}
.gold{{background:#d7a429;color:#2c260f}} table{{width:100%;border-collapse:collapse;background:white}}
th,td{{padding:10px;border-bottom:1px solid #dce9e5;text-align:start}} .muted{{color:#6f827d}}
.notice{{padding:13px 15px;border-radius:12px;background:#fff8dd;border:1px solid #f0d88b;margin:14px 0}}
.error{{padding:13px 15px;border-radius:12px;background:#fdecec;border:1px solid #efb8b8;margin:14px 0}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}.hero{{padding:28px 20px}}header{{align-items:flex-start;flex-direction:column;gap:10px}}}}
</style></head><body>
<header><div><b>AcquiAI</b><div style="font-size:12px;opacity:.8">Designed & Developed by Yameen Abdullah</div></div>
<nav>{nav}</nav></header>
<main>{content}</main></body></html>""")


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    lang = lang_of(request)
    user = auth_user(request)
    open_text = tr(lang, "Open Selection Portal", "فتح بوابة الاختيار")
    sign = tr(lang, "Sign In", "تسجيل الدخول")
    req = tr(lang, "Request Access", "طلب الوصول")

    if user and user.get("approval_status") == "approved":
        button = f'<a class="btn gold" href="/catalogue?lang={lang}">{open_text}</a>'
    elif user:
        button = f'<a class="btn gold" href="/account-status?lang={lang}">{tr(lang,"View Account Status","عرض حالة الحساب")}</a>'
    else:
        button = (
            f'<a class="btn gold" href="/login?lang={lang}">{sign}</a> '
            f'<a class="btn" href="/register?lang={lang}">{req}</a>'
        )

    kicker = tr(lang, "AI-POWERED LIBRARY ACQUISITION", "منصة ذكية لاقتناء مصادر المكتبة")
    heading = tr(lang, "From publisher lists to smarter purchasing.", "من قوائم الناشرين إلى شراء أكثر ذكاءً.")
    desc = tr(
        lang,
        "A bilingual workflow for publisher files, master catalogue creation, authenticated user selection, administrative approval and publisher purchase orders.",
        "منصة ثنائية اللغة لمعالجة ملفات الناشرين، وإنشاء القائمة الموحدة، واختيار المستخدمين المعتمدين، والموافقة الإدارية، وإعداد أوامر الشراء للناشرين.",
    )
    steps = [
        (tr(lang,"01 • Upload","01 • الرفع"), tr(lang,"Combine publisher and vendor Excel lists.","دمج قوائم Excel الواردة من الناشرين والموردين.")),
        (tr(lang,"02 • Select","02 • الاختيار"), tr(lang,"Approved users search and select required titles.","يبحث المستخدمون المعتمدون عن العناوين ويختارونها.")),
        (tr(lang,"03 • Approve","03 • الاعتماد"), tr(lang,"Admin sees user and department demand for each title.","يرى المسؤول المستخدمين والأقسام التي طلبت كل عنوان.")),
        (tr(lang,"04 • Purchase","04 • الشراء"), tr(lang,"Generate final purchase and publisher order files.","إنشاء ملفات الشراء النهائية وأوامر الناشرين.")),
    ]
    cards = "".join(f'<div class="card"><b>{a}</b><p>{b}</p></div>' for a,b in steps)

    recovery_script = f"""
<script>
(function () {{
    const hash = window.location.hash || "";
    if (!hash) return;

    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const type = params.get("type");
    const accessToken = params.get("access_token");

    if (type === "recovery" && accessToken) {{
        window.location.replace("/reset-password?lang={lang}" + hash);
        return;
    }}

    if ((type === "signup" || type === "email_change") && accessToken) {{
        window.location.replace("/auth/callback?lang={lang}" + hash);
    }}
}})();
</script>
"""

    return simple_page(
        tr(lang,"Welcome","مرحباً"),
        f"""<section class="hero"><div style="color:#f0d36d;font-weight:800">{kicker}</div>
<h1 style="font-size:clamp(34px,6vw,60px)">{heading}</h1>
<p style="font-size:18px;line-height:1.7">{desc}</p><p>{button}</p></section>
<div class="grid">{cards}</div>
{recovery_script}""",
        lang,
        user=user,
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    lang = lang_of(request)
    return simple_page(
        tr(lang,"Request Access","طلب الوصول"),
        f"""<div class="card"><h1>{tr(lang,"Request Access","طلب الوصول")}</h1>
<p>{tr(lang,"Create your AcquiAI account. After email verification, access remains pending until approved by an administrator.","أنشئ حساب AcquiAI. بعد التحقق من البريد الإلكتروني يبقى الوصول قيد الانتظار حتى موافقة مسؤول النظام.")}</p>
<form method="post" action="/register?lang={lang}">
<label>{tr(lang,"Full Name","الاسم الكامل")}</label><input name="full_name" required>
<label>{tr(lang,"Student / Employee ID","الرقم الطلابي / الوظيفي")}</label><input name="employee_student_id" required>
<label>{tr(lang,"Department / Programme","القسم / البرنامج")}</label><input name="department" required>
<label>{tr(lang,"Email","البريد الإلكتروني")}</label><input type="email" name="email" required>
<label>{tr(lang,"Password","كلمة المرور")}</label><input type="password" name="password" minlength="8" required>
<label>{tr(lang,"Confirm Password","تأكيد كلمة المرور")}</label><input type="password" name="confirm_password" minlength="8" required>
<button type="submit">{tr(lang,"Create Account","إنشاء الحساب")}</button></form></div>""",
        lang,
    )


@app.post("/register")
async def register_submit(request: Request):
    lang = lang_of(request)
    f = await request.form()
    password = str(f.get("password",""))

    if password != str(f.get("confirm_password","")) or len(password) < 8:
        return simple_page(
            tr(lang,"Registration","التسجيل"),
            f'<div class="card"><h2>{tr(lang,"Password error","خطأ في كلمة المرور")}</h2>'
            f'<p>{tr(lang,"Passwords must match and contain at least 8 characters.","يجب أن تتطابق كلمتا المرور وأن تتكونا من 8 أحرف على الأقل.")}</p></div>',
            lang,
        )

    email = str(f.get("email","")).strip().lower()
    metadata = {
        "full_name": str(f.get("full_name","")).strip(),
        "employee_student_id": str(f.get("employee_student_id","")).strip(),
        "department": str(f.get("department","")).strip(),
    }

    try:
        client = _supabase_public()
        client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": metadata,
                    "email_redirect_to": f"{APP_BASE_URL}/auth/callback",
                },
            }
        )
    except Exception as error:
        return simple_page(
            tr(lang,"Registration","التسجيل"),
            f'<div class="card"><h2>{tr(lang,"Unable to create account","تعذر إنشاء الحساب")}</h2>'
            f'<div class="error">{esc(error)}</div></div>',
            lang,
        )

    return simple_page(
        tr(lang,"Check Your Email","تحقق من بريدك الإلكتروني"),
        f"""<div class="card">
<h2>{tr(lang,"Registration received","تم استلام التسجيل")}</h2>
<p>{tr(lang,"A verification email has been sent. Verify your email first, then sign in. Your AcquiAI access will remain pending until an administrator approves it.","تم إرسال رسالة تحقق إلى بريدك الإلكتروني. تحقق من البريد أولاً ثم سجّل الدخول. سيبقى وصولك إلى AcquiAI قيد الانتظار حتى موافقة المسؤول.")}</p>
<a class="btn" href="/login?lang={lang}">{tr(lang,"Go to Sign In","الانتقال إلى تسجيل الدخول")}</a>
</div>""",
        lang,
    )


@app.get("/auth/callback", response_class=HTMLResponse)
def auth_callback(request: Request):
    lang = lang_of(request)
    return simple_page(
        tr(lang,"Email Verified","تم التحقق من البريد"),
        f"""<div class="card">
<h2>{tr(lang,"Email verification completed","اكتمل التحقق من البريد الإلكتروني")}</h2>
<p>{tr(lang,"You can now sign in. If your account is still pending, AcquiAI will show your approval status.","يمكنك الآن تسجيل الدخول. إذا كان الحساب لا يزال قيد الانتظار فسيعرض AcquiAI حالة الموافقة.")}</p>
<a class="btn" href="/login?lang={lang}">{tr(lang,"Sign In","تسجيل الدخول")}</a>
</div>
<script>
(function () {{
    const hash = window.location.hash || "";
    if (!hash) return;
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    if (params.get("type") === "recovery" && params.get("access_token")) {{
        window.location.replace("/reset-password?lang={lang}" + hash);
    }}
}})();
</script>""",
        lang,
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    lang = lang_of(request)
    return simple_page(
        tr(lang,"Sign In","تسجيل الدخول"),
        f"""<div class="card"><h1>{tr(lang,"Sign In","تسجيل الدخول")}</h1>
<form method="post" action="/login?lang={lang}">
<label>{tr(lang,"Email","البريد الإلكتروني")}</label><input type="email" name="email" required>
<label>{tr(lang,"Password","كلمة المرور")}</label><input type="password" name="password" required>
<button type="submit">{tr(lang,"Sign In","تسجيل الدخول")}</button>
</form>
<p><a href="/forgot-password?lang={lang}">{tr(lang,"Forgot password?","هل نسيت كلمة المرور؟")}</a></p>
<p class="muted">{tr(lang,"New user?","مستخدم جديد؟")} <a href="/register?lang={lang}">{tr(lang,"Request Access","طلب الوصول")}</a></p>
</div>""",
        lang,
    )


@app.post("/login")
async def login_submit(request: Request):
    lang = lang_of(request)
    f = await request.form()
    email = str(f.get("email","")).strip().lower()
    password = str(f.get("password",""))

    try:
        client = _supabase_public()
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        session = getattr(response, "session", None)
        if not session:
            raise RuntimeError("No authenticated session was returned.")

        request.session["sb_access_token"] = session.access_token
        request.session["sb_refresh_token"] = session.refresh_token

    except Exception:
        return simple_page(
            tr(lang,"Sign In","تسجيل الدخول"),
            f'<div class="card"><h2>{tr(lang,"Unable to sign in","تعذر تسجيل الدخول")}</h2>'
            f'<p>{tr(lang,"Check your email and password and make sure your email has been verified.","تحقق من البريد الإلكتروني وكلمة المرور وتأكد من التحقق من بريدك الإلكتروني.")}</p>'
            f'<a class="btn" href="/login?lang={lang}">{tr(lang,"Try Again","حاول مرة أخرى")}</a></div>',
            lang,
        )

    user = auth_user(request)
    if not user:
        request.session.clear()
        return simple_page(
            tr(lang,"Profile Error","خطأ في الملف الشخصي"),
            f'<div class="card"><h2>{tr(lang,"Your account profile could not be loaded.","تعذر تحميل ملف حسابك.")}</h2>'
            f'<p>{tr(lang,"Ask the AcquiAI administrator to verify the Supabase profiles table.","يرجى من مسؤول AcquiAI التحقق من جدول profiles في Supabase.")}</p></div>',
            lang,
        )

    if user.get("approval_status") != "approved":
        return RedirectResponse(f"/account-status?lang={lang}", status_code=303)

    if user.get("role") == "admin":
        return RedirectResponse(f"/admin?lang={lang}", status_code=303)

    return RedirectResponse(f"/catalogue?lang={lang}", status_code=303)


@app.get("/account-status", response_class=HTMLResponse)
def account_status(request: Request):
    lang = lang_of(request)
    user = auth_user(request)
    if not user:
        return RedirectResponse(f"/login?lang={lang}", status_code=303)

    labels = {
        "pending": tr(lang,"Pending Approval","قيد الموافقة"),
        "approved": tr(lang,"Approved","معتمد"),
        "rejected": tr(lang,"Rejected","مرفوض"),
    }
    status = labels.get(user.get("approval_status"), user.get("approval_status",""))

    return simple_page(
        tr(lang,"Account Status","حالة الحساب"),
        f"""<div class="card">
<h1>{tr(lang,"Account Status","حالة الحساب")}</h1>
<h2>{status}</h2>
<p><strong>{esc(user.get("full_name",""))}</strong></p>
<p>{esc(user.get("department",""))}</p>
<p>{tr(lang,"Email verification and administrator approval are separate. Only approved accounts can open the book-selection catalogue.","التحقق من البريد الإلكتروني وموافقة المسؤول مرحلتان منفصلتان. لا يمكن فتح فهرس اختيار الكتب إلا للحسابات المعتمدة.")}</p>
<a class="btn" href="/logout">{tr(lang,"Sign Out","تسجيل الخروج")}</a>
</div>""",
        lang,
        user=user,
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    lang = lang_of(request)
    return simple_page(
        tr(lang,"Forgot Password","نسيت كلمة المرور"),
        f"""<div class="card">
<h1>{tr(lang,"Forgot Password","نسيت كلمة المرور")}</h1>
<p>{tr(lang,"Enter the email address linked to your AcquiAI account.","أدخل البريد الإلكتروني المرتبط بحساب AcquiAI.")}</p>
<form method="post" action="/forgot-password?lang={lang}">
<label>{tr(lang,"Email","البريد الإلكتروني")}</label>
<input type="email" name="email" required>
<button type="submit">{tr(lang,"Send Reset Link","إرسال رابط إعادة التعيين")}</button>
</form></div>""",
        lang,
    )


@app.post("/forgot-password")
async def forgot_password_submit(request: Request):
    lang = lang_of(request)
    f = await request.form()
    email = str(f.get("email","")).strip().lower()

    try:
        client = _supabase_public()
        client.auth.reset_password_for_email(
            email,
            {"redirect_to": f"{APP_BASE_URL}/reset-password"},
        )
    except Exception:
        pass

    return simple_page(
        tr(lang,"Reset Email Sent","تم إرسال رسالة إعادة التعيين"),
        f"""<div class="card">
<h2>{tr(lang,"Check your email","تحقق من بريدك الإلكتروني")}</h2>
<p>{tr(lang,"If an account exists for that email, Supabase has sent a password reset link.","إذا كان هناك حساب بهذا البريد الإلكتروني فسيرسل Supabase رابط إعادة تعيين كلمة المرور.")}</p>
<a class="btn" href="/login?lang={lang}">{tr(lang,"Back to Sign In","العودة إلى تسجيل الدخول")}</a>
</div>""",
        lang,
    )


@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    lang = lang_of(request)
    direction = "rtl" if lang == "ar" else "ltr"
    title = tr(lang, "Reset Password", "إعادة تعيين كلمة المرور")
    new_password = tr(lang, "New Password", "كلمة المرور الجديدة")
    confirm_password = tr(lang, "Confirm Password", "تأكيد كلمة المرور")
    save_password = tr(lang, "Save New Password", "حفظ كلمة المرور الجديدة")
    mismatch = tr(lang, "Passwords must match and contain at least 8 characters.", "يجب أن تتطابق كلمتا المرور وأن تتكونا من 8 أحرف على الأقل.")
    success = tr(lang, "Password updated successfully. You can now sign in.", "تم تحديث كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول.")
    invalid = tr(lang, "The recovery link is invalid or has expired. Request a new reset link.", "رابط الاسترداد غير صالح أو منتهي الصلاحية. اطلب رابطاً جديداً.")
    signin = tr(lang, "Sign In", "تسجيل الدخول")

    return HTMLResponse(f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | AcquiAI</title>
<style>
body{{margin:0;font-family:Segoe UI,Tahoma,Arial,sans-serif;background:#f3f8f6;color:#12332d}}
main{{width:min(680px,92%);margin:70px auto}}
.card{{background:white;padding:30px;border-radius:22px;box-shadow:0 12px 35px #0b6f6115}}
input{{width:100%;padding:12px;margin:7px 0 14px;border:1px solid #dce9e5;border-radius:11px;box-sizing:border-box}}
button,.btn{{display:inline-block;padding:11px 17px;border:0;border-radius:11px;background:#0b6f61;color:white;font-weight:700;text-decoration:none;cursor:pointer}}
.msg{{margin:14px 0;padding:12px;border-radius:10px;background:#f3f8f6}}
</style></head>
<body><main><div class="card">
<h1>{title}</h1>
<div id="message" class="msg">{tr(lang,"Enter a new password below.","أدخل كلمة مرور جديدة أدناه.")}</div>
<form id="resetForm">
<label>{new_password}</label><input id="password" type="password" minlength="8" required>
<label>{confirm_password}</label><input id="confirm" type="password" minlength="8" required>
<button type="submit">{save_password}</button>
</form>
<p><a class="btn" href="/login?lang={lang}">{signin}</a></p>
</div></main>
<script>
const SUPABASE_URL = {SUPABASE_URL!r};
const SUPABASE_KEY = {SUPABASE_PUBLISHABLE_KEY!r};
const message = document.getElementById("message");
const form = document.getElementById("resetForm");
const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
const accessToken = params.get("access_token");

if (!accessToken) {{
    message.textContent = {invalid!r};
}}

form.addEventListener("submit", async (event) => {{
    event.preventDefault();
    const p1 = document.getElementById("password").value;
    const p2 = document.getElementById("confirm").value;

    if (p1.length < 8 || p1 !== p2) {{
        message.textContent = {mismatch!r};
        return;
    }}
    if (!accessToken) {{
        message.textContent = {invalid!r};
        return;
    }}

    try {{
        const response = await fetch(SUPABASE_URL + "/auth/v1/user", {{
            method: "PUT",
            headers: {{
                "apikey": SUPABASE_KEY,
                "Authorization": "Bearer " + accessToken,
                "Content-Type": "application/json"
            }},
            body: JSON.stringify({{password: p1}})
        }});
        if (!response.ok) throw new Error("Reset failed");
        message.textContent = {success!r};
        form.style.display = "none";
        history.replaceState(null, "", "/reset-password?lang={lang}");
    }} catch (error) {{
        message.textContent = {invalid!r};
    }}
}});
</script></body></html>""")


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    lang = lang_of(request)
    admin_user, redirect = require_admin(request)
    if redirect:
        return redirect

    try:
        admin = _supabase_admin()
        result = (
            admin.table("profiles")
            .select(
                "id,full_name,employee_student_id,department,"
                "email,role,approval_status,created_at"
            )
            .order("created_at", desc=True)
            .execute()
        )
        rows = result.data or []
    except Exception as error:
        return simple_page(
            tr(lang,"User Management","إدارة المستخدمين"),
            f'<div class="card"><h2>{tr(lang,"Unable to load users","تعذر تحميل المستخدمين")}</h2>'
            f'<div class="error">{esc(error)}</div></div>',
            lang,
            user=admin_user,
        )

    def status_label(value):
        return {
            "pending": tr(lang,"Pending","قيد الانتظار"),
            "approved": tr(lang,"Approved","معتمد"),
            "rejected": tr(lang,"Rejected","مرفوض"),
        }.get(value, value)

    trs = ""
    for r in rows:
        is_admin = r.get("role") == "admin"
        action = "—"
        if not is_admin:
            action = f"""<form method="post" action="/admin/users/{r.get('id')}/status?lang={lang}">
<button name="status" value="approved">{tr(lang,"Approve","اعتماد")}</button>
<button name="status" value="rejected">{tr(lang,"Reject","رفض")}</button>
<button name="status" value="pending">{tr(lang,"Pending","قيد الانتظار")}</button>
</form>"""
        trs += (
            f"<tr><td>{esc(r.get('full_name'))}</td>"
            f"<td>{esc(r.get('employee_student_id'))}</td>"
            f"<td>{esc(r.get('department'))}</td>"
            f"<td>{esc(r.get('email'))}</td>"
            f"<td>{esc(r.get('role'))}</td>"
            f"<td>{esc(status_label(r.get('approval_status')))}</td>"
            f"<td>{action}</td></tr>"
        )

    return simple_page(
        tr(lang,"User Management","إدارة المستخدمين"),
        f"""<div class="card" style="max-width:none">
<h1>{tr(lang,"User Management","إدارة المستخدمين")}</h1>
<p><a href="/admin?lang={lang}">{tr(lang,"Admin Dashboard","لوحة تحكم المسؤول")}</a></p>
<div style="overflow:auto"><table>
<tr><th>{tr(lang,"Name","الاسم")}</th><th>{tr(lang,"ID","الرقم")}</th>
<th>{tr(lang,"Department","القسم")}</th><th>{tr(lang,"Email","البريد الإلكتروني")}</th>
<th>{tr(lang,"Role","الدور")}</th><th>{tr(lang,"Status","الحالة")}</th><th>{tr(lang,"Action","الإجراء")}</th></tr>
{trs}</table></div></div>""",
        lang,
        user=admin_user,
    )


@app.post("/admin/users/{uid}/status")
async def admin_user_update(uid: str, request: Request):
    lang = lang_of(request)
    admin_user, redirect = require_admin(request)
    if redirect:
        return redirect

    f = await request.form()
    status = str(f.get("status",""))
    if status not in {"approved","rejected","pending"}:
        status = "pending"

    try:
        admin = _supabase_admin()
        existing = (
            admin.table("profiles")
            .select("id,role")
            .eq("id", uid)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows and rows[0].get("role") != "admin":
            (
                admin.table("profiles")
                .update({"approval_status": status})
                .eq("id", uid)
                .execute()
            )
    except Exception:
        pass

    return RedirectResponse(f"/admin/users?lang={lang}", status_code=303)


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
        "requested_by": "Requested By",
        "total_requests": "Total Requests",
        "admin_decision": "Admin Decision / Final Qty",
        "approve": "Approve",
        "reject": "Reject",
        "reset": "Reset",
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
        "requested_by": "عدد الطالبين",
        "total_requests": "إجمالي الطلبات",
        "admin_decision": "قرار المسؤول / الكمية النهائية",
        "approve": "اعتماد",
        "reject": "رفض",
        "reset": "إعادة",
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

    portal_url = build_url("/catalogue", lang)
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
    --brand: #07594b;
    --brand-dark: #033b32;
    --brand-soft: #e8f5f1;
    --gold: #d9a62e;
    --text: #17302b;
    --muted: #6c7c78;
    --border: #d9e5e1;
    --bg: #f5f8f7;
    --danger: #b84c4c;
    --success: #2f8a62;
    --shadow: 0 10px 30px rgba(16, 59, 50, .08);
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: "Segoe UI", Tahoma, Arial, sans-serif;
    background:
        radial-gradient(circle at top right, rgba(7,89,75,.08), transparent 30%),
        var(--bg);
    color: var(--text);
    text-align: {align};
}}

header {{
    background:
        linear-gradient(120deg, var(--brand-dark), var(--brand));
    color: white;
    padding: 22px 34px;
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
    width: 48px;
    height: 48px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    background: rgba(255,255,255,.14);
    border: 1px solid rgba(255,255,255,.2);
    font-size: 23px;
    font-weight: 900;
}}

.brand {{
    font-size: 30px;
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
    background: rgba(255,255,255,.11);
    padding: 10px 14px;
    border-radius: 10px;
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
    background: var(--gold);
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
        linear-gradient(135deg, rgba(7,89,75,.98), rgba(11,126,102,.92));
    color: white;
    border-radius: 22px;
    padding: 28px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
}}

.hero h1 {{
    margin: 0 0 8px;
    font-size: 30px;
}}

.hero p {{
    margin: 0;
    opacity: .9;
    max-width: 900px;
    line-height: 1.7;
}}

.card {{
    background: rgba(255,255,255,.96);
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
    border: 1px solid rgba(217,229,225,.75);
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
    border-radius: 10px;
    display: grid;
    place-items: center;
    background: var(--brand-soft);
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
    border-radius: 11px;
    font-size: 14px;
    background: white;
    color: var(--text);
    outline: none;
}}

input:focus,
select:focus,
textarea:focus {{
    border-color: #57a893;
    box-shadow: 0 0 0 3px rgba(7,89,75,.08);
}}

button {{
    border: none;
    border-radius: 11px;
    padding: 11px 18px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 800;
    transition: .18s ease;
}}

button:hover {{
    transform: translateY(-1px);
}}

.primary {{
    background: var(--brand);
    color: white;
}}

.secondary {{
    background: var(--brand-soft);
    color: var(--brand-dark);
}}

.warning {{
    background: var(--gold);
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
    background: white;
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: var(--shadow);
    border: 1px solid rgba(217,229,225,.75);
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
    background: var(--brand-dark);
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
    background: #f7fbfa;
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
    background: rgba(255,255,255,.96);
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

.toolbar {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 16px;
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
    </div>
</div>

<div class="nav">
    <a href="{portal_url}" class="nav-link">{esc(t["portal"])}</a>
    {f'<a href="{admin_url}" class="nav-link">{esc(t["admin"])}</a>' if admin else ""}
    <a href="/logout" class="nav-link">{esc("تسجيل الخروج" if lang == "ar" else "Sign Out")}</a>
    <a href="{switch_url}" class="nav-link lang-link">{esc(t["language_button"])}</a>
    {admin_badge}
</div>

</div>
</header>

<div class="container">
{content}
</div>
</body>
</html>
"""


# =========================================================
# USER SELECTION PORTAL
# =========================================================

@app.get("/catalogue", response_class=HTMLResponse)
def selection_page(
    request: Request,
    q: str = "",
    publisher: str = "",
    language: str = "",
    subject: str = "",
    page: int = 1,
    lang: str = "en",
):
    lang, t = lang_pack(lang)
    current_user, redirect = require_approved_user(request)
    if redirect:
        return redirect

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
    value="{esc(current_user.get("full_name",""))}"
    placeholder="{esc(t["full_name"])}"
    readonly
>

<input
    type="text"
    name="user_id"
    value="{esc(current_user.get("employee_student_id",""))}"
    placeholder="{esc(t["user_id"])}"
    readonly
>

<input
    type="text"
    name="department"
    value="{esc(current_user.get("department",""))}"
    placeholder="{esc(t["department"])}"
    readonly
>

<input
    type="email"
    name="email"
    value="{esc(current_user.get("email",""))}"
    placeholder="{esc(t["email"])}"
    readonly
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
    current_user, redirect = require_approved_user(request)
    if redirect:
        return redirect

    full_name = str(current_user.get("full_name","")).strip()
    user_id = str(current_user.get("employee_student_id","")).strip()
    department = str(current_user.get("department","")).strip()
    email = str(current_user.get("email","")).strip()
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
    request: Request,
    lang: str = "en",
):
    lang, t = lang_pack(lang)
    admin_user, redirect = require_admin(request)
    if redirect:
        return redirect

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
<td colspan="8">{esc(t["no_demand"])}</td>
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

        content = f"""
<div class="hero">
<h1>{esc(t["admin_title"])}</h1>
<p>{esc(t["admin_subtitle"])}</p>
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

<a href="{export_url}">
<button class="primary">
{esc(t["export_final"])}
</button>
</a>

</div>

<div class="table-wrap">
<table>

<thead>
<tr>
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
# ADMIN DECISION
# =========================================================

@app.post("/admin/book/{book_id}/decision")
async def admin_book_decision(
    book_id: int,
    request: Request,
):
    admin_user, redirect = require_admin(request)
    if redirect:
        return redirect

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
    request: Request,
    lang: str = "en",
):
    lang, t = lang_pack(lang)
    admin_user, redirect = require_admin(request)
    if redirect:
        return redirect

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
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    db = SessionLocal()

    try:
        return {
            "status": "ok",
            "application": "AcquiAI",
            "version": "4.1.1",
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
