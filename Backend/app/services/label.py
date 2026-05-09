"""
Warehouse label image generator.

Produces a print-ready PNG label containing:
  - Package metadata (SKU, sender, contents, weight, destination, date)
  - QR code encoding the SKU (scannable by the /verify/package endpoint)

Dependencies: qrcode[pil], Pillow
"""

import io
import os
import json
from datetime import datetime

import qrcode
from PIL import Image, ImageDraw, ImageFont
from barcode import Code128
from barcode.writer import ImageWriter


LABEL_W = 800
LABEL_H = 520
PADDING = 28

HEADER_H = 72
HEADER_BG = (30, 41, 59)
HEADER_FG = (248, 250, 252)

BODY_BG = (255, 255, 255)
TEXT_COLOR = (15, 23, 42)
MUTED_COLOR = (100, 116, 139)
ACCENT_COLOR = (37, 99, 235)
DIVIDER_COLOR = (226, 232, 240)

QR_SIZE = 220
RIGHT_COL_W = 420
RIGHT_COL_X = LABEL_W - PADDING - RIGHT_COL_W
QR_X = RIGHT_COL_X + (RIGHT_COL_W - QR_SIZE) // 2
QR_Y = HEADER_H + PADDING



def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try common system fonts; fall back to PIL default."""
    candidates = []
    if bold:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    # Pillow ≥ 10 supports size parameter
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()



def generate_label(
    sku: str,
    sender: str,
    recipient: str,
    contents: str,
    weight_kg: float,
    destination: str,
    routing_zone: str,
    created_at: datetime,
) -> bytes:
    """
    Render a warehouse label as PNG bytes.

    Parameters match :class:`~app.db.models.PackageRecord` fields so the
    caller can unpack the ORM record directly.
    """
    img = Image.new("RGB", (LABEL_W, LABEL_H), BODY_BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (LABEL_W, HEADER_H)], fill=HEADER_BG)
    header_font = _font(26, bold=True)
    draw.text((PADDING, 20), "WAREHOUSE LABEL", font=header_font, fill=HEADER_FG)
    draw.text(
        (LABEL_W - PADDING, 20),
        "WAREHOUSE LABEL",
        font=_font(14),
        fill=MUTED_COLOR,
        anchor="ra",
    )

    qr_data = json.dumps({
        "sku": sku,
        "sender": sender,
        "recipient": recipient,
        "contents": contents,
        "weight_kg": weight_kg,
        "destination": destination,
        "routing_zone": routing_zone,
        "created_at": created_at.isoformat()
    }, ensure_ascii=False)
    
    qr_img = qrcode.make(qr_data).resize((QR_SIZE, QR_SIZE), Image.LANCZOS)
    img.paste(qr_img, (QR_X, QR_Y))

    # Generate and draw 1D Barcode (Code128) below QR code WITHOUT resizing
    # Resizing a 1D barcode with LANCZOS destroys the lines and makes it unscannable!
    writer = ImageWriter()
    writer_options = {
        'write_text': True, 
        'module_height': 5.0, 
        'quiet_zone': 2.0
    }
    barcode_class = Code128(sku, writer=writer)
    barcode_img = barcode_class.render(writer_options=writer_options)
    
    bw, bh = barcode_img.size
    barcode_x = RIGHT_COL_X + (RIGHT_COL_W - bw) // 2
    img.paste(barcode_img, (barcode_x, QR_Y + QR_SIZE + 16))

    label_font = _font(13)
    value_font = _font(15, bold=True)

    fields = [
        ("SKU", sku),
        ("Routing Zone", routing_zone),
        ("Sender", sender),
        ("Recipient", recipient),
        ("Contents", contents),
        ("Weight", f"{weight_kg} kg"),
        ("Destination", destination),
        ("Created At", created_at.strftime("%Y-%m-%d %H:%M")),
    ]

    text_x = PADDING
    text_y = HEADER_H + PADDING
    row_h = 60

    for label_text, value_text in fields:
        draw.text((text_x, text_y), label_text.upper(), font=label_font, fill=MUTED_COLOR)
        draw.text((text_x, text_y + 18), value_text, font=value_font, fill=TEXT_COLOR)
        draw.line(
            [(text_x, text_y + row_h - 4), (RIGHT_COL_X - PADDING, text_y + row_h - 4)],
            fill=DIVIDER_COLOR,
            width=1,
        )
        text_y += row_h

    draw.line(
        [(RIGHT_COL_X - PADDING // 2, HEADER_H + PADDING), (RIGHT_COL_X - PADDING // 2, LABEL_H - PADDING)],
        fill=DIVIDER_COLOR,
        width=1,
    )

    draw.rectangle([(0, LABEL_H - 6), (LABEL_W, LABEL_H)], fill=ACCENT_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
