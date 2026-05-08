"""
Reads chapter46_study_guide.html, strips any existing base64 <img> tags
for fig46_XX placeholders, then embeds the correct PNG files as base64
data URIs at <!-- IMG:fig46_XX --> comments.
Usage: python embed_ch46.py
"""
import base64, os, re

html_path = r"books\lewis-medsurg\chapter46_study_guide.html"

ch46    = r"books\lewis-medsurg\images\ch46"
ch46_v2 = r"books\lewis-medsurg\images\ch46_v2"

# (fig_key, directory, filename)
picks = [
    ("fig46_01", ch46_v2, "fig46_01_p1086.png"),
    ("fig46_02", ch46_v2, "fig46_02_p1092.png"),
    ("fig46_03", ch46_v2, "fig46_03_p1093.png"),
    ("fig46_04", ch46_v2, "fig46_04_p1096.png"),
    ("fig46_05", ch46_v2, "fig46_05_p1097.png"),
    ("fig46_06", ch46_v2, "fig46_06_p1100.png"),
    ("fig46_07", ch46,    "fig_46_07_p1101.png"),
    ("fig46_08", ch46,    "fig_46_08_p1101.png"),
    ("fig46_09", ch46_v2, "fig46_09_p1102.png"),
    ("fig46_10", ch46_v2, "fig46_10_p1102.png"),
    ("fig46_11", ch46,    "fig_46_11_p1103.png"),
    ("fig46_12", ch46,    "fig_46_12_p1103.png"),
    ("fig46_13", ch46_v2, "fig46_13_p1104.png"),
    ("fig46_14", ch46_v2, "fig46_14_p1106.png"),
    ("fig46_15", ch46_v2, "fig46_15_p1109.png"),
    ("fig46_16", ch46_v2, "fig46_16_p1110.png"),
    ("fig46_17", ch46,    "fig_46_17_p1111.png"),
]

b64 = {}
for key, img_dir, fname in picks:
    fpath = os.path.join(img_dir, fname)
    if os.path.exists(fpath):
        with open(fpath, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        b64[key] = f"data:image/png;base64,{data}"
        print(f"  Encoded {key}: {len(data)//1024} KB")
    else:
        print(f"  MISSING: {fpath}")

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Strip any previously embedded base64 <img> tags back to placeholders
html = re.sub(
    r'<img src="data:image/png;base64,[^"]*"[^>]*alt="(fig46_\d+)"[^>]*>',
    lambda m: f"<!-- IMG:{m.group(1)} -->",
    html,
)
print("  Stripped old embedded images, restored placeholders")

# Embed new images
img_tag = '<img src="{uri}" style="max-width:78%;border-radius:6px;border:1px solid #c8d8ea;box-shadow:0 2px 8px rgba(13,59,102,.12);" alt="{key}">'
for key, uri in b64.items():
    placeholder = f"<!-- IMG:{key} -->"
    if placeholder in html:
        html = html.replace(placeholder, img_tag.format(uri=uri, key=key))
        print(f"  Inserted {key}")
    else:
        print(f"  No placeholder for {key}")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("\nDone. HTML updated.")
