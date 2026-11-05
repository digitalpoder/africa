"""Convierte la matriz bibliográfica de DIGITALPODER (.xlsm/.xlsx) en data/repositorio.json.

Uso:  python scripts/build_data.py ruta/a/la/matriz.xlsm

Lee las hojas de los ejes 1 a 6 y la hoja de documentación (eje 7), fusiona
duplicados por título, añade las referencias de data/referencias_complementarias.md
que aún no estén en la matriz y clasifica cada ficha por ámbito geográfico,
tipo de documento e idioma.
"""
import json, re, sys, unicodedata, datetime, pathlib
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "repositorio.json"
EXTRA = ROOT / "data" / "referencias_complementarias.md"

# Hojas de la matriz -> número de eje (se buscan por el comienzo del nombre)
SHEETS = [("eje tecnol", 1), ("emprendimiento", 2), ("compatibilidad", 3),
          ("estrategias", 4), ("marco te", 5), ("contextos", 6)]
DOC_SHEET = "documentaci"
EXTRA_HEAD = {"Emprendimiento y Empoderamiento": 2, "Compatibilidad Cultural y Aprop": 3,
              "Estrategias Regionales y Gobern": 4, "Marco Teórico + general": 5, "Contextos": 6}


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s)


def cell(x):
    if x is None:
        return ""
    s = str(x).strip()
    return s[:-2] if re.fullmatch(r"\d{4}\.0", s) else s


def year(a):
    m = re.search(r"(19|20)\d\d", a or "")
    return int(m.group(0)) if m else None


GEO = [
    ("gb", r"guin[eé]a?[\s-]*bis|guin[eé][\s-]*bissau|bissau"),
    ("cv", r"cabo[\s-]*verd|cape verd|caboverd"),
    ("tz", r"tanzan|dar es salaam|zanzibar"),
    ("ao", r"occid|uemoa|waemu|cedeao|ecowas|senegal|ghana|nigeria|burkina|ben[ií]n|\bmal[ií]\b|n[ií]ger\b|togo|marfil|c[oô]te|liberia|sierra leona|west africa|camer[uú]n"),
    ("aor", r"kenia|kenya|uganda|ruanda|rwanda|etiop|\beac\b|oriental|east afric"),
    ("otr", r"sud[aá]frica|south africa|zimbabwe|malawi|mozambi|zambia|egipt|marruec|namib|botsuana|angola|congo|madagas|lesoth|eswatini|t[uú]nez|argelia|sud[aá]n"),
    ("af", r"[aá]frica|subsah"),
    ("gl", r"global|comparativ|pa[ií]ses|brasil|india|españa|espana|ee\.?\s?uu|estados unidos|am[eé]rica|asia|europa|reino unido|china|vietnam|pakist|indonesia|sur global|galicia|transnacional"),
]


def geo_tags(pais, titulo):
    full = (pais + " " + titulo).lower()
    tags = []
    for code, rx in GEO:
        src = full if code in ("gb", "cv", "tz") else pais.lower()
        if re.search(rx, src):
            tags.append(code)
    if not tags:
        tags = ["af"] if "afric" in full else ["gl"]
    return tags


def doc_type(fuente, ref):
    f = (fuente + " " + ref).lower()
    if re.search(r"fin de m[aá]ster|tesis|thesis|dissertation|tfg|doctoral", f):
        return "tesis"
    if re.search(r"cap[ií]tulo|chapter|in:|actas|proceedings|conference|congreso", f):
        return "capitulo"
    if re.search(r"arxiv|preprint|ssrn|working paper|discussion paper|documento de trabajo", f):
        return "preprint"
    if re.search(r"\(libro\)|books|press\b|lexington|routledge|editorial|libro", f) and not re.search("journal|revista", f):
        return "libro"
    if re.search(r"banco mundial|world bank|gsma|fmi|\bimf\b|informe|report|unesco|un women|onu|oecd|ocde|pnud|undp|\bitu\b|uit|afrobarometer|eeas|global gateway|blog|policy brief|ecdpm|bceao|gobierno|minist|government|strategy|estrategia|uni[oó]n africana|african union|auda|nepad|ficha|usaid|giz|afdb|banco africano|women in tech|plataforma|web|sitio|unctad|fao|ifad", f):
        return "informe"
    return "articulo"


PT = r"\b(da|do|das|dos|nas|nos|para as|mulheres|não|uma|em|com)\b|ção\b|ções\b|ões\b"
ES = r"\b(el|los|las|del|mujeres|una|en el|y la|sobre|desde)\b|ción\b|ciones\b"
FR = r"\b(les|des|et|femmes|une|dans|pour|numérique|au)\b"


