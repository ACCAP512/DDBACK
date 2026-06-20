"""OCR document-intake — PDF→image (pypdfium2) → OCR (Tesseract subprocess) → classify → extract →
propose a match → human-confirm. Built in M4. OCR *proposes*; extracted fields land as
``needs_review`` until a human confirms; nothing auto-files. Local-first (client docs stay in-tenant);
cloud IDP is opt-in only. M0 placeholder.
"""
