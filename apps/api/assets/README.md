# Prescription letterhead assets

WhatsApp PDFs draw a full-page background from here when `pdf_templates.logo_path` points at a relative path.

Expected files (already seeded for Aarogyam clinic 1):

- `prescription_background.jpg` — default fallback
- `prescription_backgrounds/clinic_1_bg.jpg` — clinic 1 WhatsApp background

# Warranty card PDF

- `warranty_card_pdf.png` — full-page background for warranty card PDFs (ported from legacy)

If missing, the PDF still sends with text slots only (no background).
