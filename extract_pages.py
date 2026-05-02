import sys
import fitz  # PyMuPDF

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
