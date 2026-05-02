# FundStudyGuide — Claude Instructions

## Project Purpose
Generate HTML study guides from nursing/medical textbook PDFs, one guide per chapter, organized by book.

---

## Infrastructure (already set up)

- **Python 3.12** installed
- **PyMuPDF** (`fitz`) installed via pip
- **Extraction script**: `extract_pages.py` at the project root (works with any PDF)

---

## Directory Structure

```
FundStudyGuide/
  extract_pages.py        # PDF extraction script (book-agnostic)
  books.json              # Registry: all books, offsets, completed chapters
  books/
    fundamentals-nursing/ # One folder per book slug
      chapter42_study_guide.html
    <new-book-slug>/
      chapter<N>_study_guide.html
```

PDFs live in `C:\Users\logan\Projects\FundStudyGuide\` alongside this repo but are excluded from git via `.gitignore`.

---

## Adding a New Book

### 1. Determine the page offset
The PDF page index ≠ book page number because of front-matter pages. Run a probe:
```powershell
python extract_pages.py <PdfFile.pdf> 1 3 probe_raw.txt
```
Read `probe_raw.txt` and look for the actual page number printed on page 1 of the book body. The offset = PDF page index − book page number. Delete `probe_raw.txt` when done.

### 2. Register the book in books.json
Add an entry to the `books` array:
```json
{
  "slug": "short-kebab-name",
  "title": "Full Book Title (Author)",
  "pdf": "FileName.pdf",
  "page_offset": <offset>,
  "notes": "how offset was determined",
  "completed_chapters": []
}
```

### 3. Create the book folder
```powershell
New-Item -ItemType Directory -Path "books\<slug>"
```

---

## Workflow for Each New Chapter

### 1. Look up the book in books.json
Find the book's `slug` and `page_offset`.

### 2. Calculate PDF page range
```
pdf_start = book_page + page_offset
```
Extract a couple of pages at the expected end to confirm where the chapter ends.

### 3. Extract chapter text
```powershell
python extract_pages.py <PdfFile.pdf> <pdf_start> <pdf_end> chapter<N>_raw.txt
```

### 4. Read extracted text
Read `chapter<N>_raw.txt` in chunks with the Read tool (offset 0 through end, ~300 lines at a time for large chapters).

### 5. Generate HTML study guide
Output: `books/<slug>/chapter<N>_study_guide.html`

Use `books/fundamentals-nursing/chapter42_study_guide.html` as the format template. Every guide must include:
- **Collapsible sections** using native `<details>`/`<summary>` HTML (no JavaScript)
- **Blue gradient summary bars** with ▼/▲ toggle indicators; Section 1 open by default, rest collapsed
- **Proper chemical formula markup**: `<sub>` and `<sup>` tags — never raw HTML entities like `&sub2;`
  - Examples: `Na<sup>+</sup>`, `K<sup>+</sup>`, `Ca<sup>2+</sup>`, `HCO<sub>3</sub><sup>-</sup>`, `CO<sub>2</sub>`, `H<sub>2</sub>O`
- **NCLEX Critical To Knows** section at the end with red-themed cards (`#c0392b`) — 6–10 high-yield cards
- **Expandable Q&A review questions** using inner `<details class="qa">` elements
- Fully self-contained (inline CSS, no external dependencies)

### 6. Record completion in books.json
Add the completed chapter to the book's `completed_chapters` array.

### 7. Delete the raw text file
`chapter<N>_raw.txt` is an intermediate file — delete it after the guide is generated. It is already gitignored.

### 8. Commit and push
```powershell
git add books/<slug>/chapter<N>_study_guide.html books.json
git commit -m "Add <BookTitle> Chapter <N> study guide"
git push
```

---

## Known Books & Offsets

See `books.json` for the authoritative registry. Quick reference:

| Slug | PDF File | Page Offset |
|------|----------|-------------|
| fundamentals-nursing | FundamentalsNursing.pdf | +20 |

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
