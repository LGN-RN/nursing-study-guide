# FundStudyGuide — Claude Instructions

## Project Purpose
Generate HTML study guides from `FundamentalsNursing.pdf` (Potter & Perry), one per chapter.

---

## Infrastructure (already set up)

- **Python 3.12** installed
- **PyMuPDF** (`fitz`) installed via pip
- **Extraction script**: `extract_pages.py` in this directory
- **PDF page offset**: +20 (PDF page = book page + 20)

---

## Workflow for Each New Chapter

### 1. Calculate PDF page range
```
pdf_start = book_page + 20
```
Probe a few pages beyond the expected end to find where the chapter ends.

### 2. Extract chapter text
```powershell
python extract_pages.py FundamentalsNursing.pdf <pdf_start> <pdf_end> chapter<N>_raw.txt
```

### 3. Read extracted text
Read `chapter<N>_raw.txt` in chunks using the Read tool (offset 0 through ~6000+ lines depending on chapter length).

### 4. Generate HTML study guide
Output: `chapter<N>_study_guide.html`

Use `chapter42_study_guide.html` as the format template. Every guide must include:
- **13 collapsible sections** using native `<details>`/`<summary>` HTML (no JavaScript)
- **Blue gradient summary bars** with ▼/▲ toggle indicators; Section 1 open by default, rest collapsed
- **Proper chemical formula markup**: `<sub>` and `<sup>` tags — never raw HTML entities like `&sub2;`
  - Examples: `Na<sup>+</sup>`, `K<sup>+</sup>`, `Ca<sup>2+</sup>`, `HCO<sub>3</sub><sup>-</sup>`, `CO<sub>2</sub>`, `H<sub>2</sub>O`
- **Section 13: NCLEX Critical To Knows** with red-themed cards (`#c0392b`) — 6–10 high-yield cards
- **Expandable Q&A review questions** using inner `<details class="qa">` elements
- Fully self-contained (inline CSS, no external dependencies)

---

## Completed Chapters

| Chapter | Book Page | PDF Pages | Output File |
|---------|-----------|-----------|-------------|
| 42 — Fluid, Electrolyte, Acid-Base Balance | 1042 | 1062–1124 | `chapter42_study_guide.html` |

---

## extract_pages.py Reference

```python
# Usage: python extract_pages.py <pdf> <start_pdf_page> <end_pdf_page> <output_file>
import sys
import fitz

def extract(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)
    text = []
    for i in range(start_page - 1, min(end_page, len(doc))):
        page = doc[i]
        text.append(f"\n--- PDF Page {i+1} ---\n")
        text.append(page.get_text())
    return "\n".join(text)

if __name__ == "__main__":
    pdf = sys.argv[1]
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    out_file = sys.argv[4] if len(sys.argv) > 4 else "extracted.txt"
    content = extract(pdf, start, end)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Extracted pages {start}-{end} to {out_file}")
```
