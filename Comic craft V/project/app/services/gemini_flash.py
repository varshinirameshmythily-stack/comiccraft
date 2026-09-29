import time

from google.genai import types

from app.models import ComicOutline, PromptRequest
from app.services.gemini_client import get_gemini_client
from app.config import settings


# ============================================================
# CHECK WHETHER GEMINI ERROR IS TEMPORARY
# ============================================================

def _is_temporary_error(exc: Exception) -> bool:

    message = str(exc).lower()

    temporary_errors = (
        "503",
        "unavailable",
        "high demand",
        "overloaded",
        "temporarily",
        "timeout",
        "timed out",
        "deadline exceeded",
        "429",
        "resource_exhausted",
    )

    return any(
        error in message
        for error in temporary_errors
    )


# ============================================================
# SEND REQUEST TO GEMINI
# ============================================================

def _generate_with_model(
    client,
    model_name: str,
    prompt: str,
):

    return client.models.generate_content(

        model=model_name,

        contents=prompt,

        config=types.GenerateContentConfig(

            response_mime_type="application/json",

            response_schema=ComicOutline,

            temperature=0.8,

            max_output_tokens=5000,
        ),
    )


# ============================================================
# GENERATE COMIC OUTLINE
# ============================================================

def generate_outline(
    request: PromptRequest,
) -> ComicOutline:

    client = get_gemini_client()

    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    prompt = f"""
Create a cohesive {settings.panels_count}-panel comic outline.

User story idea:
{request.story_prompt}

Main character:
{request.character_name}

Setting:
{request.setting}

Tone:
{request.tone}

Art style:
{request.art_style}

Requirements:

1. Return exactly {settings.panels_count} panels.

2. Keep the same main character and visual identity
   across all panels.

3. The story must contain:

   - beginning
   - development
   - turning point
   - ending

4. Every panel must contain:

   - panel_number
   - title
   - scene_description
   - narration
   - dialogue
   - image_prompt

5. Every image_prompt must describe ONE illustration.

6. Do NOT create a collage.

7. Do NOT put written text inside the image.

8. Do NOT put captions inside the image.

9. Do NOT put speech bubbles inside the image.

10. Do NOT put logos or watermarks inside the image.

11. Describe:

   - character appearance
   - character action
   - environment
   - camera framing
   - lighting
   - art style

12. Maintain visual continuity between panels.

13. Keep the story suitable for a comic.

14. Keep each panel description concise.
"""

    # --------------------------------------------------------
    # MODEL ORDER
    # --------------------------------------------------------
    #
    # We start with the model from .env.
    # Then use lightweight available models.
    #
    # This avoids repeatedly waiting on one overloaded model.
    # --------------------------------------------------------

    models_to_try = [

        settings.gemini_flash_model,

        "gemini-3.5-flash-lite",

        "gemini-3.1-flash-lite",

        "gemini-2.5-flash-lite",

        "gemini-flash-lite-latest",

        "gemini-2.5-flash",

    ]

    # Remove duplicates while preserving order.

    models_to_try = list(
        dict.fromkeys(models_to_try)
    )

    last_error = None

    # --------------------------------------------------------
    # TRY EACH MODEL
    # --------------------------------------------------------

    for model_name in models_to_try:

        print()
        print("=" * 60)
        print(
            f"Trying Gemini outline model: "
            f"{model_name}"
        )
        print("=" * 60)

        # ----------------------------------------------------
        # ONLY TWO ATTEMPTS
        # ----------------------------------------------------

        for attempt in range(2):

            try:

                print(
                    f"Gemini outline request: "
                    f"{model_name} "
                    f"(attempt {attempt + 1}/2)"
                )

                response = _generate_with_model(
                    client,
                    model_name,
                    prompt,
                )

                # ------------------------------------------------
                # CHECK RESPONSE
                # ------------------------------------------------

                if getattr(
                    response,
                    "parsed",
                    None
                ):

                    outline = response.parsed

                else:

                    if not response.text:

                        raise RuntimeError(
                            "Gemini returned an empty response."
                        )

                    outline = (
                        ComicOutline
                        .model_validate_json(
                            response.text
                        )
                    )

                # ------------------------------------------------
                # VALIDATE PANEL COUNT
                # ------------------------------------------------

                if len(outline.panels) != settings.panels_count:

                    raise RuntimeError(
                        f"Gemini returned "
                        f"{len(outline.panels)} panels; "
                        f"expected "
                        f"{settings.panels_count}."
                    )

                # ------------------------------------------------
                # SUCCESS
                # ------------------------------------------------

                print()
                print(
                    "SUCCESS: Comic outline generated "
                    f"using {model_name}"
                )
                print()

                return outline

            except Exception as exc:

                last_error = exc

                print(
                    f"Gemini outline error from "
                    f"{model_name}: {exc}"
                )

                # ------------------------------------------------
                # PERMANENT ERROR
                # ------------------------------------------------

                if not _is_temporary_error(exc):

                    raise

                # ------------------------------------------------
                # TEMPORARY ERROR
                # ------------------------------------------------

                if attempt == 0:

                    print(
                        "Temporary Gemini error."
                    )

                    print(
                        "Waiting 2 seconds before retry..."
                    )

                    time.sleep(2)

                else:

                    print(
                        f"Second attempt failed "
                        f"for {model_name}."
                    )

        # ----------------------------------------------------
        # MOVE TO NEXT MODEL
        # ----------------------------------------------------

        print(
            f"Model {model_name} failed."
        )

        print(
            "Trying the next available model..."
        )

    # --------------------------------------------------------
    # ALL MODELS FAILED
    # --------------------------------------------------------

    raise RuntimeError(
        "Gemini could not generate the comic outline.\n\n"
        "Models attempted:\n"
        + "\n".join(
            f"- {model}"
            for model in models_to_try
        )
        + "\n\n"
        f"Last error: {last_error}"
    )