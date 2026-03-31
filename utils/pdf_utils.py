import fitz
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def open_pdf(pdf_path):
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(str(path))
        logger.info(f"Opened PDF: {path.name} ({doc.page_count} pages)")
        return doc
    except Exception as e:
        raise ValueError(f"Cannot open PDF '{path.name}': {e}")

def extract_images_from_pdf(
    doc,
    source_name,
    output_dir,
    min_width=100,
    min_height=100
):
    images = extract_images(doc, source_name, output_dir)
    pages = extract_text_by_page(doc, source_name)
    return map_images_to_context(pages, images)

    
def extract_text_by_page(doc, source_name):
    pages = []

    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text("text")

        pages.append({
            "page": page_num + 1,
            "text": text.strip(),
            "source": source_name
        })

    return pages


def extract_images(doc, source_name, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    images = []
    counter = 0

    for page_num in range(doc.page_count):
        page = doc[page_num]
        for img in page.get_images(full=True):
            xref = img[0]

            try:
                base = doc.extract_image(xref)
                width = base["width"]
                height = base["height"]

                # Skip noise images
                if width < 100 or height < 100:
                    continue

                counter += 1
                image_id = f"{source_name}_img_{counter:03d}"
                ext = base["ext"]
                path = output_dir / f"{image_id}.{ext}"

                path.write_bytes(base["image"])

                images.append({
                    "image_id": image_id,
                    "path": str(path),
                    "page": page_num + 1,
                    "width": width,
                    "height": height,
                    "source": source_name
                })

            except Exception as e:
                logger.warning(f"Image extraction failed: {e}")

    return images


def map_images_to_context(pages, images):
    mapped = []

    for img in images:
        page_text = next(
            (p["text"] for p in pages if p["page"] == img["page"]),
            ""
        )

        context = page_text[:300] if page_text else "Not Available"

        mapped.append({
            **img,
            "context_text": context
        })

    return mapped


def render_full_pages(doc, source_name, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered = []

    for i in range(doc.page_count):
        path = output_dir / f"{source_name}_page_{i+1}.png"

        mat = fitz.Matrix(2, 2)
        pix = doc[i].get_pixmap(matrix=mat)
        pix.save(str(path))

        rendered.append({
            "image_id": f"{source_name}_page_{i+1}",
            "path": str(path),
            "page": i + 1,
            "type": "full_page",
            "source": source_name
        })

    return rendered


def process_pdf(pdf_path, source_name, output_dir, render_pages=False):
    doc = open_pdf(pdf_path)

    pages = extract_text_by_page(doc, source_name)
    images = extract_images(doc, source_name, output_dir)

    # Add full-page images for thermal reports
    if render_pages:
        images.extend(render_full_pages(doc, source_name, output_dir))

    mapped_images = map_images_to_context(pages, images)

    return {
        "source": source_name,
        "pages": pages,
        "images": mapped_images
    }   