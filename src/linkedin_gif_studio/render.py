from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import DraftPackage, PairManifest, StoryboardSpec


CANVAS = 1080
FPS = 10


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _wrapped(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), candidate, font=font)
        if box[2] - box[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _make_frame(
    storyboard: StoryboardSpec,
    frame_index: int,
    progress: float,
    brand_name: str,
    background: str,
    foreground: str,
    accent: str,
) -> Image.Image:
    image = Image.new("RGB", (CANVAS, CANVAS), _hex(background))
    draw = ImageDraw.Draw(image)
    fg = _hex(foreground)
    accent_rgb = _hex(accent)
    small = _font(28, bold=True)
    headline = _font(74, bold=True)
    body = _font(32)

    draw.text((72, 64), brand_name.upper(), font=small, fill=fg)
    draw.rounded_rectangle((72, 130, 1008, 138), radius=4, fill=accent_rgb)
    draw.text((72, 178), storyboard.concept, font=body, fill=fg)

    current = storyboard.frames[frame_index]
    lines = _wrapped(draw, current.on_screen_words, headline, 850)
    line_height = 92
    block_height = len(lines) * line_height
    y = 470 - block_height // 2
    opacity = max(0.25, math.sin(min(1, progress) * math.pi / 2))
    animated = tuple(round(channel * opacity + _hex(background)[i] * (1 - opacity)) for i, channel in enumerate(fg))
    for line in lines:
        draw.text((96, y), line, font=headline, fill=animated)
        y += line_height

    bar_width = int(850 * min(1, progress * 1.4))
    draw.rounded_rectangle((96, 720, 96 + bar_width, 738), radius=9, fill=accent_rgb)
    draw.text((96, 780), current.visual_change, font=body, fill=fg)
    draw.text((72, 1000), f"{frame_index + 1:02d} / {len(storyboard.frames):02d}", font=small, fill=accent_rgb)
    return image


def render_storyboard(
    storyboard: StoryboardSpec,
    output_dir: str | Path,
    brand_name: str = "AI Native Studio",
    background: str = "#F7F4E9",
    foreground: str = "#101820",
    accent: str = "#3157D5",
) -> tuple[Path, Path]:
    if not storyboard.approved:
        raise ValueError("Storyboard must be approved before rendering")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    durations: list[int] = []
    for index, item in enumerate(storyboard.frames):
        count = max(10, round(item.duration_seconds * FPS))
        for step in range(count):
            frames.append(
                _make_frame(
                    storyboard,
                    index,
                    step / max(1, count - 1),
                    brand_name,
                    background,
                    foreground,
                    accent,
                )
            )
            durations.append(round(1000 / FPS))
    gif_path = output / "infographic.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    png_path = output / "fallback.png"
    frames[-1].save(png_path, format="PNG", optimize=True)
    return gif_path, png_path


def write_pair_package(
    draft: DraftPackage,
    storyboard: StoryboardSpec,
    output_root: str | Path = "outputs",
    review_complete: bool = False,
    limitations: list[str] | None = None,
    brand_name: str = "AI Native Studio",
) -> tuple[Path, PairManifest]:
    if not draft.ready_for_visual:
        raise ValueError("Draft and claim must be approved and warning-free")
    if not storyboard.approved:
        raise ValueError("Storyboard must be approved")
    output = Path(output_root) / draft.post_id
    output.mkdir(parents=True, exist_ok=True)
    (output / "post.txt").write_text(draft.post_text, encoding="utf-8")
    storyboard_md = [f"# {storyboard.concept}", ""]
    for index, frame in enumerate(storyboard.frames, start=1):
        storyboard_md.extend(
            [
                f"## Frame {index}",
                f"- On-screen words: {frame.on_screen_words}",
                f"- Visual change: {frame.visual_change}",
                f"- Duration: {frame.duration_seconds:.1f} seconds",
                f"- Transition: {frame.transition}",
                "",
            ]
        )
    (output / "storyboard.md").write_text("\n".join(storyboard_md), encoding="utf-8")
    (output / "alt-text.txt").write_text(storyboard.alt_text, encoding="utf-8")
    render_storyboard(storyboard, output, brand_name=brand_name)
    files = {
        "post": "post.txt",
        "storyboard": "storyboard.md",
        "gif": "infographic.gif",
        "fallback": "fallback.png",
        "alt_text": "alt-text.txt",
        "manifest": "manifest.json",
    }
    manifest = PairManifest(
        post_id=draft.post_id,
        source_references=draft.sources,
        voice_profile_version=draft.voice_profile_version,
        model_name=draft.model_name,
        post_approved=draft.post_approved,
        claim_approved=draft.claim_approved,
        storyboard_approved=storyboard.approved,
        review_complete=review_complete,
        limitations=limitations or [],
        files=files,
    )
    (output / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return output, manifest

