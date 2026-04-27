import os
import base64
import fitz  # PyMuPDF
from pathlib import Path


OCR_THRESHOLD_CHARS = 50  # pages with fewer native chars trigger OCR


class OcrProcessor:
    def __init__(self, client: "ResilientClient", model: str | None = None):
        """
        client: ResilientClient pointing to VertexAI Proxy
        model: e.g. "gemini-2.5-flash" (from OCR_MODEL env var)
        """
        self.client = client
        self.model = model or os.environ.get("OCR_MODEL", "gemini-2.5-flash")

    def ocr_page(self, page: fitz.Page) -> str:
        """
        If page has enough native text, return it directly.
        Otherwise: render at 300 DPI → PNG → base64 → Gemini multimodal call.
        """
        native_text = page.get_text().strip()
        if len(native_text) >= OCR_THRESHOLD_CHARS:
            return native_text

        # Render page to PNG at 300 DPI
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        b64 = base64.b64encode(png_bytes).decode()

        prompt = (
            "Extract all text from this document page. Return only the text, preserving structure."
        )
        return self.client.chat_multimodal(
            model=self.model,
            text_prompt=prompt,
            image_b64=b64,
            image_mime="image/png",
        )

    def ocr_image(self, path: Path) -> str:
        """OCR a standalone image file (JPG, PNG, etc.)."""
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        suffix = path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        mime = mime_map.get(suffix, "image/jpeg")
        prompt = "Extract all text from this document page. Return only the text, preserving structure."
        return self.client.chat_multimodal(model=self.model, text_prompt=prompt, image_b64=b64, image_mime=mime)