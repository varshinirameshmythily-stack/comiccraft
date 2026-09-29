from app.models import ComicOutline, ComicStory, PromptRequest
from app.services.gemini_client import get_gemini_client
from app.config import settings
from google.genai import types

def generate_story(request: PromptRequest, outline: ComicOutline) -> ComicStory:
    client = get_gemini_client()

    outline_text = outline.model_dump_json(indent=2)

    prompt = f"""
Turn this comic outline into polished panel-by-panel comic narration.

User inputs:
Story idea: {request.story_prompt}
Main character: {request.character_name}
Setting: {request.setting}
Tone: {request.tone}
Art style: {request.art_style}

Outline:
{outline_text}

Requirements:
- Return exactly {settings.panels_count} panels.
- Preserve panel numbers and titles from the outline.
- Keep character behavior and story continuity consistent.
- scene_description should be concise and visual.
- caption should be a short ambient/comic caption.
- narration should advance the story.
- dialogue should contain natural dialogue and may include multiple speakers.
- Match the requested tone without making the story excessively long.
"""

    response = client.models.generate_content(
        model=settings.gemini_pro_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ComicStory,
            temperature=0.9,
            max_output_tokens=7000,
        ),
    )

    if getattr(response, "parsed", None):
        story = response.parsed
    else:
        story = ComicStory.model_validate_json(response.text)

    if len(story.panels) != settings.panels_count:
        raise RuntimeError(
            f"Gemini returned {len(story.panels)} story panels; expected {settings.panels_count}."
        )
    return story
