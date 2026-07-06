🪶 Samjho — Pehle Samjho, Phir Sign Karo
AI-powered legal document assistant for empowering India's underserved millions.

Samjho helps everyday people understand contracts, agreements, and government forms before they sign — breaking down dense legal language into plain, actionable explanations across 12+ Indian languages.

Python
Streamlit
License
Status

📖 About
Millions of people in India sign employment contracts, loan agreements, rental leases, and government forms every day without fully understanding what they're agreeing to — often at the cost of hidden penalties, unfair clauses, or legal exposure they never knew existed.

Samjho ("Understand") bridges this gap. Upload any document and get an instant, plain-language breakdown of what it means, what it's asking of you, and what could go wrong — in your own language, before you sign.

⚠️ Samjho provides automated, educational analysis and is not a substitute for a licensed lawyer.

🌟 Features
📄 Document Intake
Multi-format support — PDF, DOCX, TXT, and scanned images (PNG/JPG)
Layered extraction pipeline with OCR fallback for scanned/image-based documents
Automatic document-type classification (Employment Contract, Loan Agreement, Rental Lease, NDA, Privacy Policy, Insurance Policy, Government Form, and more) with a confidence score
Jurisdiction detection (Indian vs. foreign governing law) and authenticity signal scanning
🧠 AI-Powered Explanation Engine
Three levels of explanation — Quick Summary, Field-by-Field Breakdown, and Deep Clause Analysis
Multilingual output across 12+ Indian languages (Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu, Kannada, Malayalam, Punjabi, and more)
Optional audio narration of summaries
Optional GPT-powered deep analysis (bring your own OpenAI API key)
🚩 Tiered Risk Warnings
Clauses flagged as 🔴 Critical, 🟡 Caution, or 🟢 Informational
Plain-language explanation + real-world consequence example for every flagged clause
Benchmark comparison for interest rates and penalty clauses against typical market norms
Fraud / high-pressure language detector (e.g., "act now," "guaranteed returns")
✍️ Smart Form Filling
Field-level guidance on what each input actually commits you to
Built-in validation for PAN, Aadhaar, IFSC, phone number, and pincode formats
Experimental voice-assisted input
🎲 What-If Scenario Simulator
Ask natural-language questions like "What if I miss a payment?" or "What if I want to exit early?"
Answers are grounded in the clauses actually detected in your uploaded document
✅ Review & Reporting
Consolidated pre-submission checklist
Downloadable PDF evidence report summarizing document type, risk score, flagged clauses, and your entered data
📅 Post-Submission Support
Calendar reminders for due dates and renewals (.ics export)
Auto-generated exit/termination notice letters
Ongoing obligation tracker
🛡️ Trust, Safety & Accessibility
Counterparty verification checklist and fraud detection
Adjustable font size, high-contrast mode, and dyslexia-friendly font
In-memory session processing with a one-click "self-destruct" data wipe
🧩 How It Works
text

Upload Document → Extract & Classify → Explain in Your Language
       ↓                                        ↓
Fill Form Safely  ←──────────  Review Risks & Warnings
       ↓
Generate Evidence Report → Track Obligations Post-Signing
🛠️ Tech Stack
Layer	Technology
App Framework	Streamlit
PDF Extraction	pdfplumber, pypdf
OCR	pytesseract, pdf2image, Pillow
DOCX Parsing	python-docx (with native XML fallback)
Translation	deep-translator
Text-to-Speech	gTTS
PDF Report Export	fpdf2
Data Tables	pandas
LLM Integration (optional)	OpenAI API
Voice Input (optional)	audio-recorder-streamlit, SpeechRecognition
The app is built to degrade gracefully — every optional library is imported defensively, so Samjho keeps running with reduced features even if a dependency is missing.

📁 Project Structure
text

samjho/
├── app.py                   # Main Streamlit application
├── requirements.txt         # Python dependencies
├── packages.txt             # System-level dependencies (OCR)
├── .streamlit/
│   ├── config.toml          # Theme & server config
│   └── secrets.toml         # API keys (gitignored)
├── .gitignore
├── LICENSE
└── README.md
🛠️ Local Installation
Prerequisites
Python 3.9+
Tesseract OCR (for scanned document/image support)
Poppler (for scanned PDF rendering)
1. Clone the repository
Bash

git clone https://github.com/<your-username>/samjho.git
cd samjho
2. Create a virtual environment
Bash

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
3. Install Python dependencies
Bash

pip install -r requirements.txt
4. Install Tesseract OCR
Ubuntu/Debian

Bash

sudo apt-get install tesseract-ocr poppler-utils
macOS (Homebrew)

Bash

brew install tesseract poppler
