"""Seed-pro viet prompt mockup: doc anh san pham + anh phu tro -> N prompt tieng Anh da dang.

Bê tu mockup-factory/providers.py, cat gon dung trong tam: chi giu phan "bo mockup
da dang & dep tu anh san pham + anh phu tro". Bo TM/variations/gemini/openai gen/chi phi.

Dung aiohttp (Studio da co san) — khong them httpx. Pillow chi de shrink anh cho re token;
thieu Pillow van chay (gui anh nguyen ban). Key ARK_KEY lay tu env hoac .env trong thu muc nay.
"""
import base64
import io
import os
import re

import aiohttp

ROOT = os.path.dirname(os.path.abspath(__file__))

# BytePlus Ark (OpenAI-compatible). Model viet prompt = Seed-2.0-pro (da phuong thuc, doc anh).
ARK_BASE_URL = os.environ.get("ARK_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3")
SEED_MODEL = os.environ.get("SEED_PROMPT_MODEL", "seed-2-0-pro-260328")


def load_env():
    """Nap .env trong thu muc Studio vao os.environ (chi key CHUA co san). Parser stdlib, khong them dep."""
    p = os.path.join(ROOT, ".env")
    try:
        with open(p, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except OSError:
        pass


def _ark_key():
    load_env()
    key = os.environ.get("ARK_KEY", "")
    if not key:
        raise RuntimeError("Thieu ARK_KEY — bo vao file .env trong thu muc Studio (ARK_KEY=...) hoac export ra env.")
    return key


def _data_uri(image_bytes, mime="image/jpeg"):
    return f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"


def _shrink(image_bytes, max_side=512):
    """Thu nho anh truoc khi dua vao vision -> it token hon, re + nhanh hon. Thieu Pillow -> tra nguyen ban."""
    try:
        from PIL import Image
    except ImportError:
        return image_bytes
    im = Image.open(io.BytesIO(image_bytes))
    im.thumbnail((max_side, max_side))
    if im.mode != "RGB":
        im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85)
    return out.getvalue()


def _split_prompts(text, count):
    """Tach text model tra ve thanh list prompt: moi dong 1 prompt, bo so thu tu/bullet + cau dan '...:'."""
    out = []
    for ln in text.splitlines():
        ln = re.sub(r"^\s*(?:[-*•]\s+|\d+[.)]\s+)", "", ln).strip()
        if not ln or ln.endswith(":"):
            continue
        out.append(ln)
    return out[:count]


def _build_multiref(n, ref_labels=None):
    """Day model gan vai Image 1..n. Image 1 = anh san pham chinh; Image 2..n dung nhan user neu co."""
    roles = []
    for k in range(1, n):  # Image 2..n
        lbl = ""
        if ref_labels and k - 1 < len(ref_labels):
            lbl = (ref_labels[k - 1] or "").strip()
        roles.append(f"Image {k + 1} is {lbl}" if lbl else f"Image {k + 1} is an extra reference")
    return (f" You are given {n} reference images labeled Image 1..Image {n} in order."
            " Image 1 is the main product/design. " + "; ".join(roles) + "."
            " Treat each label as authoritative — do NOT re-guess what an image is. When a prompt uses"
            " one, name it by its index (e.g. 'apply the fabric colour from Image 2'). Use ONLY the"
            " images provided; never invent references that aren't there, and only apply an extra"
            " reference when the user's request calls for it.")


# Khung huong dan mockup: model gen la model EDIT (da thay anh) -> NEO thiet ke, chi doi cach chup.
# Muc tieu: N anh DA DANG & DEP, moi anh 1 kieu chup khac han, giu dung vibe cua san pham.
MOCKUP_TASK = (
    "GOAL: a DIVERSE set of premium product-mockup photos of the SAME item — each prompt a genuinely"
    " DIFFERENT, beautiful shot, no two alike. The image generator already sees the reference, so DO"
    " NOT re-describe or alter the design, decoration, technique, shape, materials or colours — begin"
    " every prompt with 'Keep the exact product and its design, decoration and finish from the"
    " reference image unchanged.' Then vary ONLY the presentation, and spread the N prompts widely"
    " across: camera angle & distance (straight-on, 3/4, top-down flat-lay, low hero angle, tight"
    " macro detail, wide establishing), background/setting (clean seamless studio, coloured backdrop,"
    " natural surface like wood/stone/linen, lifestyle context that suits the product), and lighting"
    " & mood (soft diffused daylight, warm golden hour, bright high-key e-commerce, moody low-key with"
    " directional light). Aim for high-end commercial photography: realistic soft shadows and"
    " reflections, professional lighting, tasteful shallow depth of field, tidy editorial composition."
    " CRUCIAL — STAY ON-VIBE: first read the product's own aesthetic and mood from the reference"
    " (e.g. soft romantic wedding, minimal modern, rustic, playful kids). Every shot must share ONE"
    " coherent aesthetic that MATCHES that mood — a delicate wedding item stays elegant, soft and"
    " romantic in all shots; never swerve into edgy, quirky, neon, grunge or any styling that clashes"
    " with the product. Vary the SHOT, not the VIBE: the diversity is in angle/background/lighting"
    " within the product's own world, keeping props, colour palette and styling tasteful and on-brand."
    " ~30-55 words per prompt, concrete and photographic. If the user's request names a specific"
    " presentation, follow it and vary within it; if the request is silent, design the diverse premium"
    " set yourself. Never invent a human model or hands unless the request asks for one."
)

