import io
import os
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from django.conf import settings
import qrcode

CARD_WIDTH = 3.375 * inch
CARD_HEIGHT = 2.125 * inch

DARK_GREEN = HexColor("#1E4A2C")
OLIVE = HexColor("#7C8C3E")
INK = HexColor("#17231A")
WHITE = HexColor("#FFFFFF")


def generate_member_id_card_pdf(member, verify_url):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(CARD_WIDTH, CARD_HEIGHT))

    # ---------- FRONT ----------
    c.setFillColor(WHITE)
    c.rect(0, 0, CARD_WIDTH, CARD_HEIGHT, fill=1, stroke=0)

    band_h = 0.42 * inch
    c.setFillColor(DARK_GREEN)
    c.rect(0, CARD_HEIGHT - band_h, CARD_WIDTH, band_h, fill=1, stroke=0)

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'acc-logo-print.png')
    if os.path.exists(logo_path):
        logo_size = 0.34 * inch
        c.drawImage(logo_path, 0.06 * inch, CARD_HEIGHT - band_h + 0.04 * inch,
                    width=logo_size, height=logo_size, mask='auto')

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(0.46 * inch, CARD_HEIGHT - band_h + 0.24 * inch, "APOSTOLIC CAMPUS CHURCH")
    c.setFont("Helvetica", 6)
    c.drawString(0.46 * inch, CARD_HEIGHT - band_h + 0.10 * inch, "Grace and Truth")

    photo_x, photo_y = 0.1 * inch, CARD_HEIGHT - band_h - 0.85 * inch
    photo_w = photo_h = 0.75 * inch
    c.setStrokeColor(OLIVE)
    c.setLineWidth(1)
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)
    if member.photo and hasattr(member.photo, 'path') and os.path.exists(member.photo.path):
        try:
            c.drawImage(member.photo.path, photo_x, photo_y, width=photo_w, height=photo_h, mask='auto')
        except Exception:
            pass

    tx = photo_x + photo_w + 0.12 * inch
    ty = CARD_HEIGHT - band_h - 0.14 * inch
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(tx, ty, member.full_name[:26])
    c.setFont("Helvetica", 6.5)
    c.drawString(tx, ty - 0.14 * inch, f"ID: {member.member_id}")
    c.drawString(tx, ty - 0.27 * inch, member.get_membership_type_display())
    c.drawString(tx, ty - 0.40 * inch, member.branch.name if member.branch else "")
    c.drawString(tx, ty - 0.53 * inch, f"Joined: {member.registered_at.strftime('%b %Y')}")

    qr_img = qrcode.make(verify_url)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format='PNG')
    qr_buf.seek(0)
    qr_reader = ImageReader(qr_buf)
    qr_size = 0.55 * inch
    c.drawImage(qr_reader, CARD_WIDTH - qr_size - 0.08 * inch, 0.08 * inch, width=qr_size, height=qr_size)

    c.setStrokeColor(OLIVE)
    c.setLineWidth(1.2)
    c.rect(1, 1, CARD_WIDTH - 2, CARD_HEIGHT - 2, fill=0, stroke=1)
    c.showPage()

    # ---------- BACK ----------
    c.setFillColor(WHITE)
    c.rect(0, 0, CARD_WIDTH, CARD_HEIGHT, fill=1, stroke=0)
    c.setFillColor(DARK_GREEN)
    c.rect(0, 0, CARD_WIDTH, 0.12 * inch, fill=1, stroke=0)

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(CARD_WIDTH / 2, CARD_HEIGHT - 0.28 * inch, "Apostolic Campus Church")
    c.setFont("Helvetica-Oblique", 6.5)
    c.setFillColor(OLIVE)
    c.drawCentredString(CARD_WIDTH / 2, CARD_HEIGHT - 0.42 * inch, '"Grace and Truth"')

    c.setFillColor(INK)
    c.setFont("Helvetica", 5.8)
    c.drawCentredString(CARD_WIDTH / 2, CARD_HEIGHT - 0.62 * inch, "This card certifies active membership at")
    c.drawCentredString(CARD_WIDTH / 2, CARD_HEIGHT - 0.72 * inch, "Apostolic Campus Church.")

    c.line(0.3 * inch, 0.55 * inch, CARD_WIDTH - 0.3 * inch, 0.55 * inch)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(CARD_WIDTH / 2, 0.46 * inch, "Authorized Signature")

    c.setFont("Helvetica", 5)
    c.drawCentredString(CARD_WIDTH / 2, 0.2 * inch, "Property of Apostolic Campus Church.")
    c.drawCentredString(CARD_WIDTH / 2, 0.12 * inch, "If found, please return to the nearest branch.")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf