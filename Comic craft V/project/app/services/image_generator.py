from pathlib import Path
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont
from huggingface_hub import InferenceClient

from app.config import settings


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PANEL_DIR = BASE_DIR / "static" / "panels"

PANEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# SAFE FILE NAME
# ============================================================

def _safe_name(value: str) -> str:

    value = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value,
    )

    value = value.strip("_")

    return value[:80] or "panel"


# ============================================================
# LOAD FONT SAFELY
# ============================================================

def _load_font(size: int, bold: bool = False):

    possible_fonts = []

    if bold:
        possible_fonts.extend([
            "arialbd.ttf",
            "Arial Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    else:
        possible_fonts.extend([
            "arial.ttf",
            "Arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ])

    for font_path in possible_fonts:

        try:

            return ImageFont.truetype(
                font_path,
                size,
            )

        except Exception:
            pass

    # Pillow fallback
    try:

        return ImageFont.load_default(
            size=size
        )

    except Exception:

        return ImageFont.load_default()


# ============================================================
# FALLBACK IMAGE
# ============================================================

def _fallback_image(
    prompt: str,
    filename: str,
) -> Path:

    width = settings.image_width
    height = settings.image_height

    # --------------------------------------------------------
    # Create image
    # --------------------------------------------------------

    img = Image.new(
        "RGB",
        (width, height),
        "#dff3ff",
    )

    draw = ImageDraw.Draw(img)

    # --------------------------------------------------------
    # Border
    # --------------------------------------------------------

    draw.rectangle(
        (
            20,
            20,
            width - 20,
            height - 20,
        ),
        outline="#126782",
        width=6,
    )

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    title_font = _load_font(
        28,
        bold=True,
    )

    body_font = _load_font(
        18,
        bold=False,
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title = "ComicCraft - Image Fallback"

    draw.text(
        (45, 45),
        title,
        fill="#123456",
        font=title_font,
    )

    # --------------------------------------------------------
    # Prepare prompt
    # --------------------------------------------------------

    body = str(prompt)

    # Remove excessive whitespace.

    body = " ".join(
        body.split()
    )

    # Limit the amount of text.

    body = body[:500]

    # --------------------------------------------------------
    # WRAP TEXT
    #
    # This fixes:
    #
    # "Not enough horizontal space to render
    #  a single character"
    # --------------------------------------------------------

    max_chars_per_line = 55

    wrapped_lines = textwrap.wrap(
        body,
        width=max_chars_per_line,
        break_long_words=True,
        break_on_hyphens=False,
    )

    # Keep only the first few lines.

    wrapped_lines = wrapped_lines[:10]

    wrapped_text = "\n".join(
        wrapped_lines
    )

    # --------------------------------------------------------
    # Draw prompt
    # --------------------------------------------------------

    draw.multiline_text(
        (45, 110),
        wrapped_text,
        fill="#123456",
        font=body_font,
        spacing=8,
    )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    footer = (
        "Image generation fallback - "
        "configure Hugging Face to generate artwork."
    )

    footer_lines = textwrap.wrap(
        footer,
        width=65,
    )

    footer_text = "\n".join(
        footer_lines
    )

    draw.multiline_text(
        (45, height - 90),
        footer_text,
        fill="#126782",
        font=body_font,
        spacing=5,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    path = PANEL_DIR / filename

    img.save(
        path,
        format="PNG",
    )

    return path


# ============================================================
# GENERATE IMAGE
# ============================================================

def generate_image(
    image_prompt: str,
    panel_number: int,
) -> str:

    filename = (
        f"panel_{panel_number:02d}_"
        f"{_safe_name(image_prompt[:50])}.png"
    )

    output_path = PANEL_DIR / filename

    # --------------------------------------------------------
    # Check provider
    # --------------------------------------------------------

    if settings.image_provider.lower() != "huggingface":

        if settings.allow_image_fallback:

            fallback_path = _fallback_image(
                image_prompt,
                filename,
            )

            return (
                "/static/panels/"
                + fallback_path.name
            )

        raise RuntimeError(
            "Unsupported IMAGE_PROVIDER: "
            f"{settings.image_provider}"
        )

    # --------------------------------------------------------
    # Check Hugging Face token
    # --------------------------------------------------------

    if not settings.hf_token:

        print(
            "HF_TOKEN is not configured."
        )

        if settings.allow_image_fallback:

            fallback_path = _fallback_image(
                image_prompt,
                filename,
            )

            return (
                "/static/panels/"
                + fallback_path.name
            )

        raise RuntimeError(
            "HF_TOKEN is not configured."
        )

    # --------------------------------------------------------
    # Hugging Face generation
    # --------------------------------------------------------

    try:

        print()
        print(
            "=" * 60
        )

        print(
            f"Generating image for panel "
            f"{panel_number}"
        )

        print(
            f"Image model: "
            f"{settings.image_model}"
        )

        print(
            "=" * 60
        )

        client = InferenceClient(
            provider="auto",
            api_key=settings.hf_token,
        )

        image = client.text_to_image(

            prompt=image_prompt,

            model=settings.image_model,

            width=settings.image_width,

            height=settings.image_height,

            num_inference_steps=settings.image_steps,

            guidance_scale=settings.image_guidance,
        )

        image.save(
            output_path,
            format="PNG",
        )

        print(
            f"SUCCESS: Image generated "
            f"for panel {panel_number}"
        )

        return (
            "/static/panels/"
            + output_path.name
        )

    # --------------------------------------------------------
    # Image provider failed
    # --------------------------------------------------------

    except Exception as exc:

        print(
            f"Hugging Face image generation "
            f"failed for panel {panel_number}: "
            f"{exc}"
        )

        if settings.allow_image_fallback:

            print(
                "Using ComicCraft fallback image."
            )

            fallback_path = _fallback_image(
                image_prompt,
                filename,
            )

            return (
                "/static/panels/"
                + fallback_path.name
            )

        raise RuntimeError(
            "Hugging Face image generation failed: "
            f"{exc}"
        ) from exc