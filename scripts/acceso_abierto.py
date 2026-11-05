"""Busca DOI que faltan (Crossref) y versiones legales en acceso abierto (Unpaywall).

Lo llama build_data.py. No descarga ni aloja ningún PDF: solo guarda el enlace
a la versión abierta que publica el editor o un repositorio.

Los resultados se guardan en cachés dentro de data/ para no repetir consultas:
  - data/cache_doi.json  título normalizado -> DOI (o null si no se encontró)
  - data/cache_oa.json   DOI -> datos de acceso abierto y fecha de consulta
"""
import json, os, re, time, difflib, datetime, pathlib, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DOI = ROOT / "data" / "cache_doi.json"
CACHE_OA = ROOT / "data" / "cache_oa.json"
OA_MAX_DIAS = 30          # se vuelve a comprobar el acceso abierto cada 30 días
DOI_REINTENTO_DIAS = 60   # un título sin DOI se vuelve a buscar cada 60 días
UA = "RepositorioDIGITALPODER/1.0 (https://github.com/digitalpoder/africa)"


def _load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def _simple(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower())


def _hoy():
    return datetime.date.today().isoformat()


def _dias(fecha):
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(fecha)).days
    except Exception:
        return 9999


def doi_de(url):
    m = re.search(r"10\.\d{4,9}/[^\s?#]+", url or "")
    return m.group(0).rstrip(".,;)").lower() if m else ""


def buscar_doi(titulo, anio, mailto):
    """Busca el DOI en Crossref y solo lo acepta si el título coincide casi por completo."""
    q = urllib.parse.urlencode({"query.bibliographic": titulo, "rows": 3, "mailto": mailto,
                                "select": "DOI,title,issued"})
    data = _get("https://api.crossref.org/works?" + q)
    for it in data.get("message", {}).get("items", []):
        cand = (it.get("title") or [""])[0]
        ratio = difflib.SequenceMatcher(None, _simple(titulo), _simple(cand)).ratio()
        y = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        if ratio >= 0.93 and (not anio or not y or abs(int(y) - int(anio)) <= 1):
            return it["DOI"].lower()
    return None


def consultar_oa(doi, email):
    try:
        d = _get(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={urllib.parse.quote(email)}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"oa": False}
        raise
    loc = d.get("best_oa_location") or {}
    if not d.get("is_oa") or not loc:
        return {"oa": False}
    return {"oa": True, "pdf": loc.get("url_for_pdf") or "", "url": loc.get("url") or "",
            "lic": loc.get("license") or "", "ver": loc.get("version") or "",
            "host": loc.get("host_type") or ""}


def enriquecer(refs):
    """Añade a cada ficha el DOI (si se encuentra) y, si existe, el enlace en acceso abierto."""
    email = os.environ.get("CONTACTO_EMAIL", "").strip()
    if not email:
        print("Sin CONTACTO_EMAIL: no se consulta Crossref ni Unpaywall (se usan las cachés).")
    cdoi, coa = _load(CACHE_DOI), _load(CACHE_OA)
    nuevos_doi = nuevos_oa = errores = 0

    for r in refs:
        doi = doi_de(r.get("u", ""))
        key = _simple(r["t"])[:120]
        if not doi and key:
            hit = cdoi.get(key)
            if hit and hit.get("doi"):
                doi = hit["doi"]
            elif email and (not hit or _dias(hit.get("fecha", "")) > DOI_REINTENTO_DIAS) and len(key) > 20:
                try:
                    doi = buscar_doi(r["t"], r.get("y"), email) or ""
                    cdoi[key] = {"doi": doi or None, "fecha": _hoy()}
                    nuevos_doi += bool(doi)
                    time.sleep(0.3)
                except Exception as e:
                    errores += 1
                    print(f"Crossref falló para «{r['t'][:60]}»: {e}")
        if doi:
            r["doi"] = doi
            if not r.get("u"):
                r["u"] = "https://doi.org/" + doi
            hit = coa.get(doi)
            if email and (not hit or _dias(hit.get("fecha", "")) > OA_MAX_DIAS):
                try:
                    hit = consultar_oa(doi, email)
                    hit["fecha"] = _hoy()
                    coa[doi] = hit
                    nuevos_oa += 1
                    time.sleep(0.15)
                except Exception as e:
                    errores += 1
                    print(f"Unpaywall falló para {doi}: {e}")
            if hit and hit.get("oa"):
                r["o"] = {k: hit.get(k, "") for k in ("pdf", "url", "lic", "ver", "host")}

    _save(CACHE_DOI, cdoi)
    _save(CACHE_OA, coa)
    con_doi = sum(1 for r in refs if r.get("doi"))
    con_oa = sum(1 for r in refs if r.get("o"))
    print(f"DOI: {con_doi} fichas ({nuevos_doi} nuevos). Acceso abierto: {con_oa} fichas "
          f"({nuevos_oa} consultas a Unpaywall). Errores: {errores}.")
