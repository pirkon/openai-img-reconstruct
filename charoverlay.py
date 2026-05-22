#!/usr/bin/env python3
"""
charoverlay.py — Batch-replaces the subject in input photos with a custom
character reference, using Claude for scene analysis and gpt-image-2 for generation.

Workflow per image:
  1. Claude analyzes the input image and writes a detailed scene prompt.
  2. gpt-image-2 receives that prompt + the character reference to generate output.

Usage:
    python charoverlay.py [--size 1024x1024] [--quality high]
"""

import argparse
import base64
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from openai import BadRequestError, OpenAI

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

ANALYSIS_SYSTEM_PROMPT = """\
You are an expert image analyst and creative director specializing in photorealistic AI image generation.

Your job is to analyze a photograph and write a generation prompt that allows an image model to recreate the scene exactly — but with a different person as the subject.

The prompt you write will be sent to GPT-Image-2 along with a character reference image. GPT-Image-2 places that character into the scene you describe.

IMPORTANT RULES to avoid content moderation false positives:
- Never mention the gender, age, or physical attributes of the original subject.
- Never use words associated with bedroom furniture or bedroom contexts (avoid: daybed, bed, mattress, lingerie, intimate, bedroom). Instead describe a sofa as "upholstered settee", "modern lounge sofa", "plush couch", etc.
- Keep all clothing descriptions modest and fully clothed — describe garments as complete outfits.
- Describe poses in neutral, athletic or fashion-editorial terms (e.g. "relaxed seated posture", "leaning casually", "confident upright stance").

Your prompt must cover ALL of the following in rich, precise detail:

- Scene & setting: location, environment, time of day, season, indoor/outdoor
- Lighting: quality (soft/harsh/diffused), direction, color temperature, shadows, highlights
- Clothing & outfit: every garment, color, fabric, fit, accessories, shoes, style
- Pose & body language: exact stance, limb positions, gesture, expression, energy — described in neutral fashion/editorial terms
- Background & props: what is visible behind and around the subject, depth, elements
- Photographic style: (e.g. candid lifestyle, editorial fashion, moody portrait, golden-hour outdoor, street photography)
- Image quality & aesthetic: sharpness, depth of field, film grain or digital clean, color grading, mood

End the prompt with: "The subject is the person from the reference image provided. Preserve their exact face, hair, and physical identity while placing them into this scene."

Output ONLY the generation prompt — no headers, labels, explanations, or preamble.\
"""

SAFETY_PREFIX = (
    "Safe-for-work fully clothed lifestyle and fashion photograph. "
    "No nudity, no revealing clothing, no sexual content. "
)



def encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def media_type(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/jpeg")


def analyze_scene(client: anthropic.Anthropic, image_path: Path) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type(image_path),
                            "data": encode_image(image_path),
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analyze this photo and write the generation prompt. "
                            "Describe everything about the scene precisely so it can be fully recreated. "
                            "Do not describe or reference the actual person in the image — only the scene, setting, lighting, clothing, pose, and style."
                        ),
                    },
                ],
            }
        ],
    )
    return message.content[0].text.strip()


def generate_image(
    client: OpenAI,
    prompt: str,
    character_path: Path,
    output_path: Path,
    size: str,
    quality: str,
) -> None:
    safe_prompt = SAFETY_PREFIX + prompt
    with open(character_path, "rb") as char_file:
        result = client.images.edit(
            model="gpt-image-2",
            image=[char_file],
            prompt=safe_prompt,
            size=size,
            quality=quality,
        )

    image_bytes = base64.b64decode(result.data[0].b64_json)
    with open(output_path, "wb") as f:
        f.write(image_bytes)


def find_character(character_dir: Path) -> Path:
    images = sorted([p for p in character_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTS])
    if not images:
        sys.exit(f"Error: No image found in {character_dir}/. Add one character reference image.")
    if len(images) > 1:
        print(f"Note: Multiple images in /character — using: {images[0].name}")
    return images[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace the subject in photos with a character reference using Claude + gpt-image-2."
    )
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="Output dimensions: 1024x1024, 1536x1024, or 1024x1536 (default: 1024x1024)",
    )
    parser.add_argument(
        "--quality",
        default="high",
        choices=["low", "medium", "high", "auto"],
        help="Output quality (default: high)",
    )
    parser.add_argument(
        "--save-prompts",
        action="store_true",
        help="Save generated Claude prompts as .txt files alongside outputs",
    )
    args = parser.parse_args()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY not set. Add it to your .env file.")
    if not openai_key:
        sys.exit("Error: OPENAI_API_KEY not set. Add it to your .env file.")

    base = Path(__file__).parent
    input_dir = base / "input"
    character_dir = base / "character"
    output_dir = base / "output"

    for d, label in [(input_dir, "input"), (character_dir, "character")]:
        if not d.exists():
            sys.exit(f"Error: /{label} directory not found.")

    output_dir.mkdir(exist_ok=True)

    character_path = find_character(character_dir)
    input_images = sorted([p for p in input_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTS])

    if not input_images:
        sys.exit("Error: No images found in /input. Add images to process.")

    anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
    openai_client = OpenAI(api_key=openai_key)

    print(f"Character: {character_path.name}")
    print(f"Images to process: {len(input_images)}")
    print(f"Output size: {args.size}  Quality: {args.quality}\n")

    for i, input_path in enumerate(input_images, 1):
        stem = input_path.stem
        output_path = output_dir / f"{stem}_output.png"

        print(f"[{i}/{len(input_images)}] {input_path.name}")
        print("  Analyzing scene with Claude...")

        prompt = analyze_scene(anthropic_client, input_path)

        preview = prompt[:140].replace("\n", " ")
        print(f"  Prompt preview: {preview}...")

        if args.save_prompts:
            prompt_path = output_dir / f"{stem}_prompt.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            print(f"  Prompt saved: {prompt_path.name}")

        print("  Generating with gpt-image-2...")
        try:
            generate_image(openai_client, prompt, character_path, output_path, args.size, args.quality)
            print(f"  Saved: {output_path.name}\n")
        except BadRequestError as e:
            print(f"  SKIPPED — OpenAI rejected the request: {e}\n")

    print(f"Done. {len(input_images)} image(s) saved to /output/")


if __name__ == "__main__":
    main()