def lang(titulo):
    t = " " + titulo.lower() + " "
    sc = {"pt": len(re.findall(PT, t)), "es": len(re.findall(ES, t)), "fr": len(re.findall(FR, t))}
    best = max(sc, key=sc.get)
    if sc[best] >= 2 or (sc[best] == 1 and re.search(r"[ãõçáéíóúâêô]", t)):
        if best == "es" and re.search(r"[ãõ]|ção", t):
            best = "pt"
        return best
    return "en"


def find_sheet(wb, prefix):
    for ws in wb.worksheets:
        if norm(ws.title).startswith(norm(prefix)):
            return ws
    return None


def main(path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    recs, order = {}, []

    def add(r, eje):
        key = norm(r["tit"])[:80] or norm(r["ref"])
        if not key:
            return
        if key in recs:
            o = recs[key]
            if eje not in o["ejes"]:
                o["ejes"].append(eje)
            for f in ("pais", "anio", "ref", "fuente", "tema", "metodo", "hall", "enl", "doi"):
                if not o.get(f) and r.get(f):
                    o[f] = r[f]
            return
        r["ejes"] = [eje]
        recs[key] = r
        order.append(key)

    for prefix, eje in SHEETS:
        ws = find_sheet(wb, prefix)
        if ws is None:
            print(f"Aviso: no encuentro la hoja del eje {eje} ({prefix}…)")
            continue
        for row in ws.iter_rows(min_row=2, values_only=True):
            v = [cell(x) for x in list(row)[:9]] + [""] * 9
            if not any(v[:9]):
                continue
            add(dict(pais=v[0], anio=v[1], ref=v[2], tit=v[3], fuente=v[4], tema=v[5],
                     metodo=v[6], hall=v[7], enl=v[8]), eje)

    # Referencias complementarias verificadas (solo se añaden si no están ya en la matriz)
    fuentes_extra = []
    if EXTRA.exists():
        cur = None
        for line in EXTRA.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("## "):
                h = line[3:]
                cur = 7 if "Eje 7" in h else EXTRA_HEAD.get(h)
                continue
            if not line.startswith("- ") or cur is None:
                continue
            if cur == 7:
                n, t, u = line[2:].split("|")
                fuentes_extra.append(dict(n=n, t=t, i="", tm="", u=u))
                continue
            m = re.match(r"- \*\*(.+?)\*\* — (.+?)\. \*(.+?)\*\. \[(.+?)\] (\S+)$", line)
            if not m:
                continue
            ref, tit, fu, pa, url = m.groups()
            ym = re.search(r"20\d\d", ref)
            add(dict(pais=pa, anio=ym.group(0) if ym else "", ref=ref, tit=tit, fuente=fu,
                     tema="", metodo="", hall="", enl="", doi=url), cur)

    data = []
    for i, k in enumerate(order):
        r = recs[k]
        enl = r.get("enl", "")
        url = enl if enl.startswith("http") else r.get("doi", "")
        if not url:
            d = re.search(r"10\.\d{4,9}/\S+", " ".join([enl, r["fuente"], r["tit"]]))
            if d:
                url = "https://doi.org/" + d.group(0).rstrip(".,;)")
        data.append(dict(
            i=i, e=sorted(r["ejes"]), p=r["pais"], y=year(r["anio"]), yr=r["anio"],
            a=r["ref"], t=r["tit"], f=r["fuente"], k=r["tema"], m=r["metodo"], h=r["hall"],
            u=url, d="" if enl.startswith("http") else enl,
            g=geo_tags(r["pais"], r["tit"]), ty=doc_type(r["fuente"], r["ref"]), l=lang(r["tit"])))

    fuentes, seen = [], set()
    ws = find_sheet(wb, DOC_SHEET)
    rows = []
    if ws is not None:
        for row in ws.iter_rows(min_row=2, values_only=True):
            v = [cell(x) for x in list(row)[:5]] + [""] * 5
            if any(v[:5]):
                rows.append(dict(n=v[0], t=v[1], i=v[2], tm=v[3], u=v[4]))
    for f in rows + fuentes_extra:
        key = f["u"].rstrip("/").lower() or norm(f["n"])
        if not f["n"] or key in seen or (not f["u"] and not f["tm"] and any(norm(f["n"]) in norm(g["n"]) for g in rows if g is not f)):
            continue
        seen.add(key)
        fuentes.append(f)

    out = dict(actualizado=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
               refs=data, fuentes=fuentes)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(data)} referencias y {len(fuentes)} fuentes -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/build_data.py ruta/a/la/matriz.xlsm")
    main(sys.argv[1])
