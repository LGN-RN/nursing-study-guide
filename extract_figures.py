"""
Smart figure extractor for two-column nursing textbook PDFs (Lewis Med-Surg et al.)

Replaces: crop_figures.py, crop_figures2.py, crop_figures_ch46.py,
          crop_ch46_targeted.py, extract_fig_images.py

Algorithm
---------
1. Scan each page for "Fig. <chapter>.<num>" caption text.
2. Classify each figure's column layout (full-width / left / right) from the
   caption x-position relative to the page midpoint.
3. Find the top of each figure by looking for the highest text block ABOVE the
   caption that falls within the same column — the figure lives between that
   block's bottom edge and the caption.
4. If the page contains an embedded JPEG covering that region (clinical photos),
   extract it directly; otherwise render+crop the page region.
5. Write <out_dir>/figures_manifest.json with metadata for every figure found.

Usage
-----
  python extract_figures.py <pdf> <chapter_num> <start_page> <end_page> <out_dir> [--dpi 150]

Output
------
  <out_dir>/fig_<ch>_<num>_p<page>.<ext>   one image per figure
  <out_dir>/figures_manifest.json
"""

import argparse
import json
import os
import re
import sys

import fitz  # PyMuPDF


# ── helpers ──────────────────────────────────────────────────────────────────

def col_bounds(cap_x0, cap_x1, page_w):
    """Return (x_left, x_right) crop bounds based on caption position."""
    cap_span = cap_x1 - cap_x0
    cap_mid  = (cap_x0 + cap_x1) / 2
    midpoint = page_w / 2

    # Caption wider than 55 % of page → almost certainly full-width figure
    if cap_span > page_w * 0.55:
        return 0, page_w

    gap = 22  # pts of overlap so we don't clip column edges
    if cap_mid < midpoint - 20:          # clearly left column
        return 0, midpoint + gap
    elif cap_mid > midpoint + 20:        # clearly right column
        return midpoint - gap, page_w
    else:                                # straddling midpoint → full width
        return 0, page_w


def figure_top(page, cap_y, x_left, x_right):
    """
    Walk text blocks upward from the caption to find where the figure starts.
    Returns the y-coordinate of the figure's top edge.
    """
    blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,block_no,block_type)
    best_bottom = 0  # default: start of page

    for blk in blocks:
        bx0, by0, bx1, by1 = blk[0], blk[1], blk[2], blk[3]
        block_type = blk[6] if len(blk) > 6 else 0
        if block_type != 0:          # skip image blocks in the text stream
            continue
        if by1 > cap_y - 8:         # block overlaps or is below caption
            continue
        # Block must substantially overlap with the figure's column
        overlap_w = min(bx1, x_right) - max(bx0, x_left)
        col_w = x_right - x_left
        if overlap_w < col_w * 0.25: # < 25 % overlap → different column
            continue
        if by1 > best_bottom:
            best_bottom = by1

    return best_bottom + 2  # 2-pt buffer below the limiting text block


