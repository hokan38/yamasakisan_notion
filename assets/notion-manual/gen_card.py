# -*- coding: utf-8 -*-
"""料理レシピの図解カード画像を生成する"""
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
W, H = 1600, 1200
H_MAX = 2600
NAVY   = (27, 42, 74)
CREAM  = (245, 239, 224)
GOLD   = (201, 162, 39)
RED    = (139, 42, 42)
INK    = (43, 43, 43)
SUB    = (110, 100, 85)
WHITE  = (255, 255, 255)
PANEL  = (252, 249, 242)

CAT_COLOR = {
    "すぐ出る一品": (46, 125, 74), "冷奴シリーズ": (40, 90, 150), "サラダ": (46, 125, 74),
    "おすすめ一品": (196, 108, 30), "鉄板料理": (160, 45, 45), "卵焼き": (198, 150, 20),
    "オムレツ": (198, 150, 20), "お好み焼き": (120, 78, 40), "焼きそば": (120, 78, 40),
    "ご飯もの": (120, 78, 40), "揚げ物": (108, 62, 140), "デザート": (190, 90, 130),
    "仕込み": (95, 95, 95),
}

def f(sz, ):
    return ImageFont.truetype(FONT, sz)

def wrap(draw, text, font, maxw):
    """日本語向け：1文字ずつ幅を測って折り返す"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        t = cur + ch
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = ch
    if cur:
        lines.append(cur)
    return lines

def fit_font(draw, text, maxw, start, minimum=34):
    sz = start
    while sz > minimum and draw.textlength(text, font=f(sz)) > maxw:
        sz -= 2
    return f(sz)

def split_steps(text):
    if not text:
        return []
    out = []
    for raw in text.replace("<br>", "\n").split("\n"):
        s = raw.strip()
        if not s:
            continue
        # 先頭の①②③/番号記号を外す
        for mark in "①②③④⑤⑥⑦⑧⑨⑩":
            if s.startswith(mark):
                s = s[1:].strip()
                break
        out.append(s)
    return out

def split_items(text):
    if not text:
        return []
    out = []
    for raw in text.replace("<br>", "\n").split("\n"):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("【"):
            m = s.find("】")
            if m != -1:
                out.append(("head", s[:m + 1]))
                s = s[m + 1:].strip()
                if not s:
                    continue
        for part in s.split("、"):
            p = part.strip()
            if p:
                out.append(("item", p))
    return out

def make_card(d, path):
    img = Image.new("RGB", (W, H_MAX), CREAM)
    dr = ImageDraw.Draw(img)
    cat = d.get("カテゴリー") or "その他"
    accent = CAT_COLOR.get(cat, NAVY)

    # ---- ヘッダー ----
    dr.rectangle([0, 0, W, 190], fill=NAVY)
    dr.rectangle([0, 186, W, 194], fill=GOLD)
    name = d["料理名"]
    nf = fit_font(dr, name, W - 520, 92, 46)
    dr.text((70, 95), name, font=nf, fill=WHITE, anchor="lm")
    # カテゴリバッジ
    bf = f(40)
    bw = dr.textlength(cat, font=bf) + 60
    dr.rounded_rectangle([W - bw - 70, 58, W - 70, 132], radius=37, fill=accent)
    dr.text((W - 70 - bw / 2, 95), cat, font=bf, fill=WHITE, anchor="mm")
    if d.get("新人必修") == "__YES__":
        sf = f(30)
        tw = dr.textlength("新人必修", font=sf) + 44
        dr.rounded_rectangle([W - bw - 70 - tw - 20, 70, W - bw - 90, 120], radius=25,
                             fill=None, outline=GOLD, width=3)
        dr.text((W - bw - 70 - tw / 2 - 20, 95), "新人必修", font=sf, fill=GOLD, anchor="mm")

    # ---- メタ情報（分量・加熱時間・皿）----
    y = 232
    metas = []
    if d.get("分量"):      metas.append(("分量", d["分量"]))
    if d.get("加熱時間"):  metas.append(("加熱", d["加熱時間"]))
    if d.get("使用する皿"): metas.append(("皿", d["使用する皿"]))
    if metas:
        mf, mlf = f(32), f(30)
        x = 70
        for label, val in metas:
            txt = f"{label}：{val}"
            tw = dr.textlength(txt, font=mf) + 44
            if x + tw > W - 70:
                break
            dr.rounded_rectangle([x, y, x + tw, y + 62], radius=14, fill=(236, 228, 210))
            dr.text((x + 22, y + 31), txt, font=mf, fill=SUB, anchor="lm")
            x += tw + 18
        y += 92

    # ---- 2カラム（材料 / 作り方）----
    col_gap = 40
    left_w = 560
    right_x = 70 + left_w + col_gap
    right_w = W - right_x - 70
    top = y

    # 材料パネル
    items = split_items(d.get("材料"))
    hf, itf = f(40), f(33)
    ly = top
    dr.rectangle([70, ly, 70 + left_w, ly + 66], fill=accent)
    dr.text((70 + 22, ly + 33), "材料", font=hf, fill=WHITE, anchor="lm")
    ly += 66
    panel_top = ly
    ly += 22
    if items:
        for kind, txt in items:
            if kind == "head":
                for ln in wrap(dr, txt, f(31), left_w - 60):
                    dr.text((70 + 26, ly), ln, font=f(31), fill=accent)
                    ly += 42
                continue
            lines = wrap(dr, txt, itf, left_w - 76)
            dr.ellipse([70 + 28, ly + 15, 70 + 42, ly + 29], fill=GOLD)
            for i, ln in enumerate(lines):
                dr.text((70 + 58, ly), ln, font=itf, fill=INK)
                ly += 46
            ly += 6
    else:
        dr.text((70 + 28, ly), "（レシピ未登録）", font=itf, fill=SUB)
        ly += 46
    dr.rectangle([70, panel_top, 70 + left_w, max(ly + 14, panel_top + 60)],
                 outline=(222, 212, 192), width=3)

    # 作り方パネル
    steps = split_steps(d.get("調理手順"))
    ry = top
    dr.rectangle([right_x, ry, right_x + right_w, ry + 66], fill=NAVY)
    dr.text((right_x + 22, ry + 33), "作り方", font=hf, fill=WHITE, anchor="lm")
    ry += 66
    rpanel_top = ry
    ry += 24
    stf = f(34)
    if steps:
        for i, s in enumerate(steps, 1):
            dr.ellipse([right_x + 26, ry + 2, right_x + 74, ry + 50], fill=accent)
            dr.text((right_x + 50, ry + 26), str(i), font=f(30), fill=WHITE, anchor="mm")
            for ln in wrap(dr, s, stf, right_w - 130):
                dr.text((right_x + 92, ry), ln, font=stf, fill=INK)
                ry += 48
            ry += 12
    else:
        dr.text((right_x + 30, ry), "（レシピ未登録・社員が追記してください）",
                font=stf, fill=SUB)
        ry += 48
    dr.rectangle([right_x, rpanel_top, right_x + right_w, max(ry + 14, rpanel_top + 60)],
                 outline=(222, 212, 192), width=3)

    # ---- 下部：盛り付け・注意点・アレルギー ----
    by = max(ly, ry) + 40
    notes = []
    if d.get("盛り付け・トッピング"):
        notes.append(("盛り付け", d["盛り付け・トッピング"], GOLD))
    if d.get("注意点・よくある失敗"):
        notes.append(("注意", d["注意点・よくある失敗"], RED))
    if d.get("アレルギー"):
        notes.append(("アレルギー", d["アレルギー"], RED))
    nf2 = f(31)
    for label, val, col in notes:
        txt = f"{label}：{val}"
        lines = wrap(dr, txt, nf2, W - 190)[:2]
        h = 26 + 42 * len(lines)
        dr.rectangle([70, by, W - 70, by + h], fill=PANEL)
        dr.rectangle([70, by, 78, by + h], fill=col)
        yy = by + 13
        for ln in lines:
            dr.text((100, yy), ln, font=nf2, fill=INK)
            yy += 42
        by += h + 14

    # ---- コンテンツ高さでトリミングしてからフッターを描く ----
    content_bottom = by + 24
    total = max(int(content_bottom) + 56, 900)
    img = img.crop((0, 0, W, total))
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, total - 56, W, total], fill=NAVY)
    dr.text((70, total - 28), "お好み焼ダイニング ぽぱい｜料理マニュアル",
            font=f(26), fill=(206, 196, 176), anchor="lm")
    dr.text((W - 70, total - 28), cat, font=f(26), fill=GOLD, anchor="rm")
    img.save(path, quality=92)

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    for i, d in enumerate(data):
        make_card(d, os.path.join(outdir, f"{d['slug']}.jpg"))
    print(f"generated {len(data)} cards")
