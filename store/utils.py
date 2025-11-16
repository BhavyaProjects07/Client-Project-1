# store/utils.py
import re
from html import escape

HEADING_PATTERNS = [
    r'^[A-Z0-9][A-Za-z0-9 \-]{2,}$',  # e.g. "Key Features" or UPPERCASE/TitleCase
]

def is_heading(line: str) -> bool:
    # treat lines that look like headings:
    # - short title-like lines
    # - lines ending with ":" also indicate heading
    l = line.strip()
    if not l or len(l) < 3:
        return False
    if l.endswith(':'):
        return True
    # Title-case / Upper-case heuristics:
    if l == l.upper() and any(c.isalpha() for c in l):  # ALL CAPS
        return True
    # If line is Title Case (First letters uppercase)
    if l.istitle():
        return True
    # fallback: if matches heading patterns
    for p in HEADING_PATTERNS:
        if re.match(p, l):
            return True
    return False

def format_description(raw: str) -> str:
    """
    Convert plain text to HTML:
      - Detect headings -> <h3>
      - Detect bullets starting with -, •, * -> <ul><li>...
      - Detect numbered lists 1., 2. -> <ol><li>...
      - Detect key: value blocks -> simple <table>
      - Convert paragraphs
    Returns safe HTML string (escape user text).
    """
    lines = raw.splitlines()
    output = []
    in_ul = False
    in_ol = False
    kv_block = []   # temporarily store key: value lines
    para_buffer = []

    def flush_para():
        nonlocal para_buffer
        if not para_buffer:
            return
        text = " ".join(p.strip() for p in para_buffer).strip()
        if text:
            output.append(f"<p class='desc-paragraph'>{escape(text)}</p>")
        para_buffer = []

    def flush_kv():
        nonlocal kv_block
        if not kv_block:
            return
        output.append("<table class='w-full text-sm my-3 text-gray-700'><tbody>")
        for k, v in kv_block:
            output.append(
                "<tr class='border-t'><td class='py-1 align-top font-semibold w-1/3'>{}</td>"
                "<td class='py-1'>{}</td></tr>".format(escape(k), escape(v))
            )
        output.append("</tbody></table>")
        kv_block = []

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            output.append("</ul>")
            in_ul = False
        if in_ol:
            output.append("</ol>")
            in_ol = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            # blank line -> paragraph break
            flush_para()
            close_lists()
            flush_kv()
            continue

        # bullet list
        m_b = re.match(r'^\s*[-•\*]\s+(.*)', line)
        if m_b:
            flush_para()
            flush_kv()
            if in_ol:
                output.append("</ol>"); in_ol = False
            if not in_ul:
                output.append("<ul class='desc-list list-disc pl-6 my-2'>")
                in_ul = True
            output.append(f"<li>{escape(m_b.group(1).strip())}</li>")
            continue

        # numbered list
        m_n = re.match(r'^\s*\d+\.\s+(.*)', line)
        if m_n:
            flush_para()
            flush_kv()
            if in_ul:
                output.append("</ul>"); in_ul = False
            if not in_ol:
                output.append("<ol class='desc-numbered list-decimal pl-6 my-2'>")
                in_ol = True
            output.append(f"<li>{escape(m_n.group(1).strip())}</li>")
            continue

        # key: value lines (technical specs)
        m_kv = re.match(r'^\s*([^:]{1,60})\s*:\s*(.+)$', line)
        if m_kv:
            flush_para()
            close_lists()
            kv_block.append((m_kv.group(1).strip(), m_kv.group(2).strip()))
            continue

        # headings heuristics
        if is_heading(line.strip()):
            flush_para()
            close_lists()
            flush_kv()
            output.append(f"<h3 class='desc-heading'>{escape(line.strip().rstrip(':'))}</h3>")
            continue

        # otherwise plain paragraph line -> buffer until blank line
        para_buffer.append(line)

    # flush remaining
    flush_para()
    close_lists()
    flush_kv()

    # join and return
    html = "\n".join(output)
    # Add a lightweight wrapper class if you want to style it in frontend
    return f"<div class='description-content'>{html}</div>"
