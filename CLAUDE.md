# FundStudyGuide — Claude Instructions

## Project Purpose
Generate HTML study guides from nursing/medical textbook PDFs, one guide per chapter, organized by book.

---

## Infrastructure (already set up)

- **Python 3.12** installed
- **PyMuPDF** (`fitz`) installed via pip
- **Pipeline CLI**: `guide.py` — orchestrates the full chapter workflow (prepare → embed → finalize)
- **Figure extractor**: `extract_figures.py` — smart, column-aware figure extraction
- **CSS sync**: `sync_css.py` — keeps all guides' styles in sync with the template
- **Template**: `template/study_guide_base.html` — master HTML/CSS template for new guides

---

## Directory Structure

```
FundStudyGuide/
  guide.py                        # Pipeline CLI (replaces manual step-by-step)
  extract_figures.py              # Smart figure extractor
  extract_pages.py                # PDF text extraction
  sync_css.py                     # Push CSS updates to all guides
  books.json                      # Registry: all books, offsets, completed chapters
  template/
    study_guide_base.html         # Master CSS + HTML skeleton (copy for new chapters)
  books/
    fundamentals-nursing/
      chapter42_study_guide.html
    lewis-medsurg/
      chapter17_study_guide.html
      chapter46_study_guide.html
      chapter47_study_guide.html
      images/
        ch17/   ch46/   ch46_v2/   ch47/   # figure image files + figures_manifest.json
```

PDFs live at the project root but are excluded from git via `.gitignore`.

---

## Adding a New Book

### 1. Determine the page offset
```powershell
python extract_pages.py <PdfFile.pdf> 1 3 probe_raw.txt
```
Read `probe_raw.txt`, find the printed page number on page 1 of the book body.
`offset = PDF page index − book page number`. Delete `probe_raw.txt` when done.

### 2. Register the book in books.json
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

## Workflow for Each New Chapter  ← PRIMARY WORKFLOW

### Step 1 — Prepare (extract text + figures)
```powershell
python guide.py prepare <slug> <chapter> <book_start_page> <book_end_page>
```
Example:
```powershell
python guide.py prepare lewis-medsurg 48 1135 1178
```
This will:
- Calculate PDF page range automatically (book page + offset)
- Extract chapter text → `chapter<N>_raw.txt`
- Run the smart figure extractor → `books/<slug>/images/ch<N>/`
- Print a manifest of all figures found with their `<!-- FIG_N_NN -->` placeholder tags

### Step 2 — Generate the HTML
1. Read `chapter<N>_raw.txt` in ~300-line chunks.
2. Copy `template/study_guide_base.html` as your starting point.
3. Fill in all `<!-- FILL: ... -->` placeholder sections.
4. Where figures belong in the content, write the corresponding placeholder comment:
   ```html
   <!-- FIG_48_01 -->
   ```
   (Exact placeholders are listed at the end of the `prepare` output and in `figures_manifest.json`.)
5. Save as `books/<slug>/chapter<N>_study_guide.html`.

Every guide must include (all already in the template):
- **Collapsible sections** using native `<details>`/`<summary>` (no JavaScript)
- **Blue gradient summary bars** with ▼/▲ toggle; Section 1 open by default, rest collapsed
- **Close Section ▲ button** at the bottom of every section
- **Common Conditions & Pharmacology** table in each content section (`.pharma-box`)
- **NCLEX Critical To Know** section — 6–10 red-themed cards
- **Expandable Q&A review questions** using `<details class="qa">`
- **Proper chemical markup**: `<sub>` and `<sup>` tags — never raw HTML entities
  - Examples: `Na<sup>+</sup>`, `HCO<sub>3</sub><sup>-</sup>`, `CO<sub>2</sub>`, `H<sub>2</sub>O`
- **Fully self-contained**: inline CSS only, no external dependencies (preserves HTML preview)

### Step 3 — Embed figures
```powershell
python guide.py embed <slug> <chapter>
```
Finds every `<!-- FIG_N_NN -->` placeholder in the HTML and replaces it with an
inline base64 image. The guide remains fully self-contained after this step.

### Step 4 — Finalize (books.json + cleanup + commit)
```powershell
python guide.py finalize <slug> <chapter> \
  --title "Chapter Title Here" \
  --book-pages "1135-1178" \
  --pdf-pages "1170-1213" \
  --clean \
  --yes
```
Flags:
- `--clean` — deletes `chapter<N>_raw.txt` and the `images/ch<N>/` directory
- `--yes`   — runs `git add`, `git commit`, `git push` automatically
- Omit `--yes` to get the git commands printed instead of run

---

## CSS Updates (Idea 2 — consistency tool)

If you add a new CSS class or fix a style in `template/study_guide_base.html`:
```powershell
python sync_css.py             # updates ALL guides
python sync_css.py --dry-run   # preview only
python sync_css.py --file books/lewis-medsurg/chapter47_study_guide.html  # one file
```
This replaces the entire `<style>` block in each guide with the template's CSS.
Output remains self-contained — no external stylesheets.

---

## Figure Extraction Details (Idea 3 — smart extractor)

`extract_figures.py` (called automatically by `guide.py prepare`) detects:

| Layout | Detection method | Crop bounds |
|--------|-----------------|-------------|
| Left column | caption midpoint < page midpoint − 20 pt | x: 0 → page_mid + 22 |
| Right column | caption midpoint > page midpoint + 20 pt | x: page_mid − 22 → page_w |
| Full width | caption span > 55 % of page width | x: 0 → page_w |

For embedded JPEG photos (clinical images), the script extracts the raster
directly from the PDF rather than rendering the page. Diagrams and charts
(vector graphics) are rendered at the requested DPI (default 150).

Manual override: if auto-cropping is still wrong for a specific figure, edit
the manifest JSON and re-run `guide.py embed`.

---

## Known Books & Offsets

See `books.json` for the authoritative registry. Quick reference:

| Slug | PDF File | Page Offset |
|------|----------|-------------|
| fundamentals-nursing | FundamentalsNursing.pdf | +20 |
| lewis-medsurg | LEWIS'S MEDICAL-SURGICAL NURSING … .pdf | +35 |

---

## Legacy Scripts (kept for reference, no longer needed)

These one-off scripts still exist at the root but are superseded by the new tools:

| Script | Replaced by |
|--------|-------------|
| `crop_figures.py` | `extract_figures.py` |
| `crop_figures2.py` | `extract_figures.py` |
| `crop_figures_ch46.py` | `extract_figures.py` |
| `crop_ch46_targeted.py` | manual manifest edit + `guide.py embed` |
| `extract_fig_images.py` | `extract_figures.py` (embedded-raster detection) |
| `extract_images.py` | `extract_figures.py` |
| `embed_images.py` | `guide.py embed` |
| `embed_ch46.py` | `guide.py embed` |
| `render_pages.py` | kept — useful for visual inspection of PDF pages |
