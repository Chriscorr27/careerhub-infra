import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

def convert_txt_to_pdf(txt_path: str):
    """Converts a plain text file to PDF, handling text wrapping."""
    temp_pdf_path = txt_path.replace(".txt", ".pdf")
    doc = SimpleDocTemplate(temp_pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            story.append(Paragraph(line.strip(), styles["Normal"]))

    doc.build(story)

    # read bytes
    with open(temp_pdf_path, "rb") as pdf_file:
        input_pdf_bytes = pdf_file.read()

    return input_pdf_bytes

def create_watermark(watermark_text, page_width, page_height):
    """Generates a temporary PDF in memory perfectly sized to the current page."""
    packet = io.BytesIO()

    # 1. Match the exact dimensions of the target page
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # 2. Dynamically calculate font size (e.g., 10% of the page width)
    dynamic_font_size = int(page_width * 0.10)

    c.setFont("Helvetica-Bold", dynamic_font_size)
    c.setFillColorRGB(0.5, 0.5, 0.5)  # Gray
    c.setFillAlpha(0.3)               # 30% Opacity

    # 3. Move to the exact mathematical center of this specific page
    c.translate(page_width / 2, page_height / 2)
    c.rotate(45)

    # 4. Draw text at the new center (0, 0)
    c.drawCentredString(0, 0, watermark_text)

    c.save()
    packet.seek(0)

    return PdfReader(packet).pages[0]

def process_pdf_watermark(input_pdf_bytes, watermark_text):
    """Iterates through the PDF, applying the dynamically sized watermark to each page."""
    reader = PdfReader(io.BytesIO(input_pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        # Get dimensions of the current page
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Generate a perfectly sized watermark for this page
        watermark_page = create_watermark(watermark_text, page_width, page_height)

        # Overlay the watermark on top of the original page
        page.merge_page(watermark_page)
        writer.add_page(page)

    # Return the finalized PDF as bytes for S3 upload
    output_packet = io.BytesIO()
    writer.write(output_packet)
    return output_packet.getvalue()

def apply_watermark(input_path, output_pdf_path, watermark_text="CONFIDENTIAL"):
    """Reads the input file, applies the watermark to each page, and saves the output."""
    # 1. Read File
    if input_path.endswith(".pdf"):
        # Read the original PDF and watermark image into memory as bytes ('rb' = read binary)
        with open(input_path, "rb") as pdf_file:
                input_pdf_bytes = pdf_file.read()
    elif input_path.endswith(".txt"):
        # 1. Convert the original Txt to PDF and read as bytes ('rb' = read binary)
        input_pdf_bytes = convert_txt_to_pdf(input_path)

    # 2. Pass the bytes to your function
    modified_pdf_bytes = process_pdf_watermark(input_pdf_bytes, watermark_text)

    # 3. Save the returned bytes to a new local file ('wb' = write binary)
    with open(output_pdf_path, "wb") as output_file:
        output_file.write(modified_pdf_bytes)

    print(f"Successfully saved to {output_pdf_path}")