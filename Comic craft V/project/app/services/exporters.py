from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from PIL import Image

from app.models import ComicLayoutItem

BASE_DIR = Path(__file__).resolve().parents[2]
EXPORT_DIR = BASE_DIR / "static" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

class ComicPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.cell(0, 10, "ComicCraft - AI Comic Story", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)

def _safe_text(value: str) -> str:
    # Helvetica in a standard PDF has limited Unicode coverage.
    return value.encode("latin-1", "replace").decode("latin-1")

def save_pdf(layout: list[ComicLayoutItem], title: str = "ComicCraft Comic") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comic_{timestamp}.pdf"
    output = EXPORT_DIR / filename

    pdf = ComicPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    for panel in layout:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 17)
        pdf.multi_cell(0, 9, _safe_text(f"Panel {panel.panel_number}: {panel.title}"))
        pdf.ln(2)

        image_file = BASE_DIR / panel.image_path.lstrip("/").replace("/", "/")
        if image_file.exists():
            with Image.open(image_file) as im:
                w, h = im.size
            max_w, max_h = 180, 105
            scale = min(max_w / w, max_h / h)
            draw_w, draw_h = w * scale, h * scale
            x = (210 - draw_w) / 2
            pdf.image(str(image_file), x=x, y=pdf.get_y(), w=draw_w, h=draw_h)
            pdf.ln(draw_h + 6)

        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 6, _safe_text(panel.scene_description))
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, _safe_text("Caption"))
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _safe_text(panel.caption))
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, _safe_text("Narration"))
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _safe_text(panel.narration))
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, _safe_text("Dialogue"))
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _safe_text(panel.dialogue))

    pdf.output(str(output))
    return f"/static/exports/{output.name}"
