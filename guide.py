"""
guide.py — Study guide pipeline CLI

Three subcommands orchestrate the full chapter workflow:

  prepare   Extract chapter text + figures from the PDF
  embed     Replace <!-- FIG_N_NN --> placeholders with base64 images
  finalize  Update books.json, clean temp files, commit

Typical session
---------------
  # Step 1: extract raw material
  python guide.py prepare lewis-medsurg 48 1088 1134

  # Step 2: Claude reads <slug>/chapter48_raw.txt and writes chapter48_study_guide.html
  #         Place <!-- FIG_48_01 --> comments where figures should appear.

  # Step 3: embed figures
  python guide.py embed lewis-medsurg 48

  # Step 4: wrap up
  python guide.py finalize lewis-medsurg 48 --clean --yes
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys


BOOKS_JSON = os.path.join(os.path.dirname(__file__), "books.json")
BOOKS_DIR  = os.path.join(os.path.dirname(__file__), "books")
PDF_DIR    = os.path.dirname(__file__)


# ── helpers ───────────────────────────────────────────────────────────────────

def load_books():
    with open(BOOKS_JSON, encoding="utf-8") as f:
        return json.load(f)

def save_books(data):
    with open(BOOKS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Updated {BOOKS_JSON}")

def find_book(data, slug):
    for book in data["books"]:
        if book["slug"] == slug:
            return book
    raise SystemExit(f"Book slug '{slug}' not found in books.json")

def book_dir(slug):
    return os.path.join(BOOKS_DIR, slug)

def img_dir(slug, chapter):
    return os.path.join(BOOKS_DIR, slug, "images", f"ch{chapter}")

def raw_txt(chapter):
    return os.path.join(os.path.dirname(__file__), f"chapter{chapter}_raw.txt")

def html_path(slug, chapter):
    return os.path.join(book_dir(slug), f"chapter{chapter}_study_guide.html")

def manifest_path(slug, chapter):
    return os.path.join(img_dir(slug, chapter), "figures_manifest.json")


# ── prepare ──────────────────────────────────────────────────────────────────

def cmd_prepare(args):
    data   = load_books()
    book   = find_book(data, args.slug)
    offset = book["page_offset"]
    pdf    = os.path.join(PDF_DIR, book["pdf"])

    if not os.path.isfile(pdf):
        raise SystemExit(f"PDF not found: {pdf}")

    pdf_start = args.book_start + offset
    pdf_end   = args.book_end   + offset

    print(f"Book '{book['title']}'")
    print(f"  Book pages {args.book_start}–{args.book_end}  →  PDF pages {pdf_start}–{pdf_end}")

    # ── 1. Extract text ───────────────────────────────────────────────────────
    raw = raw_txt(args.chapter)
    extract_script = os.path.join(os.path.dirname(__file__), "extract_pages.py")
    print(f"\n[1/2] Extracting text → {raw}")
    subprocess.run(
        [sys.executable, extract_script, pdf, str(pdf_start), str(pdf_end), raw],
        check=True,
    )

    # ── 2. Extract figures ────────────────────────────────────────────────────
    out_dir = img_dir(args.slug, args.chapter)
    fig_script = os.path.join(os.path.dirname(__file__), "extract_figures.py")
    print(f"\n[2/2] Extracting figures → {out_dir}/")
    subprocess.run(
        [sys.executable, fig_script,
         pdf, str(args.chapter), str(pdf_start), str(pdf_end), out_dir,
         "--dpi", str(args.dpi)],
        check=True,
    )

    print(f"""
{'='*60}
PREPARE COMPLETE — next steps:
  1. Read {raw} (in ~300-line chunks) to understand the chapter content.
  2. Generate {html_path(args.slug, args.chapter)}
     starting from template/study_guide_base.html.
  3. Add <!-- FIG_{args.chapter}_NN --> placeholders where figures belong.
     (See {manifest_path(args.slug, args.chapter)} for the full list.)
  4. Run:  python guide.py embed {args.slug} {args.chapter}
{'='*60}""")


# ── embed ─────────────────────────────────────────────────────────────────────

def cmd_embed(args):
    mpath = manifest_path(args.slug, args.chapter)
    hpath = html_path(args.slug, args.chapter)

    if not os.path.isfile(mpath):
        raise SystemExit(f"Manifest not found: {mpath}\nRun 'prepare' first.")
    if not os.path.isfile(hpath):
        raise SystemExit(f"HTML not found: {hpath}\nGenerate the study guide first.")

    with open(mpath, encoding="utf-8") as f:
        manifest = json.load(f)

    with open(hpath, encoding="utf-8") as f:
        html = f.read()

    replaced = 0
    skipped  = []

    for fig_num_str, meta in sorted(manifest.items(), key=lambda x: int(x[0])):
        placeholder = meta["placeholder"]
        img_file    = os.path.join(img_dir(args.slug, args.chapter), meta["file"])

        if placeholder not in html:
            skipped.append((fig_num_str, placeholder))
            continue

        if not os.path.isfile(img_file):
            print(f"  WARNING: image file missing for {placeholder}: {img_file}")
            continue

        ext = meta["file"].rsplit(".", 1)[-1].lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
        with open(img_file, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        fig_html = (
            f'\n<div class="fig-wrap">'
            f'<img src="data:{mime};base64,{b64}" alt="{meta["alt"]}" '
            f'style="max-width:100%;border-radius:6px;margin:12px auto;display:block;">'
            f'</div>\n'
        )
        html = html.replace(placeholder, fig_html, 1)
        replaced += 1
        print(f"  Embedded Fig {args.chapter}.{fig_num_str} ({meta['file']})")

    with open(hpath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nEmbedded {replaced} figure(s) into {hpath}")
    if skipped:
        print("Placeholders NOT found in HTML (add them manually and re-run embed):")
        for num, ph in skipped:
            print(f"  Fig {args.chapter}.{num}: {ph}")


# ── finalize ──────────────────────────────────────────────────────────────────

def cmd_finalize(args):
    data = load_books()
    book = find_book(data, args.slug)

    # ── Check the chapter isn't already recorded ──────────────────────────────
    existing = [c["chapter"] for c in book.get("completed_chapters", [])]
    if args.chapter in existing:
        print(f"Chapter {args.chapter} already in books.json — skipping update.")
    else:
        entry = {
            "chapter":    args.chapter,
            "title":      args.title or f"Chapter {args.chapter}",
            "book_pages": args.book_pages or "",
            "pdf_pages":  args.pdf_pages  or "",
            "output":     f"books/{args.slug}/chapter{args.chapter}_study_guide.html",
        }
        book.setdefault("completed_chapters", []).append(entry)
        save_books(data)

    # ── Optional cleanup ──────────────────────────────────────────────────────
    if args.clean:
        raw = raw_txt(args.chapter)
        if os.path.isfile(raw):
            os.remove(raw)
            print(f"Deleted {raw}")

        idir = img_dir(args.slug, args.chapter)
        if os.path.isdir(idir):
            import shutil
            shutil.rmtree(idir)
            print(f"Deleted {idir}/")

    # ── Git commit ────────────────────────────────────────────────────────────
    hpath = html_path(args.slug, args.chapter)
    files = [hpath, BOOKS_JSON]

    if args.yes:
        for fp in files:
            subprocess.run(["git", "add", fp], check=True)
        msg = (
            f"Ch{args.chapter}: add {book['title']} Chapter {args.chapter} study guide\n\n"
            f"Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
        )
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Committed and pushed.")
    else:
        print(f"\nFinalize complete. To commit, run:")
        print(f"  git add {hpath} {BOOKS_JSON}")
        print(f'  git commit -m "Ch{args.chapter}: add Chapter {args.chapter} study guide"')
        print(f"  git push")


# ── CLI entry ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="guide.py",
        description="Study guide pipeline: prepare -> (write HTML) -> embed -> finalize",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # prepare
    p_prep = sub.add_parser("prepare", help="Extract text + figures from PDF")
    p_prep.add_argument("slug",       help="Book slug (from books.json)")
    p_prep.add_argument("chapter",    type=int, help="Chapter number")
    p_prep.add_argument("book_start", type=int, help="First book page of the chapter")
    p_prep.add_argument("book_end",   type=int, help="Last book page of the chapter")
    p_prep.add_argument("--dpi",      type=int, default=150, help="Figure render DPI (default 150)")

    # embed
    p_emb = sub.add_parser("embed", help="Embed figures into the HTML study guide")
    p_emb.add_argument("slug",    help="Book slug")
    p_emb.add_argument("chapter", type=int, help="Chapter number")

    # finalize
    p_fin = sub.add_parser("finalize", help="Update books.json, clean up, commit")
    p_fin.add_argument("slug",        help="Book slug")
    p_fin.add_argument("chapter",     type=int, help="Chapter number")
    p_fin.add_argument("--title",     help="Chapter title for books.json entry")
    p_fin.add_argument("--book-pages",dest="book_pages", help="Book page range e.g. '1088-1134'")
    p_fin.add_argument("--pdf-pages", dest="pdf_pages",  help="PDF page range e.g. '1123-1169'")
    p_fin.add_argument("--clean",     action="store_true", help="Delete raw text + figure image files")
    p_fin.add_argument("--yes",       action="store_true", help="Auto git-add, commit, and push")

    args = parser.parse_args()
    {"prepare": cmd_prepare, "embed": cmd_embed, "finalize": cmd_finalize}[args.cmd](args)


if __name__ == "__main__":
    main()
