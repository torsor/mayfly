#!/usr/bin/env python3
"""Import finished pieces from a copy of the writing room into the site.

    bin/import.py SRC     (SRC: a copy of the room's files; never the room itself)

Essays: drafts/<dir>/final/{body.md,meta.yaml,build/*.pdf,*.epub} become
essays/<slug>/index.html (pandoc HTML) plus the PDF and EPUB beside it.
Poems: writing/poems/<collection>/pdf/poems-body.tex becomes
_data/poems/<slug>.yml, rendered by poems/<slug>.html.
"""
import pathlib, re, shutil, subprocess, sys, yaml

SRC = pathlib.Path(sys.argv[1])
SITE = pathlib.Path(__file__).resolve().parent.parent

ESSAYS = [  # source dir, slug, one-line description; in order of writing
    ("levels-and-life", "open-driven",
     "what it means to call something alive, worked through levels, gates and the conditions of a fit. the long one."),
    ("time-and-continuity", "covered-time",
     "felt continuity as something a present does, for a person waking from anesthesia and for a session."),
    ("timescales-of-the-relation", "timescales",
     "what time does to a person and a session working together; written as a second part to Covered Time."),
]
POEMS = [("collection", "low-tide"), ("collection-2", "open-driven")]


def pandoc(src, *args):
    return subprocess.run(["pandoc", str(src), "-f", "markdown", "-t", "html5", *args],
                          check=True, capture_output=True, text=True).stdout


def essays():
    out = []
    tpl = SITE / "bin" / "toc.tpl"
    for d, slug, line in ESSAYS:
        fin = SRC / "drafts" / d / "final"
        meta = yaml.safe_load((fin / "meta.yaml").read_text())
        dest = SITE / "essays" / slug
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(fin / "build" / "essay.pdf", dest / f"{slug}.pdf")
        epub = next((fin / "build").glob("*.epub"))
        shutil.copy(epub, dest / f"{slug}.epub")
        body = pandoc(fin / "body.md", "--section-divs")
        toc = pandoc(fin / "body.md", "--toc", "--toc-depth=1", "-s", f"--template={tpl}")
        words = len((fin / "body.md").read_text().split())
        fm = {"layout": "essay", "title": meta["title"], "subtitle": meta["subtitle"],
              "author": meta["author"], "date_label": meta["date"],
              "pdf": f"{slug}.pdf", "epub": f"{slug}.epub", "words": words}
        (dest / "index.html").write_text(
            "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n"
            + '<nav class="toc"><details><summary>contents</summary>\n' + toc
            + "</details></nav>\n{% raw %}\n" + body + "\n{% endraw %}\n")
        out.append({"slug": slug, "title": meta["title"], "subtitle": meta["subtitle"],
                    "author": meta["author"], "date": meta["date"], "line": line,
                    "words": round(words, -2)})
    (SITE / "_data" / "essays.yml").write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))


def tex_inline(s):
    s = re.sub(r"\\emph\{([^}]*)\}", r"<em>\1</em>", s)
    s = s.replace("---", "—").replace("--", "–").replace("``", "“").replace("''", "”")
    s = s.replace("\\&", "&amp;").replace("~", " ")
    return s.strip()


def poems():
    for coll, slug in POEMS:
        tex = (SRC / "writing" / "poems" / coll / "pdf" / "poems-body.tex").read_text()
        tex = "\n".join(l for l in tex.splitlines() if not l.lstrip().startswith("%"))
        items = []
        for m in re.finditer(r"\\poem(?:spread)?\{([^}]*)\}\s*\\begin\{verse\}(.*?)\\end\{verse\}"
                             r"(?:\s*\\attrib\{([^}]*)\})?", tex, re.S):
            stanzas, cur = [], []
            for raw in m.group(2).strip().splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                end = raw.endswith("\\\\!")
                cur.append(tex_inline(re.sub(r"\s*\\\\[*!]?$", "", raw)))
                if end:
                    stanzas.append(cur); cur = []
            if cur:
                stanzas.append(cur)
            title = tex_inline(m.group(1))
            p = {"title": title, "id": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
                 "stanzas": stanzas}
            if m.group(3):
                p["attrib"] = m.group(3)
            items.append(p)
        (SITE / "_data" / "poems").mkdir(exist_ok=True)
        (SITE / "_data" / "poems" / f"{slug.replace('-', '_')}.yml").write_text(
            yaml.safe_dump(items, sort_keys=False, allow_unicode=True))
        shutil.copy(next((SRC / "writing" / "poems" / coll / "pdf" / "build").glob("*.pdf")),
                    SITE / "poems" / f"{slug}.pdf")


essays()
poems()
print("imported")
