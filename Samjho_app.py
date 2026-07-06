# ==========================================================================
#  Samjho — Pehle Samjho, Phir Sign Karo
#  A Streamlit app implementing document intake, AI-style explanation,
#  smart form fill, tiered warnings, review & post-submission support.
# ==========================================================================

import io
import re
import json
import math
import zipfile
import random
import traceback
from audio_recorder_streamlit import audio_recorder
from xml.etree import ElementTree
from datetime import datetime, timedelta

import streamlit as st

# ---------------------------------------------------------------------
# OPTIONAL DEPENDENCIES  (app degrades gracefully if any are missing)
# ---------------------------------------------------------------------
try:
    import pdfplumber
    HAVE_PDFPLUMBER = True
except Exception:
    HAVE_PDFPLUMBER = False

try:
    from pypdf import PdfReader
    HAVE_PYPDF = True
except Exception:
    HAVE_PYPDF = False

try:
    from docx import Document as DocxDocument
    HAVE_DOCX_LIB = True
except Exception:
    HAVE_DOCX_LIB = False

try:
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

try:
    import pytesseract
    HAVE_TESSERACT = True
except Exception:
    HAVE_TESSERACT = False

try:
    from pdf2image import convert_from_bytes
    HAVE_PDF2IMAGE = True
except Exception:
    HAVE_PDF2IMAGE = False

try:
    from deep_translator import GoogleTranslator
    HAVE_TRANSLATOR = True
except Exception:
    HAVE_TRANSLATOR = False

try:
    from gtts import gTTS
    HAVE_TTS = True
except Exception:
    HAVE_TTS = False

try:
    from fpdf import FPDF
    HAVE_FPDF = True
except Exception:
    HAVE_FPDF = False

try:
    import pandas as pd
    HAVE_PANDAS = True
except Exception:
    HAVE_PANDAS = False

try:
    from openai import OpenAI
    HAVE_OPENAI = True
except Exception:
    HAVE_OPENAI = False

try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
    HAVE_MIC = True
except Exception:
    HAVE_MIC = False
    
try:
    import speech_recognition as sr
    HAVE_SR = True
except Exception:
    HAVE_SR = False


# ==========================================================================
# APP IDENTITY
# ==========================================================================
APP_NAME = "Samjho"
APP_TAGLINE = "Pehle Samjho, Phir Sign Karo"
APP_KICKER = "OFFICIAL DOCUMENT INTELLIGENCE"

# ==========================================================================
# PAGE CONFIG
# ==========================================================================
st.set_page_config(
    page_title=f"{APP_NAME} — {APP_TAGLINE}",
    page_icon="🪶",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================================
# LOGO — Hand-built "Wax Seal / Official Stamp" SVG monogram
#   IMPORTANT: built as a SINGLE-LINE string (no embedded newlines) to avoid
#   a Streamlit/Markdown quirk where indented multi-line HTML/SVG can get
#   misinterpreted as a literal code block instead of rendered HTML.
# ==========================================================================
def get_seal_logo_svg(size=80, grad_id="seal"):
    ticks = []
    n_ticks = 30
    r_outer, r_inner = 47, 43
    for i in range(n_ticks):
        angle = (2 * math.pi / n_ticks) * i
        x1 = 50 + r_outer * math.cos(angle)
        y1 = 50 + r_outer * math.sin(angle)
        x2 = 50 + r_inner * math.cos(angle)
        y2 = 50 + r_inner * math.sin(angle)
        ticks.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="url(#{grad_id})" stroke-width="1.4" stroke-linecap="round"/>'
        )
    ticks_svg = "".join(ticks)

    parts = [
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">',
        '<defs>',
        f'<linearGradient id="{grad_id}" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">',
        '<stop offset="0%" stop-color="#fdeeb0"/>',
        '<stop offset="45%" stop-color="#e8b74b"/>',
        '<stop offset="100%" stop-color="#9c6b1f"/>',
        '</linearGradient>',
        f'<radialGradient id="{grad_id}bg" cx="50%" cy="45%" r="65%">',
        '<stop offset="0%" stop-color="#1c1f2b"/>',
        '<stop offset="100%" stop-color="#0d0f16"/>',
        '</radialGradient>',
        '</defs>',
        ticks_svg,
        f'<circle cx="50" cy="50" r="40" fill="url(#{grad_id}bg)" stroke="url(#{grad_id})" stroke-width="2.2"/>',
        f'<circle cx="50" cy="50" r="34" fill="none" stroke="url(#{grad_id})" stroke-width="0.8" stroke-dasharray="1.5 3.2"/>',
        f'<text x="50" y="63" font-family="Georgia, serif" font-size="34" font-weight="700" '
        f'fill="url(#{grad_id})" text-anchor="middle">S</text>',
        f'<path d="M32 66 Q50 76 68 66" stroke="url(#{grad_id})" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
        '</svg>',
    ]
    return "".join(parts)