def find_embedded_jpeg(page, fig_x0, fig_y0, fig_x1, fig_y1, pdf):
    """
    Return (xref, img_bytes, ext) if there is a large embedded JPEG inside
    the figure bounding box, else None.
    """
    try:
        img_infos = page.get_image_info(xrefs=True)
    except AttributeError:
        return None  # older PyMuPDF — skip

    best = None
    best_area = 0

    for info in img_infos:
        bbox = info.get("bbox") or info.get("rect")
        if bbox is None:
            continue
        bx0, by0, bx1, by1 = bbox

        # Check overlap with figure region
        ox = min(bx1, fig_x1) - max(bx0, fig_x0)
        oy = min(by1, fig_y1) - max(by0, fig_y0)
        if ox <= 0 or oy <= 0:
            continue

        xref = info.get("xref", 0)
        if not xref:
            continue

        try:
            base = pdf.extract_image(xref)
        except Exception:
            continue

        # Only take JPEG (clinical photos); skip tiny icons / decorations
        if base["ext"] not in ("jpeg", "jpg"):
            continue
        if base["width"] < 200 or base["height"] < 200:
            continue

        area = ox * oy
        if area > best_area:
            best_area = area
            best = (xref, base["image"], base["ext"])

    return best


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Smart figure extractor for nursing textbook PDFs")
    parser.add_argument("pdf",         help="Path to the PDF file")
    parser.add_argument("chapter_num", help="Chapter number (e.g. 47)")
    parser.add_argument("start_page",  type=int, help="First PDF page to scan (1-based)")
    parser.add_argument("end_page",    type=int, help="Last PDF page to scan (inclusive, 1-based)")
    parser.add_argument("out_dir",     help="Output directory for images and manifest")
    parser.add_argument("--dpi",       type=int, default=150, help="DPI for rendered crops (default 150)")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    ch = args.chapter_num
    fig_pattern = re.compile(rf"Fig\.?\s*{re.escape(ch)}\.(\d+)", re.IGNORECASE)

    pdf = fitz.open(args.pdf)
    scale = args.dpi / 72
    mat = fitz.Matrix(scale, scale)

    manifest = {}   # fig_num → metadata dict

    for page_idx in range(args.start_page - 1, min(args.end_page, len(pdf))):
        page     = pdf[page_idx]
        page_num = page_idx + 1
        page_w   = page.rect.width
        page_h   = page.rect.height
        words    = page.get_text("words")

        # ── find captions ────────────────────────────────────────────────────
        found_captions = {}  # fig_num → (x0, y0, x1, y1)
        for i in range(len(words)):
            window = " ".join(w[4] for w in words[i:i+5])
            m = fig_pattern.search(window)
            if not m:
                continue
            fig_num = int(m.group(1))
            if fig_num in found_captions:
                continue
            span = words[i:i+5]
            found_captions[fig_num] = (
                min(w[0] for w in span),
                min(w[1] for w in span),
                max(w[2] for w in span),
                max(w[3] for w in span),
            )

        # ── extract each figure ──────────────────────────────────────────────
        for fig_num, (cx0, cy0, cx1, cy1) in found_captions.items():
            # Column classification
            xl, xr = col_bounds(cx0, cx1, page_w)

            # Figure vertical bounds
            top    = figure_top(page, cy0, xl, xr)
            bottom = min(page_h, cy1 + 80)   # include caption + short description

            fig_rect = fitz.Rect(
                max(0, xl),
                max(0, top),
                min(page_w, xr),
                bottom,
            )

            # Try embedded JPEG first (clinical photos)
            jpeg_result = find_embedded_jpeg(page, xl, top, xr, cy1, pdf)

            if jpeg_result:
                xref, img_bytes, ext = jpeg_result
                fname = f"fig_{ch}_{fig_num:02d}_p{page_num}.{ext}"
                fpath = os.path.join(args.out_dir, fname)
                with open(fpath, "wb") as f:
                    f.write(img_bytes)
                method = "embedded-raster"
            else:
                pix   = page.get_pixmap(matrix=mat, clip=fig_rect, alpha=False)
                fname = f"fig_{ch}_{fig_num:02d}_p{page_num}.png"
                fpath = os.path.join(args.out_dir, fname)
                pix.save(fpath)
                method = "rendered"

            manifest[fig_num] = {
                "file":    fname,
                "page":    page_num,
                "method":  method,
                "col":     "left" if xr < page_w * 0.6 else ("right" if xl > page_w * 0.4 else "full"),
                "rect":    [round(xl,1), round(top,1), round(xr,1), round(bottom,1)],
                "alt":     f"Fig. {ch}.{fig_num}",
                "placeholder": f"<!-- FIG_{ch}_{fig_num:02d} -->",
            }
            print(f"  p{page_num} Fig {ch}.{fig_num:02d} [{method}] → {fname}")

    pdf.close()

    manifest_path = os.path.join(args.out_dir, "figures_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nExtracted {len(manifest)} figures → {args.out_dir}")
    print(f"Manifest: {manifest_path}")
    print("\nAdd these placeholder comments to your HTML where figures should appear:")
    for num in sorted(manifest):
        print(f"  {manifest[num]['placeholder']}  ({manifest[num]['file']})")


if __name__ == "__main__":
    main()
