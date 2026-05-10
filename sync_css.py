"""
sync_css.py — Push CSS from template/study_guide_base.html to all existing guides.

Run this whenever you update the template CSS to keep every guide in sync.

Usage:
  python sync_css.py [--dry-run] [--file <path>]

Options:
  --dry-run   Show which files would be updated without writing anything
  --file      Update only this specific HTML file instead of all guides
"""

import argparse
import os
import re
import glob

TEMPLATE = os.path.join(os.path.dirname(__file__), "template", "study_guide_base.html")
BOOKS_DIR = os.path.join(os.path.dirname(__file__), "books")

CSS_RE = re.compile(r"(<style>)(.*?)(</style>)", re.DOTALL)


def extract_css(html):
    m = CSS_RE.search(html)
    return m.group(2) if m else None


def replace_css(html, new_css):
    return CSS_RE.sub(lambda m: m.group(1) + new_css + m.group(3), html, count=1)


def main():
    parser = argparse.ArgumentParser(description="Sync CSS from template to all study guides")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--file",    help="Update only this HTML file")
    args = parser.parse_args()

    if not os.path.isfile(TEMPLATE):
        raise SystemExit(f"Template not found: {TEMPLATE}")

    with open(TEMPLATE, encoding="utf-8") as f:
        tmpl_html = f.read()

    new_css = extract_css(tmpl_html)
    if not new_css:
        raise SystemExit("Could not find <style>...</style> in template.")

    if args.file:
        targets = [args.file]
    else:
        targets = glob.glob(os.path.join(BOOKS_DIR, "**", "*_study_guide.html"), recursive=True)

    updated = 0
    for fpath in sorted(targets):
        with open(fpath, encoding="utf-8") as f:
            html = f.read()

        old_css = extract_css(html)
        if old_css is None:
            print(f"  SKIP (no <style> block): {fpath}")
            continue

        if old_css == new_css:
            print(f"  OK (already current): {os.path.relpath(fpath)}")
            continue

        if args.dry_run:
            print(f"  WOULD UPDATE: {os.path.relpath(fpath)}")
        else:
            new_html = replace_css(html, new_css)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(new_html)
            print(f"  UPDATED: {os.path.relpath(fpath)}")
            updated += 1

    if not args.dry_run:
        print(f"\nSync complete. {updated} file(s) updated.")
    else:
        print("\n(dry run — no files were written)")


if __name__ == "__main__":
    main()