# ==========================================================================
# THEME / CSS  — "Official Legal Seal" design language
# ==========================================================================
def inject_css(font_scale=1.0, high_contrast=False, dyslexia_font=False):
    title_font = "'OpenDyslexic', Georgia, serif" if dyslexia_font else "'Playfair Display', Georgia, serif"
    body_font = "'OpenDyslexic', Verdana, sans-serif" if dyslexia_font else "'Manrope','Inter',sans-serif"
    bg = "#000000" if high_contrast else "#0b0c10"
    text_color = "#ffff00" if high_contrast else "#eae6da"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800;900&family=Manrope:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: {body_font} !important;
        font-size: {font_scale}rem;
        color: {text_color};
    }}

    .stApp {{
        background:
          radial-gradient(circle at 20% 0%, rgba(232,183,75,0.06) 0%, transparent 45%),
          radial-gradient(circle at 85% 90%, rgba(15,118,110,0.10) 0%, transparent 50%),
          {bg};
    }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg,#111319 0%, #0b0c10 100%);
        border-right: 1px solid rgba(232,183,75,0.18);
    }}

    /* ---------------- Keyframes ---------------- */
    @keyframes sealFloat {{
        0%,100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(-6px); }}
    }}
    @keyframes goldGlow {{
        0%,100% {{ filter: drop-shadow(0 0 4px rgba(232,183,75,0.35)); }}
        50% {{ filter: drop-shadow(0 0 18px rgba(232,183,75,0.8)); }}
    }}
    @keyframes pillPulse {{
        0%,100% {{ box-shadow: 0 4px 16px rgba(45,212,191,0.4); }}
        50% {{ box-shadow: 0 4px 26px rgba(45,212,191,0.75); }}
    }}

    /* ---------------- HERO HEADER (Home page) ---------------- */
    .ll-header {{
        position: relative;
        padding: 44px 46px 40px 46px;
        border-radius: 6px;
        background:
          linear-gradient(180deg, rgba(232,183,75,0.05), transparent 30%),
          repeating-linear-gradient(0deg, rgba(255,255,255,0.012) 0px, rgba(255,255,255,0.012) 1px, transparent 1px, transparent 3px),
          #14161d;
        border: 1px solid rgba(232,183,75,0.35);
        box-shadow: 0 25px 60px rgba(0,0,0,0.55), inset 0 0 60px rgba(232,183,75,0.03);
        margin-bottom: 30px;
    }}
    .ll-header::before {{
        content:'';
        position:absolute; inset:8px;
        border: 1px solid rgba(232,183,75,0.18);
        border-radius: 3px;
        pointer-events:none;
    }}
    .header-content {{ position:relative; z-index:1; display:flex; align-items:center; gap:32px; flex-wrap:wrap; }}
    .logo-mark {{ flex-shrink:0; animation: sealFloat 4.5s ease-in-out infinite; }}
    .logo-mark svg {{ animation: goldGlow 3.4s ease-in-out infinite; }}

    .kicker {{
        display:inline-flex; align-items:center; gap:8px;
        font-family: 'Manrope', sans-serif;
        font-size: 0.68rem; font-weight:800; letter-spacing:3px; text-transform:uppercase;
        color:#e8b74b;
        border-top: 1px solid rgba(232,183,75,0.5);
        border-bottom: 1px solid rgba(232,183,75,0.5);
        padding: 5px 0; margin-bottom:16px;
    }}
    .kicker::before {{ content:'◆'; font-size:0.55rem; }}

    .brand-title {{
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 4rem; font-weight:800; margin:0; letter-spacing:-1px; line-height:1;
        color: #f3e9c9;
        text-shadow:
          0 1px 0 #b98c2f,
          0 2px 3px rgba(0,0,0,0.6),
          0 0 26px rgba(232,183,75,0.25);
    }}
    .brand-title .accent-dot {{ color:#0f766e; }}

    .brand-tagline {{
        display:inline-flex; align-items:center; gap:10px; margin-top:16px;
        font-family: 'Playfair Display', Georgia, serif;
        font-style: italic; font-weight:600; font-size:1.25rem;
        color:#9fd8c9;
        padding: 4px 18px;
        border-left: 3px solid #0f766e;
        border-right: 3px solid #0f766e;
    }}
    .brand-sub {{
        margin-top:18px; color:#b7b0a0; font-size:1rem; max-width:660px; line-height:1.6;
        font-family:'Manrope',sans-serif;
    }}

    /* ---------------- Compact page headers (Phase pages) ---------------- */
    .ll-header-sm {{
        position:relative;
        padding: 20px 30px;
        border-radius: 5px;
        background: #14161d;
        border: 1px solid rgba(232,183,75,0.3);
        border-left: 5px solid #e8b74b;
        box-shadow: 0 10px 30px rgba(0,0,0,0.45);
        margin-bottom: 24px;
    }}
    .header-content-sm {{ display:flex; align-items:center; gap:16px; }}
    .header-content-sm svg {{ animation: goldGlow 3.4s ease-in-out infinite; flex-shrink:0; }}
    .page-title {{
        font-family: 'Playfair Display', Georgia, serif;
        font-size:1.65rem; font-weight:700; margin:0; letter-spacing:-0.3px;
        color:#f3e9c9;
    }}

    /* ---------------- NEW: Sidebar Brand Highlight Box ---------------- */
    .sidebar-brand-box {{
        text-align:center;
        padding: 28px 14px 24px 14px;
        margin-bottom: 18px;
        border-radius: 16px;
        background: radial-gradient(circle at 50% 10%, rgba(232,183,75,0.20), transparent 65%), #14161d;
        border: 1px solid rgba(232,183,75,0.45);
        box-shadow: 0 12px 34px rgba(0,0,0,0.55), inset 0 0 40px rgba(232,183,75,0.06);
    }}
    .sidebar-brand-box svg {{
        animation: goldGlow 3.2s ease-in-out infinite, sealFloat 4.5s ease-in-out infinite;
    }}
    .sidebar-brand-title-big {{
        display:block;
        font-family:'Playfair Display', Georgia, serif;
        font-size: 2.1rem;
        font-weight:800;
        margin: 16px 0 10px 0;
        letter-spacing:-0.5px;
        background: linear-gradient(180deg, #fdeeb0 10%, #e8b74b 55%, #b98c2f 100%);
        -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
        filter: drop-shadow(0 2px 10px rgba(232,183,75,0.45));
    }}
    .sidebar-tagline-highlight {{
        display:inline-block;
        font-family:'Playfair Display', Georgia, serif;
        font-style:italic; font-weight:700; font-size:0.86rem;
        color:#052e2b;
        background: linear-gradient(90deg,#5eead4,#2dd4bf);
        padding: 6px 18px;
        border-radius: 999px;
        animation: pillPulse 2.4s ease-in-out infinite;
    }}
    .sidebar-rule {{
        height:1px; margin: 14px 0 16px 0;
        background: linear-gradient(90deg, transparent, rgba(232,183,75,0.6), transparent);
    }}

    /* ---------------- Shared components ---------------- */
    .ll-card {{
        background: #14161d;
        border: 1px solid rgba(232,183,75,0.16);
        border-left: 3px solid rgba(232,183,75,0.55);
        border-radius: 8px;
        padding: 22px 24px;
        margin-bottom: 16px;
        transition: 0.25s;
    }}
    .ll-card:hover {{ border-left-color:#0f766e; transform: translateX(2px); }}
    .ll-card h3 {{ font-family:'Playfair Display',serif; color:#f3e9c9; }}

    .badge {{
        display:inline-block; padding:4px 13px; border-radius:3px;
        font-size:0.75rem; font-weight:700; margin-right:6px; margin-bottom:6px;
        font-family:'Manrope',sans-serif; letter-spacing:0.3px;
    }}
    .badge-critical {{ background:#2a0d0d; color:#ff8a8a; border:1px solid #7f1d1d;}}
    .badge-caution  {{ background:#2a2109; color:#f4c95d; border:1px solid #92700f;}}
    .badge-info     {{ background:#0b241d; color:#5eead4; border:1px solid #0f766e;}}

    .risk-box {{
        border-radius: 6px; padding: 16px 20px; margin-bottom: 12px;
        border-left: 4px solid; background: #14161d;
    }}
    .risk-critical {{ border-color:#e05252; box-shadow: inset 0 0 25px rgba(224,82,82,0.06); }}
    .risk-caution  {{ border-color:#e8b74b; box-shadow: inset 0 0 25px rgba(232,183,75,0.06); }}
    .risk-info     {{ border-color:#2dd4bf; box-shadow: inset 0 0 25px rgba(45,212,191,0.06); }}

    .metric-pill {{
        display:inline-block; background:#181a22; padding:10px 20px;
        border-radius:5px; margin-right:10px; border:1px solid rgba(232,183,75,0.28);
        font-family:'Manrope',sans-serif;
    }}

    .stButton>button {{
        border-radius: 4px; font-weight:700; font-family:'Manrope',sans-serif;
        border:1px solid #b98c2f;
        background: linear-gradient(180deg,#e8b74b,#b98c2f); color:#1a1305;
        letter-spacing:0.3px;
    }}
    .stButton>button:hover {{ background: linear-gradient(180deg,#fdeeb0,#e8b74b); border-color:#fdeeb0; }}

    hr {{ border-color: rgba(232,183,75,0.18); }}
    </style>
    """, unsafe_allow_html=True)


def page_header(title):
    """Compact stamped-ledger style header — built as ONE-LINE HTML to avoid
    Streamlit markdown indentation quirks that render raw code instead of HTML."""
    html = (
        '<div class="ll-header-sm"><div class="header-content-sm">'
        f'{get_seal_logo_svg(48, grad_id="pg")}'
        f'<h1 class="page-title">{title}</h1>'
        '</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ==========================================================================
# KNOWLEDGE BASES
# ==========================================================================

def kw_present(keyword, text_l):
    pattern = r'(?<!\w)' + re.escape(keyword.lower()) + r'(?!\w)'
    return re.search(pattern, text_l) is not None

def kw_count(keyword, text_l, cap=5):
    pattern = r'(?<!\w)' + re.escape(keyword.lower()) + r'(?!\w)'
    n = len(re.findall(pattern, text_l))
    return min(n, cap)

def kw_weight(keyword):
    return max(1, len(keyword.split()))

DOC_TYPES = {
    "Employment Contract": [
        "employment agreement", "appointment letter", "designation", "probation period",
        "notice period", "ctc", "date of joining", "employee shall", "employer shall",
        "resignation", "termination of employment"
    ],
    "Loan Agreement": [
        "loan agreement", "borrower", "lender", "principal amount", "emi",
        "rate of interest", "repayment schedule", "event of default", "hypothecation",
        "loan tenure", "disbursement"
    ],
    "Rental / Lease Agreement": [
        "lease agreement", "landlord", "tenant", "lessee", "lessor", "monthly rent",
        "security deposit", "leased premises", "rental agreement"
    ],
    "Non-Disclosure Agreement (NDA)": [
        "non-disclosure agreement", "confidential information", "disclosing party",
        "receiving party", "non-disclosure", "trade secrets"
    ],
    "Privacy Policy": [
        "privacy policy", "personal data", "data controller", "data protection",
        "we collect", "cookies", "gdpr", "opt-out", "information we collect",
        "third-party services", "data subject"
    ],
    "Terms & Conditions": [
        "terms and conditions", "user agrees", "acceptable use", "these terms",
        "governing terms", "terms of service", "you agree to"
    ],
    "Government Form": [
        "government of india", "ministry of", "form no", "i hereby declare",
        "aadhaar number", "pan card", "for official use only"
    ],
    "Insurance Policy": [
        "policyholder", "sum assured", "premium payment", "insurer", "nominee",
        "policy period", "claim settlement", "insured event", "policy schedule"
    ],
    "Sale / Purchase Agreement": [
        "sale agreement", "vendor", "purchaser", "sale consideration", "sale deed",
        "possession of the property", "title deed"
    ],
}

INDIAN_STATES = ["andhra pradesh","arunachal pradesh","assam","bihar","chhattisgarh","goa",
    "gujarat","haryana","himachal pradesh","jharkhand","karnataka","kerala","madhya pradesh",
    "maharashtra","manipur","meghalaya","mizoram","nagaland","odisha","punjab","rajasthan",
    "sikkim","tamil nadu","telangana","tripura","uttar pradesh","uttarakhand","west bengal",
    "delhi","chandigarh","puducherry","jammu and kashmir","ladakh"]

FOREIGN_HINTS = ["singapore","united kingdom","london","dubai","uae","hong kong",
                  "new york","california","delaware","united states of america","cayman"]

EXPLAIN_DB = [
    dict(name="Personal Guarantee", tier="critical", icon="🔴",
         keywords=["personal guarantee", "guarantor shall"],
         explain="You (or a guarantor) are personally promising to repay/fulfil this obligation even if the company/borrower fails. Personal assets can be seized.",
         example="If the business defaults, creditors can pursue the guarantor's personal savings, property or salary — not just business assets."),
    dict(name="Collateral / Security Pledge", tier="critical", icon="🔴",
         keywords=["collateral", "hypothecation", "mortgage of", "pledge of"],
         explain="You are putting up an asset (property, vehicle, deposits) as security. If you default, the lender has a legal right to seize/sell it.",
         example="Missing repeated EMIs on a vehicle loan with hypothecation can lead to repossession without a full court process."),
    dict(name="Indemnity Obligation", tier="critical", icon="🔴",
         keywords=["indemnify", "indemnification", "hold harmless"],
         explain="You agree to compensate the other party for losses/damages/legal costs they incur — even ones not entirely your fault, depending on wording.",
         example="If a client sues the company over your work, an indemnity clause may make YOU liable for the company's legal costs."),
    dict(name="Non-Compete Restriction", tier="critical", icon="🔴",
         keywords=["non-compete", "restraint of trade"],
         explain="Restricts you from joining a competitor or starting a similar business, usually for a fixed period after leaving.",
         example="A 2-year non-compete could block you from working in your own industry in the same region after resignation."),
    dict(name="Waiver of Legal Rights", tier="critical", icon="🔴",
         keywords=["waiver of rights", "irrevocably waives"],
         explain="You are giving up a legal right you'd otherwise have — e.g., right to sue, right to a jury/court, right to appeal.",
         example="A waiver of the right to litigate may force you into binding arbitration only, even for serious disputes."),
    dict(name="Personal Data Sharing Consent", tier="critical", icon="🔴",
         keywords=["share your personal information", "shared with third parties"],
         explain="You are consenting to your personal data being shared with third parties, sometimes including marketing partners.",
         example="Your phone number/income data could be shared with partner companies for cross-selling."),
    dict(name="Auto-Renewal Clause", tier="critical", icon="🔴",
         keywords=["auto-renew", "automatically renew", "automatic renewal"],
         explain="The contract renews itself unless you actively cancel within a specific window.",
         example="A gym membership silently auto-renews for another year unless you cancel 30 days before renewal."),
    dict(name="Excessive Penalty / Liquidated Damages", tier="critical", icon="🔴",
         keywords=["liquidated damages", "penalty clause", "default interest"],
         explain="A pre-fixed monetary penalty is charged on breach/delay — sometimes far higher than regulators consider reasonable.",
         example="A '5% per day' late fee is effectively 150%+ per month — vastly higher than typical regulatory norms."),
    dict(name="Irrevocable Clause", tier="critical", icon="🔴",
         keywords=["irrevocable", "irrevocably"],
         explain="Once given, this commitment/authorization CANNOT be cancelled or reversed later.",
         example="An irrevocable Power of Attorney cannot be cancelled unilaterally — you may need consent or a court order."),
    dict(name="Foreign Jurisdiction / Arbitration", tier="caution", icon="🟡",
         keywords=["arbitration", "exclusive jurisdiction", "governed by the laws of"],
         explain="Disputes may need to be resolved via arbitration and/or in courts of a specific city/country.",
         example="If jurisdiction is fixed to a distant city, you may have to travel and hire local counsel there."),
    dict(name="Interest Rate Clause", tier="caution", icon="🟡",
         keywords=["rate of interest", "per annum", "compounded annually"],
         explain="An interest rate is specified — always compare against prevailing market/regulatory rates.",
         example="A personal loan at 30%+ p.a. is well above typical bank personal-loan rates (~10-16% p.a.)."),
    dict(name="Notice Period Clause", tier="caution", icon="🟡",
         keywords=["notice period", "days prior written notice"],
         explain="Defines how much advance notice you must give (or receive) before termination/exit.",
         example="A 90-day notice period means you may need to keep working (or pay in lieu) for 3 months before leaving."),
    dict(name="Restrictive Covenant", tier="caution", icon="🟡",
         keywords=["non-solicitation", "shall not solicit"],
         explain="Limits certain future actions like soliciting clients/employees of the other party.",
         example="A non-solicitation clause may prevent you from hiring former colleagues for 1-2 years."),
    dict(name="Force Majeure Limitation", tier="caution", icon="🟡",
         keywords=["force majeure"],
         explain="Defines what 'unforeseeable events' excuse either party from performing obligations — check if it's one-sided.",
         example="If force majeure only protects the other party, you may still owe payments during genuine emergencies."),
    dict(name="Right to Cancel / Cooling-off", tier="info", icon="🟢",
         keywords=["cooling-off period", "free look period"],
         explain="You have a defined window in which you can cancel without penalty — a consumer-friendly clause.",
         example="A 15-day 'free look period' on insurance lets you return it for a full refund if you change your mind."),
    dict(name="Grievance Redressal", tier="info", icon="🟢",
         keywords=["grievance redressal", "grievance officer"],
         explain="A formal complaints mechanism exists before escalating to courts/regulators — generally positive.",
         example="You can approach the Grievance Officer first, often faster/cheaper than litigation."),
    dict(name="Standard Confidentiality", tier="info", icon="🟢",
         keywords=["keep confidential", "confidential information"],
         explain="Both parties agree to protect shared confidential information — a standard, generally balanced clause.",
         example="Trade secrets discussed during the contract cannot be disclosed to competitors."),
]

FRAUD_PATTERNS = ["expires in", "limited time", "act now", "guaranteed returns", "risk free",
    "risk-free", "double your money", "no questions asked", "urgent action required",
    "offer valid till today", "100% guaranteed"]

BENCHMARKS = {"loan_interest_high_pa": 20.0, "penalty_high_daily": 0.5, "notice_period_low_days": 30}

LANGUAGES = {
    "English": "en", "Hindi": "hi", "Hinglish (approx. Hindi)": "hi", "Bengali": "bn",
    "Marathi": "mr", "Telugu": "te", "Tamil": "ta", "Gujarati": "gu", "Urdu": "ur",
    "Kannada": "kn", "Malayalam": "ml", "Punjabi": "pa",
}

WHATIF_SCENARIOS = {
    ("miss payment", "missed payment", "can't pay", "cannot pay", "default on"):
        "If a payment/EMI is missed: check for 'penalty' or 'default interest' clauses above — "
        "these typically apply immediately. Some agreements also contain an ACCELERATION clause "
        "meaning the ENTIRE outstanding amount becomes due immediately. 📌 Action: contact the "
        "lender/landlord BEFORE the due date to request a grace period.",
    ("lose my job", "lose job", "fired", "laid off", "job loss"):
        "Most agreements do NOT waive payment obligations for job loss unless a specific hardship "
        "clause exists (rare). 📌 Action: look for 'force majeure' or 'hardship' clauses; renegotiate "
        "proactively before missing a due date.",
    ("terminate early", "exit early", "break the contract", "cancel early", "get out of this"):
        "Check the 'Termination' and 'Notice Period' clauses. Early exit usually requires advance "
        "written notice and sometimes a pre-agreed exit penalty. 📌 Use the Exit Strategy Advisor tab.",
    ("not renew", "avoid renewal", "cancel auto renewal", "stop auto-renewal"):
        "If an 'Auto-Renewal' clause was detected, you typically must send a cancellation notice "
        "within a specific window BEFORE the renewal date (commonly 30-60 days).",
}

# ==========================================================================
# SESSION STATE INIT
# ==========================================================================
DEFAULTS = {
    "doc_text": None, "doc_name": None, "doc_type": None, "doc_type_confidence": 0,
    "doc_type_candidates": [], "jurisdiction_flags": [],
    "matches": {"critical": [], "caution": [], "info": []}, "fraud_hits": [],
    "financials": [], "dates_found": [], "form_data": {}, "checklist": {},
    "reminders": [], "chat_log": [], "risk_score": 0, "lang": "English",
    "font_scale": 1.0, "high_contrast": False, "dyslexia_font": False,
    "plan": "Free", "openai_key": "", "authenticity_notes": [], "show_debug": False,
    "extraction_log": [],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ==========================================================================
# ROBUST FILE EXTRACTION  (multi-backend, honest error reporting)
# ==========================================================================

def extract_docx_zip_fallback(file_bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            with z.open('word/document.xml') as f:
                tree = ElementTree.parse(f)
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        paragraphs = []
        for para in tree.getroot().iter(ns + 'p'):
            texts = [node.text for node in para.iter(ns + 't') if node.text]
            if texts:
                paragraphs.append(''.join(texts))
        return "\n".join(paragraphs), None
    except Exception as e:
        return None, f"ZIP/XML fallback failed: {e}"


def extract_pdf_pdfplumber(file_bytes):
    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts), None
    except Exception as e:
        return None, f"pdfplumber failed: {e}"


def extract_pdf_pypdf(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return None, "PDF is password-protected — cannot extract without password."
        text_parts = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(text_parts), None
    except Exception as e:
        return None, f"pypdf failed: {e}"


def extract_pdf_ocr(file_bytes):
    if not (HAVE_PDF2IMAGE and HAVE_TESSERACT):
        return None, "OCR fallback unavailable (needs pdf2image + poppler + pytesseract)."
    try:
        images = convert_from_bytes(file_bytes)
        text_parts = [pytesseract.image_to_string(img) for img in images]
        return "\n".join(text_parts), None
    except Exception as e:
        return None, f"OCR fallback failed: {e}"


def extract_text_from_file(uploaded_file):
    name = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()
    log = []

    if name.endswith(".pdf"):
        text = None
        if HAVE_PDFPLUMBER:
            text, err = extract_pdf_pdfplumber(file_bytes)
            log.append(("pdfplumber", "OK" if text else err))
        if (not text or len(text.strip()) < 30) and HAVE_PYPDF:
            text2, err = extract_pdf_pypdf(file_bytes)
            log.append(("pypdf", "OK" if text2 else err))
            if text2 and len(text2.strip()) > len((text or "").strip()):
                text = text2
        if not text or len(text.strip()) < 30:
            text3, err = extract_pdf_ocr(file_bytes)
            log.append(("OCR (scanned PDF)", "OK" if text3 else err))
            if text3:
                text = text3
        st.session_state.extraction_log = log
        if not text or len(text.strip()) < 10:
            missing = []
            if not HAVE_PDFPLUMBER: missing.append("pdfplumber")
            if not HAVE_PYPDF: missing.append("pypdf")
            hint = f" Missing libraries: {', '.join(missing)}." if missing else ""
            return None, ("❌ Could not extract readable text from this PDF. It may be a scanned "
                          f"image without OCR support available, corrupted, or password-protected.{hint} "
                          "See Settings → Library Status / Debug Log for details.")
        if len(text.strip()) < 60:
            return text, "⚠️ Very little text extracted — this may be a scanned/image-based PDF with low OCR accuracy. Consider re-uploading a higher-resolution scan."
        return text, None

    elif name.endswith((".png", ".jpg", ".jpeg")):
        if not (HAVE_PIL and HAVE_TESSERACT):
            return None, "❌ OCR unavailable — install Pillow + pytesseract AND the Tesseract OCR engine on your system."
        try:
            img = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(img)
        except Exception as e:
            return None, f"❌ OCR failed: {e}"
        if len(text.strip()) < 20:
            return text, "⚠️ Poor scan quality — text extraction was minimal. Try a clearer, higher-contrast scan."
        return text, None

    elif name.endswith(".docx"):
        text = None
        if HAVE_DOCX_LIB:
            try:
                doc = DocxDocument(io.BytesIO(file_bytes))
                text = "\n".join(p.text for p in doc.paragraphs)
                log.append(("python-docx", "OK" if text.strip() else "Extracted empty text"))
            except Exception as e:
                log.append(("python-docx", f"failed: {e}"))
        if not text or len(text.strip()) < 10:
            text2, err = extract_docx_zip_fallback(file_bytes)
            log.append(("ZIP/XML fallback", "OK" if text2 else err))
            if text2:
                text = text2
        st.session_state.extraction_log = log
        if not text or len(text.strip()) < 5:
            return None, "❌ Could not extract text from this Word file — it may be corrupted or an old .doc (not .docx) format. Please re-save as .docx or PDF."
        return text, None

    elif name.endswith(".doc"):
        return None, "❌ Legacy .doc format is not supported — please re-save as .docx or PDF and re-upload."

    elif name.endswith(".txt"):
        try:
            return file_bytes.decode("utf-8", errors="ignore"), None
        except Exception as e:
            return None, f"❌ Could not read text file: {e}"

    else:
        return None, "❌ Unsupported file format. Please upload PDF, DOCX, TXT, PNG or JPG."


# ==========================================================================
# CLASSIFICATION  (weighted, word-boundary matching, honest confidence)
# ==========================================================================

def classify_document(text):
    text_l = text.lower()
    raw_scores = {}
    matched_keywords = {}
    for doc_type, keywords in DOC_TYPES.items():
        score = 0
        hits = []
        for kw in keywords:
            c = kw_count(kw, text_l)
            if c > 0:
                score += c * kw_weight(kw)
                hits.append(kw)
        raw_scores[doc_type] = score
        matched_keywords[doc_type] = hits

    total = sum(raw_scores.values())
    ranked = sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)

    if total == 0 or ranked[0][1] == 0:
        return "General / Unclassified Legal Document", 0, [], matched_keywords

    best_type, best_score = ranked[0]
    confidence = round(100 * best_score / total)
    candidates = [(t, round(100 * s / total)) for t, s in ranked[1:4] if s > 0]

    if confidence < 35:
        return "Uncertain — please verify manually", confidence, ranked[:4], matched_keywords

    return best_type, confidence, candidates, matched_keywords


def detect_jurisdiction(text):
    text_l = text.lower()
    flags = []
    found_states = [s.title() for s in INDIAN_STATES if kw_present(s, text_l)]
    if found_states:
        flags.append(("info", f"Indian jurisdiction detected: {', '.join(found_states[:3])}"))
    foreign = [f for f in FOREIGN_HINTS if kw_present(f, text_l)]
    if foreign and any(kw_present(t, text_l) for t in ["jurisdiction", "governing law", "courts of"]):
        flags.append(("critical", f"⚠️ Possible FOREIGN jurisdiction/governing law reference detected: {', '.join(set(foreign))}"))
    if not found_states and not foreign:
        flags.append(("info", "No explicit jurisdiction/governing-law statement clearly detected — verify manually."))
    return flags


def scan_authenticity(text):
    text_l = text.lower()
    notes = []
    markers = ["seal", "stamp", "letterhead", "authorized signatory", "digitally signed", "watermark", "registration no"]
    found = [m for m in markers if kw_present(m, text_l)]
    if found:
        notes.append(f"✅ Institutional markers found: {', '.join(found)} — supports (not guarantees) authenticity.")
    else:
        notes.append("⚠️ No letterhead/seal/signatory markers detected in extracted text — verify the source directly with the issuer.")
    if kw_present("version", text_l) or kw_present("supersede", text_l):
        notes.append("ℹ️ Document references versioning/supersession language — confirm you have the LATEST version before signing.")
    return notes


def scan_red_flags(text):
    matches = {"critical": [], "caution": [], "info": []}
    text_l = text.lower()
    for item in EXPLAIN_DB:
        for kw in item["keywords"]:
            if kw_present(kw, text_l):
                idx = text_l.find(kw)
                start = max(0, idx - 90)
                end = min(len(text), idx + len(kw) + 90)
                context = text[start:end].strip().replace("\n", " ")
                matches[item["tier"]].append({
                    "name": item["name"], "icon": item["icon"], "keyword": kw,
                    "context": f"...{context}...", "explain": item["explain"], "example": item["example"],
                })
                break
    return matches


def scan_fraud_patterns(text):
    text_l = text.lower()
    return [p for p in FRAUD_PATTERNS if kw_present(p, text_l)]


def extract_financials(text):
    patterns = [
        r"(?:₹|Rs\.?|INR)\s?[\d,]+(?:\.\d{1,2})?",
        r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\s?(?:lakh|lakhs|crore|crores)\b",
        r"\b\d{1,3}(?:\.\d+)?\s?%",
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text, flags=re.IGNORECASE))
    seen = set(); uniq = []
    for f in found:
        if f.lower() not in seen:
            seen.add(f.lower()); uniq.append(f)
    return uniq[:25]


def extract_dates(text):
    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(found))[:15]


def compute_risk_score(matches):
    score = len(matches["critical"]) * 15 + len(matches["caution"]) * 6 + len(matches["info"]) * 1
    return min(100, score)


def benchmark_analysis(text):
    results = []
    for m in re.finditer(r"(\d{1,3}(?:\.\d+)?)\s?%", text):
        pct = float(m.group(1))
        start = max(0, m.start() - 60)
        context = text[start:m.start()].lower()
        if "interest" in context or "per annum" in context:
            if pct > BENCHMARKS["loan_interest_high_pa"]:
                results.append(f"🔴 Interest rate of {pct}% p.a. found — notably ABOVE the common benchmark range (~10–20% p.a.).")
            else:
                results.append(f"🟢 Interest rate of {pct}% found — within a broadly typical range, but confirm against current market rates.")
        elif "penalty" in context or "late" in context or "default" in context:
            if pct > BENCHMARKS["penalty_high_daily"]:
                results.append(f"🔴 Penalty/late fee of {pct}% found — extremely high if charged daily/monthly.")
    if not results:
        results.append("ℹ️ No clearly labeled interest/penalty percentages found near financial keywords — manual review recommended.")
    return results


def ai_explain_with_llm(text, api_key, level="summary"):
    if not (HAVE_OPENAI and api_key):
        return None
    try:
        client = OpenAI(api_key=api_key)
        prompts = {
            "summary": "Summarize this legal document in under 120 words for a layperson: purpose, key obligations, top 3 risks.",
            "deep": "Provide a clause-by-clause plain-language legal analysis of this document, flagging risky clauses.",
        }
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful legal document explainer for laypeople. Always add: This is not legal advice."},
                {"role": "user", "content": prompts.get(level, prompts["summary"]) + "\n\nDOCUMENT:\n" + text[:6000]},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"(LLM call failed, showing rule-based analysis instead — {e})"


def translate_text(text, target_lang_code):
    if target_lang_code == "en" or not text:
        return text
    if not HAVE_TRANSLATOR:
        return text + "\n\n[Translation library not installed — showing English]"
    try:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        out = [GoogleTranslator(source="auto", target=target_lang_code).translate(c) for c in chunks]
        return " ".join(out)
    except Exception:
        return text + "\n\n[Translation service unavailable — showing English]"


def text_to_speech_bytes(text, lang_code="en"):
    if not HAVE_TTS:
        return None
    try:
        tts = gTTS(text=text[:1500], lang=lang_code if lang_code != "hi" else "hi")
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception:
        return None


def validate_pan(v): return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", v.strip().upper()))
def validate_aadhaar(v): return bool(re.fullmatch(r"\d{12}", v.strip().replace(" ", "")))
def validate_ifsc(v): return bool(re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", v.strip().upper()))
def validate_pincode(v): return bool(re.fullmatch(r"\d{6}", v.strip()))
def validate_phone(v): return bool(re.fullmatch(r"[6-9]\d{9}", v.strip()))


def sanitize_for_pdf(text):
    return text.encode("latin-1", "replace").decode("latin-1")

def generate_pdf_report(data):
    if not HAVE_FPDF:
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, sanitize_for_pdf(f"{APP_NAME} — Evidence & Analysis Report"))
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 6, sanitize_for_pdf(APP_TAGLINE))
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, sanitize_for_pdf(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    pdf.ln(4)

    def section(title, body):
        pdf.set_font("Arial", "B", 13)
        pdf.multi_cell(0, 8, sanitize_for_pdf(title))
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, sanitize_for_pdf(body if body else "N/A"))
        pdf.ln(2)

    section("Document Name", data.get("doc_name", ""))
    section("Detected Document Type (confidence)", f"{data.get('doc_type','')} ({data.get('confidence',0)}%)")
    section("Risk Score (0-100)", str(data.get("risk_score", "")))

    crit = "\n".join([f"- {m['name']}: {m['explain']}" for m in data.get("matches", {}).get("critical", [])])
    section("Critical Warnings Shown To User", crit)
    caution = "\n".join([f"- {m['name']}: {m['explain']}" for m in data.get("matches", {}).get("caution", [])])
    section("Caution Alerts Shown To User", caution)
    section("Financial Figures Detected", ", ".join(data.get("financials", [])))
    section("Important Dates Detected", ", ".join(data.get("dates", [])))

    checklist = data.get("checklist", {})
    checklist_txt = "\n".join([f"[{'x' if v else ' '}] {k}" for k, v in checklist.items()])
    section("Pre-Submission Checklist Status", checklist_txt)

    form_data = data.get("form_data", {})
    form_txt = "\n".join([f"{k}: {v}" for k, v in form_data.items()])
    section("User-Entered Form Data (snapshot)", form_txt)

    section("Disclaimer", f"This report is generated by {APP_NAME}, an automated rule-based/AI assistant, for informational purposes only and does NOT constitute legal advice. Document type classification is a statistical estimate — always verify manually. Consult a qualified lawyer before acting on any contract.")

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1")
    return bytes(out)


def generate_ics(summary, description, dt: datetime):
    uid = f"{random.randint(10000,99999)}@samjho.app"
    dt_str = dt.strftime("%Y%m%dT%H%M%S")
    now_str = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//{APP_NAME}//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now_str}
DTSTART:{dt_str}
SUMMARY:{summary}
DESCRIPTION:{description}
END:VEVENT
END:VCALENDAR
""".encode("utf-8")


def generate_exit_letter(doc_type, your_name, other_party, notice_days, reason):
    today = datetime.now().strftime("%d %B %Y")
    return f"""Date: {today}

To,
{other_party or '[Other Party Name]'}

Subject: Notice of Termination / Exit — {doc_type}

Dear Sir/Madam,

I, {your_name or '[Your Name]'}, am writing to formally notify you of my intention to terminate/exit
the above-referenced {doc_type.lower()} in accordance with the notice period of {notice_days} days
as stipulated therein.

Reason for exit (if applicable): {reason or 'Not specified'}

I request you to confirm receipt of this notice and share details of any pending dues,
deposit refund process, or handover formalities required to complete this exit smoothly.

Regards,
{your_name or '[Your Name]'}

---
Generated with {APP_NAME} ({APP_TAGLINE}) — this template is for guidance only and is not legal advice.
"""


def whatif_answer(question, doc_type, matches):
    q = question.lower()
    for keys, ans in WHATIF_SCENARIOS.items():
        if any(k in q for k in keys):
            extra = ""
            if matches["critical"]:
                extra = " Also note the CRITICAL clauses already flagged above (" + \
                        ", ".join(m["name"] for m in matches["critical"][:3]) + ") — these directly affect this scenario."
            return ans + extra
    return (f"Based on your {doc_type}, I don't have a specific pre-built scenario for that question. "
            "General advice: check the Termination, Penalty, and Notice Period clauses in the Warnings tab, "
            "and use the Exit Strategy Advisor for a formal notice template. For anything financially significant, "
            "consider a quick expert consultation (see Trust & Safety tab).")


# ==========================================================================
# UI — SIDEBAR
# ==========================================================================
inject_css(st.session_state.font_scale, st.session_state.high_contrast, st.session_state.dyslexia_font)

with st.sidebar:
    # ---- Highlighted brand box: BIG glowing seal logo + gradient title + pill tagline ----
    # Built as a single-line HTML string (no embedded newlines) to prevent
    # Streamlit's markdown renderer from misreading indented lines as code.
    sidebar_brand_html = (
        '<div class="sidebar-brand-box">'
        f'{get_seal_logo_svg(92, grad_id="sbLogo")}'
        f'<span class="sidebar-brand-title-big">{APP_NAME}</span>'
        f'<span class="sidebar-tagline-highlight">{APP_TAGLINE}</span>'
        '</div>'
    )
    st.markdown(sidebar_brand_html, unsafe_allow_html=True)

    page = st.radio("Navigate", [
        "🏠 Home", "📄 1 · Document Intake", "🧠 2 · AI Explanation",
        "✍️ 3 · Smart Form Fill", "⚠️ 4 · Warnings & Simulator",
        "✅ 5 · Review & Report", "📅 6 · Post-Submission",
        "🛡️ Trust & Safety", "⚙️ Settings",
    ])

    st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
    st.markdown("**Plan:** " + st.session_state.plan)
    if st.session_state.plan == "Free":
        if st.button("⭐ Upgrade to Pro (demo)"):
            st.session_state.plan = "Pro"
            st.rerun()

    st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
    st.caption(f"🔒 {APP_NAME} provides automated, informational analysis and is **NOT legal advice**.")


# ==========================================================================
# PAGE: HOME
# ==========================================================================
if page == "🏠 Home":
    home_header_html = (
        '<div class="ll-header"><div class="header-content">'
        f'<div class="logo-mark">{get_seal_logo_svg(100, grad_id="homeLogo")}</div>'
        '<div class="title-block">'
        f'<span class="kicker">{APP_KICKER}</span>'
        f'<h1 class="brand-title">{APP_NAME}<span class="accent-dot">.</span></h1>'
        f'<div class="brand-tagline">{APP_TAGLINE}</div>'
        '<p class="brand-sub">Upload any contract, agreement or form — get an instant plain-language '
        'risk breakdown, tiered warnings, smart form-filling help, and a downloadable evidence report '
        '— in your language.</p>'
        '</div></div></div>'
    )
    st.markdown(home_header_html, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    for col, icon, title, desc in [
        (c1, "📄", "Intake & Classify", "Auto-detect doc type (with confidence %), jurisdiction & authenticity markers."),
        (c2, "🧠", "AI Explanation", "3-level plain-language breakdown in 12 languages."),
        (c3, "⚠️", "Risk Warnings", "Tiered critical/caution/info alerts + benchmark comparison."),
        (c4, "✅", "Review & Protect", "Evidence PDF + reminders so you're never caught off guard."),
    ]:
        with col:
            st.markdown(f"""<div class="ll-card"><h3>{icon} {title}</h3><p style="opacity:.8">{desc}</p></div>""", unsafe_allow_html=True)

    st.info("Go to **📄 1 · Document Intake** in the sidebar to upload your first document.")
    st.warning(f"**Disclaimer:** {APP_NAME} offers automated, educational analysis only — including a *confidence-scored, correctable* document classifier. It is **not a substitute for a licensed lawyer**.")


# ==========================================================================
# PAGE 1: DOCUMENT INTAKE
# ==========================================================================
elif page == "📄 1 · Document Intake":
    page_header("📄 Phase 1 — Document Intake & Validation")

    uploaded = st.file_uploader("Upload document (PDF, DOCX, TXT, or image scan)",
                                 type=["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"])

    if uploaded:
        with st.spinner("🔍 Reading & analyzing document..."):
            text, note = extract_text_from_file(uploaded)
            if text:
                st.session_state.doc_text = text
                st.session_state.doc_name = uploaded.name
                doc_type, confidence, candidates, matched_kw = classify_document(text)
                st.session_state.doc_type = doc_type
                st.session_state.doc_type_confidence = confidence
                st.session_state.doc_type_candidates = candidates
                st.session_state.jurisdiction_flags = detect_jurisdiction(text)
                st.session_state.authenticity_notes = scan_authenticity(text)
                st.session_state.matches = scan_red_flags(text)
                st.session_state.fraud_hits = scan_fraud_patterns(text)
                st.session_state.financials = extract_financials(text)
                st.session_state.dates_found = extract_dates(text)
                st.session_state.risk_score = compute_risk_score(st.session_state.matches)
            if note:
                if text:
                    st.warning(note)
                else:
                    st.error(note)
                    if st.session_state.show_debug and st.session_state.extraction_log:
                        st.code("\n".join(f"{k}: {v}" for k, v in st.session_state.extraction_log))

    if st.session_state.doc_text:
        st.success(f"✅ Loaded: **{st.session_state.doc_name}**")

        st.markdown("#### 📑 Document Type Classification")
        conf = st.session_state.doc_type_confidence
        conf_color = "🟢" if conf >= 60 else ("🟡" if conf >= 35 else "🔴")
        st.markdown(f'<div class="metric-pill">{conf_color} <b>Detected:</b> {st.session_state.doc_type} — <b>{conf}% confidence</b></div>', unsafe_allow_html=True)

        if conf < 60:
            st.warning("⚠️ Confidence is not high — please verify the type manually below to avoid incorrect analysis downstream.")
        if st.session_state.doc_type_candidates:
            alt = ", ".join(f"{t} ({c}%)" for t, c in st.session_state.doc_type_candidates if isinstance(c, int))
            if alt:
                st.caption(f"Other possible matches: {alt}")

        override = st.selectbox(
            "✅ Confirm or correct the document type",
            options=["(keep auto-detected)"] + list(DOC_TYPES.keys()) + ["General / Unclassified Legal Document"],
            index=0,
        )
        if override != "(keep auto-detected)":
            st.session_state.doc_type = override
            st.session_state.doc_type_confidence = 100
            st.success(f"Document type manually set to: **{override}**")

        colB, colC = st.columns(2)
        colB.markdown(f'<div class="metric-pill">🌍 <b>Jurisdiction hits:</b> {len(st.session_state.jurisdiction_flags)}</div>', unsafe_allow_html=True)
        colC.markdown(f'<div class="metric-pill">🔥 <b>Risk score:</b> {st.session_state.risk_score}/100</div>', unsafe_allow_html=True)

        st.markdown("#### 🌍 Jurisdiction & Regulatory Signals")
        for tier, msg in st.session_state.jurisdiction_flags:
            css = "risk-critical" if tier == "critical" else "risk-info"
            st.markdown(f'<div class="risk-box {css}">{msg}</div>', unsafe_allow_html=True)

        st.markdown("#### 🖋️ Authenticity Signals (heuristic)")
        for note in st.session_state.authenticity_notes:
            st.markdown(f"- {note}")

        st.markdown("#### 🚩 Immediate Red-Flag Quick Scan")
        n_crit = len(st.session_state.matches["critical"])
        n_caut = len(st.session_state.matches["caution"])
        if n_crit:
            st.markdown(f'<span class="badge badge-critical">🔴 {n_crit} Critical</span>'
                        f'<span class="badge badge-caution">🟡 {n_caut} Caution</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge badge-info">🟢 No critical red flags on quick scan</span>', unsafe_allow_html=True)

        if st.session_state.fraud_hits:
            st.error(f"⚠️ Pressure-tactic / suspicious phrasing detected: {', '.join(st.session_state.fraud_hits)}")

        with st.expander("📃 View extracted raw text"):
            st.text_area("Extracted text", st.session_state.doc_text, height=300)

        st.info("➡️ Proceed to **🧠 2 · AI Explanation** for the full breakdown.")
    else:
        st.info("Upload a document above to begin analysis.")


# ==========================================================================
# PAGE 2: AI EXPLANATION ENGINE
# ==========================================================================
elif page == "🧠 2 · AI Explanation":
    page_header("🧠 Phase 2 — AI-Powered Explanation Engine")

    if not st.session_state.doc_text:
        st.warning("Please upload a document in **Phase 1** first.")
        st.stop()

    lang_name = st.selectbox("🌐 Choose explanation language", list(LANGUAGES.keys()),
                              index=list(LANGUAGES.keys()).index(st.session_state.lang))
    st.session_state.lang = lang_name
    lang_code = LANGUAGES[lang_name]

    tabs = st.tabs(["⚡ Level 1 — Quick Summary", "🔎 Level 2 — Field Breakdown", "📚 Level 3 — Deep Analysis"])
    matches = st.session_state.matches
    doc_type = st.session_state.doc_type

    with tabs[0]:
        top_risks = (matches["critical"] + matches["caution"])[:3]
        summary_lines = [
            f"**Document type:** {doc_type} (confidence: {st.session_state.doc_type_confidence}%).",
            f"**Your key obligations:** " + (", ".join(m['name'] for m in matches['critical'][:5]) or "No major obligation clauses auto-detected — review manually."),
            f"**Top risks:** " + (", ".join(f"{m['icon']} {m['name']}" for m in top_risks) or "None flagged."),
            f"**Financial figures mentioned:** " + (", ".join(st.session_state.financials[:6]) or "None detected."),
        ]
        summary_text = "\n\n".join(summary_lines)

        llm_out = ai_explain_with_llm(st.session_state.doc_text, st.session_state.openai_key, "summary") if st.session_state.openai_key else None
        final_summary = llm_out if llm_out else summary_text
        translated = translate_text(final_summary, lang_code)
        st.markdown(f'<div class="ll-card">{translated.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

        if HAVE_TTS and st.button("🔊 Generate audio summary"):
            audio = text_to_speech_bytes(re.sub(r'[*_#]', '', final_summary), lang_code if lang_code in ["hi","bn","ta","te","mr","gu","kn","ml","pa","ur"] else "en")
            if audio:
                st.audio(audio, format="audio/mp3")
            else:
                st.error("Audio generation failed (needs internet connection).")

    with tabs[1]:
        st.caption("Icon key: 🔴 High Risk  🟡 Caution  🟢 Standard/Info")
        all_items = [("critical", m) for m in matches["critical"]] + \
                    [("caution", m) for m in matches["caution"]] + \
                    [("info", m) for m in matches["info"]]
        if not all_items:
            st.success("No specific flagged clauses detected via keyword scan — always review full text manually.")
        for tier, m in all_items:
            css = f"risk-{tier}"
            block = f"**{m['icon']} {m['name']}**\n\n_Context:_ \"{m['context']}\"\n\n**Plain-language meaning:** {m['explain']}\n\n**Real-world example:** {m['example']}"
            translated_block = translate_text(block, lang_code) if lang_code != "en" else block
            st.markdown(f'<div class="risk-box {css}">{translated_block}</div>', unsafe_allow_html=True)

    with tabs[2]:
        if st.session_state.openai_key:
            with st.spinner("Running deep LLM legal analysis..."):
                deep = ai_explain_with_llm(st.session_state.doc_text, st.session_state.openai_key, "deep")
            st.markdown(translate_text(deep, lang_code))
        else:
            st.info("💡 Add an OpenAI API key in **⚙️ Settings** to unlock full LLM-based clause-by-clause analysis. Showing rule-based deep view below.")
            paragraphs = [p for p in st.session_state.doc_text.split("\n") if len(p.strip()) > 40][:40]
            for i, para in enumerate(paragraphs, 1):
                tag = ""
                for m in matches["critical"] + matches["caution"]:
                    if m["keyword"] in para.lower():
                        tag = f" — related to flagged clause: **{m['icon']} {m['name']}**"
                        break
                with st.expander(f"Clause {i}" + tag):
                    st.write(para)
            st.caption("Related legal provisions / case law require a licensed legal database integration — consult a lawyer for binding interpretation.")


# ==========================================================================
# PAGE 3: SMART FORM FILLING
# ==========================================================================
elif page == "✍️ 3 · Smart Form Fill":
    page_header("✍️ Phase 3 — Intelligent Form Filling")
    if not st.session_state.doc_text:
        st.warning("Please upload a document in **Phase 1** first.")
        st.stop()

    st.caption("Every field below shows what it commits you to BEFORE you fill it.")

    FIELD_SAFEGUARDS = {
        "Full Name": "Used for identification on the document. Mandatory in almost all cases.",
        "PAN Number": "Used for tax/financial identification. Verify the requesting party's legitimacy first.",
        "Aadhaar Number": "Sensitive government ID — only share with verified entities; often not mandatory unless legally required.",
        "Phone Number": "May be used for contact/OTP verification. Usually mandatory for digital contracts.",
        "Email": "Used for official communication/notices — check if this becomes your registered legal-notice address.",
        "Address": "Establishes jurisdiction/notice address — legal notices may be sent here.",
        "Amount (₹)": "This becomes a financial figure you may be committing to pay/receive — double-check units.",
        "IFSC Code": "Identifies your bank branch — verify it matches your actual bank branch.",
        "Pincode": "Used to validate address/city match.",
    }

    if "form_data" not in st.session_state:
        st.session_state.form_data = {}

    st.markdown("### 🎙️ Voice-Assisted Input (experimental)")
    if HAVE_MIC and HAVE_SR:
        audio_bytes = audio_recorder(text="Click to record a value")
        if audio_bytes:
            r = sr.Recognizer()
            try:
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio_data = r.record(source)
                    recognized = r.recognize_google(audio_data)
                    st.success(f"Recognized: **{recognized}** — copy into the field below.")
            except Exception as e:
                st.error(f"Could not process audio ({e}). Please type manually below.")
    else:
        st.caption("🎤 Voice input libraries not installed — using text fallback.")

    st.markdown("### 📝 Form Fields")
    cols = st.columns(2)
    field_defs = [
        ("Full Name", "text"), ("PAN Number", "text"), ("Aadhaar Number", "text"),
        ("Phone Number", "text"), ("Email", "text"), ("Address", "textarea"),
        ("Amount (₹)", "number"), ("IFSC Code", "text"), ("Pincode", "text"),
    ]

    for i, (field, ftype) in enumerate(field_defs):
        col = cols[i % 2]
        with col:
            with st.expander(f"ℹ️ What does '{field}' commit you to?"):
                st.write(FIELD_SAFEGUARDS.get(field, "Standard field — low risk."))
                st.caption("This field may be optional depending on the form — check the original document.")
            if ftype == "textarea":
                val = st.text_area(field, value=st.session_state.form_data.get(field, ""), key=f"f_{field}")
            else:
                val = st.text_input(field, value=st.session_state.form_data.get(field, ""), key=f"f_{field}")
            st.session_state.form_data[field] = val

            if field == "PAN Number" and val:
                st.markdown("✅ Valid PAN format" if validate_pan(val) else "❌ Invalid PAN format (e.g. ABCDE1234F)")
            if field == "Aadhaar Number" and val:
                st.markdown("✅ Valid 12-digit format" if validate_aadhaar(val) else "❌ Must be exactly 12 digits")
            if field == "Phone Number" and val:
                st.markdown("✅ Valid mobile format" if validate_phone(val) else "❌ Must be 10 digits starting 6-9")
            if field == "IFSC Code" and val:
                st.markdown("✅ Valid IFSC format" if validate_ifsc(val) else "❌ Format: 4 letters + 0 + 6 alphanumeric")
            if field == "Pincode" and val:
                st.markdown("✅ Valid 6-digit pincode" if validate_pincode(val) else "❌ Must be 6 digits")

    if st.session_state.form_data.get("Amount (₹)"):
        st.info("💡 Confirm — is this amount **per month** or **per year / one-time**?")

    st.success("Form data auto-saved to your session for the Review phase.")


# ==========================================================================
# PAGE 4: WARNINGS & SIMULATOR
# ==========================================================================
elif page == "⚠️ 4 · Warnings & Simulator":
    page_header("⚠️ Phase 4 — Advanced Warning System")
    if not st.session_state.doc_text:
        st.warning("Please upload a document in **Phase 1** first.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["🚨 Tiered Alerts", "📊 Benchmark Comparison", "🎲 What-If Simulator"])
    matches = st.session_state.matches

    with tab1:
        st.markdown("#### 🔴 CRITICAL WARNINGS")
        if matches["critical"]:
            for m in matches["critical"]:
                st.markdown(f'<div class="risk-box risk-critical"><b>{m["icon"]} {m["name"]}</b><br>{m["explain"]}<br><i>{m["example"]}</i></div>', unsafe_allow_html=True)
            ack = st.checkbox("✅ I have read and understood all CRITICAL warnings above", key="ack_critical")
            if not ack:
                st.error("You must acknowledge critical warnings before proceeding to Review & Report.")
        else:
            st.success("No critical warnings detected via keyword scan.")

        st.markdown("#### 🟡 CAUTION ALERTS")
        if matches["caution"]:
            for m in matches["caution"]:
                st.markdown(f'<div class="risk-box risk-caution"><b>{m["icon"]} {m["name"]}</b><br>{m["explain"]}<br><i>{m["example"]}</i></div>', unsafe_allow_html=True)
        else:
            st.info("No caution-level items detected.")

        st.markdown("#### 🟢 INFORMATION NOTICES")
        if matches["info"]:
            for m in matches["info"]:
                st.markdown(f'<div class="risk-box risk-info"><b>{m["icon"]} {m["name"]}</b><br>{m["explain"]}</div>', unsafe_allow_html=True)
        else:
            st.caption("No standard/beneficial clauses auto-detected.")

    with tab2:
        st.markdown("#### 📊 Comparative / Benchmark Analysis")
        for line in benchmark_analysis(st.session_state.doc_text):
            st.markdown(f"- {line}")
        st.caption("Benchmarks used are illustrative approximations — always confirm against current regulatory circulars.")

    with tab3:
        st.markdown("#### 🎲 'What If' Scenario Simulator")
        q = st.text_input("Type your scenario question:")
        if st.button("Ask") and q:
            ans = whatif_answer(q, st.session_state.doc_type, matches)
            st.session_state.chat_log.append(("You", q))
            st.session_state.chat_log.append((APP_NAME, ans))
        for speaker, msg in st.session_state.chat_log[-10:]:
            with st.chat_message("user" if speaker == "You" else "assistant"):
                st.write(msg)


# ==========================================================================
# PAGE 5: REVIEW & REPORT
# ==========================================================================
elif page == "✅ 5 · Review & Report":
    page_header("✅ Phase 5 — Pre-Submission Review & Documentation")
    if not st.session_state.doc_text:
        st.warning("Please upload a document in **Phase 1** first.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📄 Original Document (excerpt)")
        st.text_area("Original", st.session_state.doc_text[:3000], height=300, disabled=True)
    with col2:
        st.markdown("#### ✍️ Your Filled Data")
        if st.session_state.form_data:
            if HAVE_PANDAS:
                df = pd.DataFrame(list(st.session_state.form_data.items()), columns=["Field", "Value"])
                st.dataframe(df, use_container_width=True, height=300)
            else:
                for k, v in st.session_state.form_data.items():
                    st.write(f"**{k}:** {v}")
        else:
            st.info("No form data entered yet (see Phase 3).")

    st.markdown("### ☑️ AI-Powered Final Checklist")
    checklist_items = [
        "All mandatory fields completed", "Supporting documents attached",
        "Understood all critical warnings", "Compared with alternatives (if applicable)",
        "Verified counterparty credentials", "Noted important dates (payment, renewal, termination)",
        "Saved a copy for my records",
    ]
    for item in checklist_items:
        st.session_state.checklist[item] = st.checkbox(item, value=st.session_state.checklist.get(item, False))

    completed = sum(1 for v in st.session_state.checklist.values() if v)
    st.progress(completed / len(checklist_items))
    st.caption(f"{completed}/{len(checklist_items)} checklist items complete")

    st.markdown("### 🧾 Evidence Trail — Downloadable Report")
    if st.button("📥 Generate Evidence PDF Report"):
        report_data = {
            "doc_name": st.session_state.doc_name,
            "doc_type": st.session_state.doc_type,
            "confidence": st.session_state.doc_type_confidence,
            "risk_score": st.session_state.risk_score,
            "matches": st.session_state.matches,
            "financials": st.session_state.financials,
            "dates": st.session_state.dates_found,
            "checklist": st.session_state.checklist,
            "form_data": st.session_state.form_data,
        }
        pdf_bytes = generate_pdf_report(report_data)
        if pdf_bytes:
            st.download_button("⬇️ Download Report PDF", data=pdf_bytes,
                                file_name=f"Samjho_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                mime="application/pdf")
            st.success("Report generated — keep it for your records.")
        else:
            st.error("fpdf2 not installed — cannot generate PDF. Run: pip install fpdf2")


# ==========================================================================
# PAGE 6: POST-SUBMISSION SUPPORT
# ==========================================================================
elif page == "📅 6 · Post-Submission":
    page_header("📅 Phase 6 — Post-Submission Support")
    if not st.session_state.doc_text:
        st.warning("Please upload a document in **Phase 1** first.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["⏰ Reminders", "🚪 Exit Strategy Advisor", "📈 Obligation Tracker"])

    with tab1:
        st.markdown("#### ⏰ Set a Reminder")
        r_title = st.text_input("Reminder title", value="Payment Due")
        r_date = st.date_input("Date", value=datetime.now() + timedelta(days=30))
        r_time = st.time_input("Time", value=datetime.strptime("09:00", "%H:%M").time())
        r_notes = st.text_area("Notes", value=f"Related to: {st.session_state.doc_name}")
        if st.button("➕ Add & Download Calendar Reminder (.ics)"):
            dt = datetime.combine(r_date, r_time)
            ics_bytes = generate_ics(r_title, r_notes, dt)
            st.session_state.reminders.append({"title": r_title, "when": str(dt)})
            st.download_button("⬇️ Download .ics file", data=ics_bytes, file_name=f"{r_title.replace(' ','_')}.ics", mime="text/calendar")
        if st.session_state.reminders:
            st.markdown("##### 📋 Saved reminders (this session)")
            for r in st.session_state.reminders:
                st.write(f"- **{r['title']}** — {r['when']}")

    with tab2:
        st.markdown("#### 🚪 Exit Strategy Advisor")
        c1, c2 = st.columns(2)
        with c1:
            your_name = st.text_input("Your name", value=st.session_state.form_data.get("Full Name", ""))
            other_party = st.text_input("Other party's name/organization")
        with c2:
            notice_days = st.number_input("Notice period (days)", min_value=0, value=30)
            reason = st.text_input("Reason for exit (optional)")
        if st.button("📝 Generate Exit Notice Letter"):
            letter = generate_exit_letter(st.session_state.doc_type, your_name, other_party, notice_days, reason)
            st.text_area("Preview", letter, height=320)
            st.download_button("⬇️ Download Letter (.txt)", data=letter.encode("utf-8"), file_name="exit_notice_letter.txt")
        st.caption("💡 Always send exit notices via a traceable channel and request written confirmation.")

    with tab3:
        st.markdown("#### 📈 Obligation Completion Tracker")
        obligations = [m["name"] for m in st.session_state.matches["critical"] + st.session_state.matches["caution"]]
        if obligations:
            for ob in obligations:
                st.checkbox(f"Obligation handled: {ob}", key=f"ob_{ob}")
        else:
            st.info("No specific obligations auto-detected to track.")
        st.warning("🔔 If you've missed any due date, revisit the **What-If Simulator** immediately.")


# ==========================================================================
# PAGE: TRUST & SAFETY
# ==========================================================================
elif page == "🛡️ Trust & Safety":
    page_header("🛡️ Trust, Safety & Accessibility")
    tab1, tab2, tab3, tab4 = st.tabs(["🕵️ Fraud Detection", "👩‍⚖️ Expert Consultation", "♿ Accessibility", "🔐 Privacy"])

    with tab1:
        st.markdown("#### 🕵️ Fraud / Pressure-Tactic Detector")
        if st.session_state.doc_text:
            hits = st.session_state.fraud_hits
            if hits:
                st.error(f"⚠️ Suspicious high-pressure phrases found: {', '.join(hits)}")
            else:
                st.success("No obvious pressure-tactic phrases detected.")
            st.markdown("#### 🏢 Counterparty Credential Checklist (manual)")
            for item in ["Company registration / CIN verified on MCA portal", "GST number verified",
                         "Physical office address verified", "Online reviews / complaints checked",
                         "License/registration for regulated activity verified"]:
                st.checkbox(item)
        else:
            st.info("Upload a document in Phase 1 to run fraud detection.")

    with tab2:
        st.markdown("#### 👩‍⚖️ Talk to an Expert")
        st.markdown(f"**Current risk score:** {st.session_state.risk_score}/100")
        consult_type = st.radio("Choose consultation type", ["Free duty counsel (govt. schemes)", "Pro-bono lawyer (EWS)", "Paid consultation (15-min video call)"])
        name = st.text_input("Your name for booking")
        phone = st.text_input("Contact number")
        if st.button("📞 Request Consultation (demo)"):
            if name and phone:
                st.success(f"✅ Request logged for **{consult_type}**.")
            else:
                st.error("Please enter your name and phone number.")

    with tab3:
        st.markdown("#### ♿ Accessibility Settings")
        st.session_state.font_scale = st.slider("Text size scale", 0.8, 1.6, st.session_state.font_scale, 0.1)
        st.session_state.high_contrast = st.checkbox("High-contrast mode", st.session_state.high_contrast)
        st.session_state.dyslexia_font = st.checkbox("Dyslexia-friendly font", st.session_state.dyslexia_font)
        st.info("Settings apply instantly across the app.")

    with tab4:
        st.markdown("#### 🔐 Privacy & Security")
        st.write(f"Documents are processed in-memory during your session only. No text leaves {APP_NAME} unless you enable the optional OpenAI integration.")
        if st.button("🗑️ Self-Destruct: Delete ALL my session data now"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.success("All session data cleared.")
            st.rerun()


# ==========================================================================
# PAGE: SETTINGS
# ==========================================================================
elif page == "⚙️ Settings":
    page_header("⚙️ Settings")

    st.markdown("#### 🤖 Optional: Enable Real LLM-Powered Explanations")
    key_input = st.text_input("OpenAI API Key", type="password", value=st.session_state.openai_key)
    if st.button("Save Key"):
        st.session_state.openai_key = key_input
        st.success("Saved for this session." if key_input else "Key cleared — using offline rule-based engine.")

    st.markdown("---")
    st.markdown("#### 📦 Library Status")
    status = {
        "PDF (pdfplumber)": HAVE_PDFPLUMBER,
        "PDF fallback (pypdf)": HAVE_PYPDF,
        "PDF OCR fallback (pdf2image)": HAVE_PDF2IMAGE,
        "DOCX (python-docx)": HAVE_DOCX_LIB,
        "DOCX fallback (built-in ZIP/XML)": True,
        "Image OCR (Pillow + pytesseract)": HAVE_PIL and HAVE_TESSERACT,
        "Translation (deep-translator)": HAVE_TRANSLATOR,
        "Text-to-Speech (gTTS)": HAVE_TTS,
        "PDF report export (fpdf2)": HAVE_FPDF,
        "Tables (pandas)": HAVE_PANDAS,
        "LLM upgrade (openai)": HAVE_OPENAI,
        "Voice recorder": HAVE_MIC,
        "Speech recognition": HAVE_SR,
    }
    for lib, ok in status.items():
        st.write(("✅ " if ok else "⚠️ ") + lib)

    st.markdown("---")
    st.session_state.show_debug = st.checkbox("🐛 Show technical extraction debug log on errors", st.session_state.show_debug)
    if st.session_state.extraction_log:
        with st.expander("Last extraction attempt log"):
            for backend, result in st.session_state.extraction_log:
                st.write(f"**{backend}:** {result}")

    st.markdown("---")
    st.caption(f"{APP_NAME} ({APP_TAGLINE}) is an informational tool and does NOT provide legal advice. Document classification is a statistical estimate shown with a confidence score — always verify manually.")