# Gen chay qua ChatGPT/codex (co safety filter) -> cam nhan hieu that de khoi bi reject.
_BRAND_RULE = (
    " NEVER name real brands, trademarks, franchises, characters, logos, celebrities, or specific real"
    " landmarks/parks (e.g. do NOT write 'Cinderella Castle', 'Disneyland', 'Eiffel Tower') — the safety"
    " filter rejects them. Use only GENERIC descriptions instead (e.g. 'a fairytale castle', 'a theme"
    " park', 'a famous tower')."
)

_REF_RULE = (
    " Before writing, silently inventory the reference: HOW MANY distinct products it shows, their"
    " layout/positions, and EACH product's decoration technique (printed, engraved, carved, embossed,"
    " etched, hand-painted). Respect ALL of that in every prompt — address each product by its clearest"
    " distinguishing trait, keep them all in one image, and NAME each product's technique explicitly"
    " (e.g. 'engraved into', 'printed on') so an engraving never turns into a flat print."
)


def _system_prompt(count, n_imgs, ref_labels):
    multiref = "" if n_imgs <= 1 else _build_multiref(n_imgs, ref_labels)
    return ("You write English prompts for an image-generation model. Look at the reference image and"
            f" the user's request, then output EXACTLY {count} distinct prompts." + _REF_RULE + multiref +
            " Format: one prompt per line, no numbering, no blank lines, no extra text — each line is"
            " ONE complete prompt with NO line breaks inside it." + _BRAND_RULE + " " + MOCKUP_TASK)


async def write_prompts(main_bytes, ref_images, request, count=6, ref_labels=None, max_side=512):
    """Vision: doc anh san pham (main) + anh phu tro (ref_images) + yeu cau -> N prompt mockup tieng Anh.

    Tra (prompts, model, tokens). tokens = {in, out} (co the 0 neu Ark khong bao usage).
    """
    key = _ark_key()
    imgs = ([_shrink(main_bytes, max_side)] + [_shrink(b, max_side) for b in (ref_images or [])])[:10]
    sys = _system_prompt(count, len(imgs), ref_labels)
    body = {
        "model": SEED_MODEL,
        "max_tokens": min(8000, 500 + count * 240),
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": [
                {"type": "text", "text": (request or "Create a diverse premium mockup set of this product.")},
                *({"type": "image_url", "image_url": {"url": _data_uri(b)}} for b in imgs)]},
        ],
    }
    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(f"{ARK_BASE_URL}/chat/completions",
                          headers={"Authorization": f"Bearer {key}"}, json=body) as r:
            txt = await r.text()
            if r.status >= 400:
                raise RuntimeError(f"Seed-pro {r.status}: {txt[:300]}")
            j = await r.json()
    prompts = _split_prompts(j["choices"][0]["message"]["content"], count)
    u = j.get("usage") or {}
    return prompts, SEED_MODEL, {"in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}


if __name__ == "__main__":
    # tach prompt: bo so thu tu/bullet + cau dan, giu so mo dau hop le, cat dung count
    assert _split_prompts("1. a red mug on wood\n2) a red mug at sunset\n- a red mug, studio\n", 5) == \
        ["a red mug on wood", "a red mug at sunset", "a red mug, studio"]
    assert _split_prompts("Here are 3 prompts:\nfirst prompt\nsecond prompt", 3) == ["first prompt", "second prompt"]
    assert _split_prompts("3D render of a mug\n1970s vintage kitchen\n2 cats on a sofa", 3) == \
        ["3D render of a mug", "1970s vintage kitchen", "2 cats on a sofa"]
    assert _split_prompts("p1\np2\np3\np4", 2) == ["p1", "p2"]
    # multiref: gan nhan user theo Image index, thieu nhan -> 'extra reference'
    _mr = _build_multiref(3, ["mau vai", "mau chi"])
    assert "Image 2 is mau vai" in _mr and "Image 3 is mau chi" in _mr, _mr
    assert "Image 3 is an extra reference" in _build_multiref(3, ["mau vai"])
    # system prompt: khoa thiet ke + da dang + giu vibe + cam nhan hieu (vi gen qua ChatGPT)
    _sys = _system_prompt(6, 2, None)
    assert "unchanged" in _sys and "DIVERSE" in _sys and "STAY ON-VIBE" in _sys, _sys
    assert "NEVER name real brands" in _sys and "Image 1 is the main product" in _sys
    print("OK seedprompt: tach prompt + multiref + system prompt")
