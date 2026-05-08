"""
Crop specific Ch46 figures from the Lewis Med-Surg PDF using
manually measured bounding boxes (PDF points, 72dpi coordinate space).
Page size is 612 x 783 points.
Usage: python crop_ch46_targeted.py <pdf_path> <out_dir> [dpi]
"""
import fitz, sys, os

pdf_path = sys.argv[1]
out_dir  = sys.argv[2]
dpi      = int(sys.argv[3]) if len(sys.argv) > 3 else 220
os.makedirs(out_dir, exist_ok=True)

pdf  = fitz.open(pdf_path)
mat  = fitz.Matrix(dpi / 72, dpi / 72)

# (fig_key, pdf_page, x0, y0, x1, y1)  — PDF point coords (72 dpi, top-left origin)
targets = [
    # Fig 46.1  – brain/CTZ vomiting diagram  (left portion, bottom of page 1086)
    ("fig46_01", 1086,   0, 490, 320, 783),
    # Fig 46.3  – esophagitis with ulcers      (upper-right, page 1093)
    ("fig46_03", 1093, 310,  30, 615, 295),
    # Fig 46.6  – esophageal diverticula sites (right column, page 1100)
    ("fig46_06", 1100, 310,  55, 615, 340),
    # Fig 46.9  – peptic ulcer types (acute/chronic cross-section, page 1102 mid)
    ("fig46_09", 1102,  30, 415, 615, 640),
    # Fig 46.10 – gastric & duodenal ulcer sites (page 1102 lower, wider crop)
    ("fig46_10", 1102, 100, 625, 615, 785),
    # Fig 46.13 – EGD endoscopy illustration (upper-right, page 1104)
    ("fig46_13", 1104, 310,  20, 615, 330),
    # Fig 46.14 – perforated duodenal ulcer (right side, below drug table, page 1106)
    ("fig46_14", 1106, 315, 155, 615, 360),
    # Fig 46.15 – stomach cancer cells in wall (lower-left, page 1109)
    ("fig46_15", 1109,   0, 545, 315, 783),
    # Fig 46.16 – Billroth I & II procedures  (right column only, page 1110)
    ("fig46_16", 1110, 310,  85, 615, 640),
    # Fig 46.2  – GERD pathogenesis diagram   (upper-right, page 1092)
    ("fig46_02", 1092, 300,  10, 612, 290),
    # Fig 46.4  – Sliding + rolling hiatal hernia A/B (lower, page 1096)
    ("fig46_04", 1096,   0, 580, 612, 783),
    # Fig 46.5  – Nissen fundoplication A/B   (upper, page 1097)
    ("fig46_05", 1097,   0,  10, 612, 295),
]

for key, page_num, x0, y0, x1, y1 in targets:
    page = pdf[page_num - 1]
    rect = fitz.Rect(x0, y0, x1, y1)
    pix  = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
    fname = f"{key}_p{page_num}.png"
    fpath = os.path.join(out_dir, fname)
    pix.save(fpath)
    print(f"  {key}  page {page_num}  {pix.width}x{pix.height}px  -> {fname}")

pdf.close()
print("\nDone.")
