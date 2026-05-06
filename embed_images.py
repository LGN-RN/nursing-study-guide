"""
Replaces image src paths in an HTML file with base64 data URIs,
making the HTML fully self-contained.
Usage: python embed_images.py <html_file>
"""
import sys
import re
import base64
import os

html_path = sys.argv[1]
html_dir = os.path.dirname(os.path.abspath(html_path))

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

def replace_src(m):
    src = m.group(1)
    if src.startswith("data:"):
        return m.group(0)
    img_path = os.path.join(html_dir, src.replace("/", os.sep))
    if not os.path.exists(img_path):
        print(f"  MISSING: {img_path}")
        return m.group(0)
    ext = os.path.splitext(img_path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "svg": "image/svg+xml"}.get(ext.lstrip("."), "image/png")
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    size_kb = len(b64) * 3 // 4 // 1024
    print(f"  Embedded {src} ({size_kb} KB)")
    return f'src="data:{mime};base64,{b64}"'

new_content = re.sub(r'src="([^"]+)"', replace_src, content)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Done. Output: {html_path}")
