#!/usr/bin/env python3
"""Build the self-contained KURA press brief: inline fonts, logos, renders; stamp gate hash."""
import base64, hashlib, json, os, sys

SP = os.path.dirname(os.path.abspath(__file__))
ACCESS_CODE = os.environ.get('KURA_CODE', 'kura2029')  # lowercase; confirmed by Lior 23 Jul 2026

def b64(path, mime):
    with open(path, 'rb') as f:
        return f'data:{mime};base64,' + base64.b64encode(f.read()).decode()

def b64_trim(path):
    """Trim transparent border to the alpha bounding box so CSS sizing is predictable,
    then return a base64 PNG data URI. Used for the v2 brand assets, which ship with
    generous transparent padding."""
    from PIL import Image
    import io
    im = Image.open(path).convert('RGBA')
    bbox = im.getchannel('A').getbbox()
    if bbox:
        im = im.crop(bbox)
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

# slide order mirrors the kura3d site, estate removed
SLIDES = [
    ('outdoor-pool.jpg',            'Pool & Gardens', 'Seasonal Outdoor Pool',   'Water, shade and the afternoon light.', False),
    ('entrance-hall-reception.jpg', 'Arrival',        'Welcoming Hall',          'Arrival, unhurried.', False),
    ('piano-bar-lounge.jpg',        'Bar & Lounge',   'Piano Lounge',            'Firelight, ceramics, a slow evening.', False),
    ('chef-restaurant.jpg',         'Dining',         'Chef Restaurant',         'The harvest sets the menu each morning.', False),
    ('spa-indoor-pool.jpg',         'Spa',            'Spa Indoor Pool',         'Three shades of stone, firelight, a skylight.', False),
    ('treatment-room.jpg',          'Spa',            'Treatment Rooms',         'Six rooms of quiet ritual.', True),
    ('outdoor-lounge.jpg',          'The Land',       'Vineyards Experience',    'Between harvest and renewal.', True),
    ('view-over-guest-rooms.jpg',   'Rooms',          'Guest Rooms',             'Terraced into the hillside, facing the valley.', False),
    ('guest-room.jpg',              'Rooms',          'Standard Guest Room',     'A room built for winter.', False),
]

html = open(f'{SP}/src/index.template.html').read()

# fonts
html = html.replace('{{F_LORA}}',     b64(f'{SP}/fonts/lora-400.woff2',  'font/woff2'))
html = html.replace('{{F_LORA_I}}',   b64(f'{SP}/fonts/lora-400i.woff2', 'font/woff2'))
html = html.replace('{{F_LATO_300}}', b64(f'{SP}/fonts/lato-300.woff2',  'font/woff2'))
html = html.replace('{{F_LATO_400}}', b64(f'{SP}/fonts/lato-400.woff2',  'font/woff2'))

# logos — KURA brand pack v2 (July 2026), parchment variants for dark backgrounds.
# Symbol/wordmark used small in the nav and as the quote mark; the full lockup
# (symbol + KURA + DOURO VALLEY · PORTUGAL) carries the centred gate/hero/footer.
html = html.replace('{{L_SYMBOL}}',   b64_trim(f'{SP}/assets/kura-symbol-parchment.png'))
html = html.replace('{{L_WORDMARK}}', b64_trim(f'{SP}/assets/kura-wordmark-parchment.png'))
html = html.replace('{{L_LOCKUP}}',   b64_trim(f'{SP}/assets/kura-lockup-parchment.png'))
html = html.replace('{{L_BOA}}',      b64(f'{SP}/assets/boa-brandname-white.png','image/png'))

# favicon — new three-arc symbol (parchment) centred on a schist tile
from PIL import Image as _Img
_sym = _Img.open(f'{SP}/assets/kura-symbol-parchment.png').convert('RGBA')
_bb = _sym.getchannel('A').getbbox()
if _bb: _sym = _sym.crop(_bb)
_fav = _Img.new('RGBA', (64, 64), (28, 23, 20, 255))  # schist
_w = 46
_h = max(1, round(_sym.height * _w / _sym.width))
_sym = _sym.resize((_w, _h), _Img.LANCZOS)
_fav.alpha_composite(_sym, ((64 - _w) // 2, (64 - _h) // 2))
_favpath = f'{SP}/img/_favicon-v2.png'
_fav.save(_favpath, 'PNG')
html = html.replace('{{FAVICON}}',    b64(_favpath, 'image/png'))

# hero background — pre-darkened so the page needs no CSS filters (filters break capture/compositing)
from PIL import Image, ImageEnhance
hero_src = f'{SP}/img/view-over-guest-rooms.jpg'
hero_out = f'{SP}/img/_hero-dark.jpg'
im = Image.open(hero_src).convert('RGB')
im = ImageEnhance.Color(im).enhance(0.72)
im = ImageEnhance.Brightness(im).enhance(0.30)
im.save(hero_out, 'JPEG', quality=70, progressive=True, optimize=True)
html = html.replace('{{IMG_HERO}}', b64(hero_out, 'image/jpeg'))

# carousel slides
from PIL import ImageFilter
slides_html, captions = [], []
for fn, label, name, note, fit in SLIDES:
    uri = b64(f'{SP}/img/{fn}', 'image/jpeg')
    cls = ' fit' if fit else ''
    blur = ''
    if fit:
        # pre-blurred darkened backdrop, baked (no CSS filters)
        bim = Image.open(f'{SP}/img/{fn}').convert('RGB')
        bim.thumbnail((120, 120), Image.LANCZOS)
        bim = bim.filter(ImageFilter.GaussianBlur(6))
        bim = ImageEnhance.Brightness(bim).enhance(0.45)
        bim = ImageEnhance.Color(bim).enhance(0.8)
        bpath = f'{SP}/img/_blur-{fn}'
        bim.save(bpath, 'JPEG', quality=60)
        blur = f'<div class="blur" style="background-image:url({b64(bpath, "image/jpeg")})"></div>'
    slides_html.append(f'<div class="slide{cls}">{blur}<img src="{uri}" alt="{name}" loading="lazy"></div>')
    captions.append([label, name, note])
html = html.replace('{{SLIDES}}', ''.join(slides_html))
html = html.replace('{{CAPTIONS}}', json.dumps(captions, ensure_ascii=False))

# gate hash
html = html.replace('{{GATE_HASH}}', hashlib.sha256(ACCESS_CODE.lower().encode()).hexdigest())

out = f'{SP}/index.html'
open(out, 'w').write(html)
print(f'built {out}  {os.path.getsize(out)/1e6:.1f} MB  code={ACCESS_CODE}')
