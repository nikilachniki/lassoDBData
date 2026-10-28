#!/usr/bin/env python3
"""Importiert die Excel-Quellen des Lasso-Werkverzeichnisses nach JSON-LD.

Aufruf:  python scripts/import_excel.py

Das Skript ist wiederholbar. Es liest jede in SOURCES registrierte Excel-Datei
aus raw/, bildet ihre Spalten auf das kanonische Feldmodell ab und schreibt die
Ergebnisse nach data/. Eine weitere Tabelle mit abweichenden Spalten wird
ergaenzt, indem ein weiterer Eintrag zu SOURCES hinzugefuegt wird. Spalten, die
im Mapping nicht vorkommen, gehen nicht verloren, sondern landen im Feld "extra".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
OUT_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schema"
REGISTRY_PATH = ROOT / "scripts" / "id-registry.json"
ENTRY_SCHEMA_PATH = SCHEMA_DIR / "entry.schema.json"
MANUSCRIPT_SCHEMA_PATH = SCHEMA_DIR / "manuscript.schema.json"

CONTEXT_URL = (
    "https://raw.githubusercontent.com/nikilachniki/lassoDBData/main/"
    "schema/context.jsonld"
)

# Registrierte Quellen. Fuer eine weitere Excel-Tabelle hier einen Eintrag
# ergaenzen. "columns" bildet den Spaltenkopf der Tabelle auf ein kanonisches
# Feld ab; unbekannte Spalten werden automatisch nach "extra" durchgereicht.
SOURCES = [
    {
        "id": "lv-katalog",
        "file": "Werke.xlsx",
        "sheet": "LV-Katalog",
        "columns": {
            "LV": "lv",
            "Titel": "title",
            "Stimmen": "voices",
            "Ersterscheinung": "firstPrint",
            "Textdichter": "textAuthor",
            "Textprovenienz": "textSource",
            "Gesamtausgabe": "completeEdition",
            "Bemerkung": "note",
            "Gattung": "genre",
            "Sprache": "language",
            "Titel normalisiert": "normalizedTitle",
            "Titel normalisiert (Grundlage)": "normalizedTitleBasis",
        },
    },
]

# Drucke.xlsx, Blatt Drucknachweise: eine Zeile je Werk und Druck, auch
# Nachdrucke, nach dem Gesamtregister der Werke Lassos. Eigene Quelle statt
# Spalten in Werke.xlsx, weil die Beziehung Werk-Druck n:m ist, siehe
# docs/entscheidungen.md, Abschnitt 23. Die Zeilen sind keine Datensaetze mit
# eigener ID, sondern Angaben am Werk, deshalb kein Eintrag in der Registry.
PRINT_APPEARANCE_SOURCE = {
    "file": "Drucke.xlsx",
    "sheet": "Drucknachweise",
}
# Drucke.xlsx, Blatt Drucke: eine Zeile je Druck mit den Angaben aus dem
# Druckeverzeichnis, siehe Abschnitt 26.
PRINT_SOURCE = {
    "file": "Drucke.xlsx",
    "sheet": "Drucke",
}
REFERENCE_PREFIX = "Verweis "
RISM_COLUMN = "RISM"

# LV-Nummer: Grundnummer, optionaler Teilsatz (1-2), optionale Fassung (74 (IV))
RE_LV_PART = re.compile(r"^(\d+)-(\d+)$")
RE_LV_VARIANT = re.compile(r"^(\d+)\s*\(([IVXLC]+)\)$")
RE_LV_PLAIN = re.compile(r"^(\d+)$")
# Druck-Sigle: Jahr, laufende Nummer innerhalb des Jahres und optional der
# Teil eines mehrbaendigen Drucks, z.B. 1555-1 oder 1575-3/I
RE_PRINT = re.compile(r"^(\d{4})-(\d+)(?:/([IVX]+))?$")
# Fuehrende Teilsatz-Markierung im Titel, z.B. "[2] Tengan dunque"
RE_TITLE_PART = re.compile(r"^\[(\d+)\]\s*")
# Teilfeld der Quellenart, z.B. "$b[6]"
RE_SUBFIELD = re.compile(r"\$(\w)([^$]*)")
# Stimmen ueber C, A, T, B hinaus, in der Quelle als Ziffer gezaehlt
VOICE_NAMES = {
    "5": "Quintus", "V": "Quintus", "6": "Sextus", "VI": "Sextus",
    "7": "Septimus", "VII": "Septimus", "8": "Octavus", "VIII": "Octavus",
}
# Verweis auf eine Nummer im LV-Anhang im Freitext, z.B. "vgl. LVanh 98"
RE_LVANH = re.compile(r"LVanh\.?\s*(\d+)", re.IGNORECASE)

# Handschriften-Quelle: andere Spalten und ein anderes Feldmodell als die
# Drucke (RISM-Sigel/Bibliothek/Signatur statt Drucksigle), deshalb ein
# eigenes Mapping statt eines weiteren Eintrags in SOURCES.
#
# "Bemerkung (Quelle)" wird bewusst nicht auf "note" gemappt, obwohl beides
# Freitext ist: "note" (Spalte "Weitere Teile") traegt die LVanh-Verweise, auf
# die parse_lvanh in read_manuscripts angewiesen ist, und darf durch eine
# zweite Quelle nicht ueberschrieben oder vermischt werden, siehe Abschnitt 16
# in docs/entscheidungen.md.
MANUSCRIPT_SOURCES = [
    {
        "id": "handschriften",
        "file": "lasso_handschriften.xlsx",
        "sheet": "Werke",
        "columns": {
            "LV": "lv",
            "Unternummer": "lvPart",
            "Titel": "title",
            "Weitere Teile": "note",
            "Stimmen": "voices",
            "Datierung": "dating",
            "RISM-Sigel": "rismSiglum",
            "Link": "link",
            "Ort": "place",
            "Bibliothek": "library",
            "Signatur": "shelfmark",
            "Weitere Signatur": "shelfmarkAlt",
            "Quellenart": "sourceType",
            "Provenienz": "provenance",
            "Bemerkung (Quelle)": "sourceNote",
            "Literatur": "literature",
        },
    },
]


def clean(value):
    """Normalisiert eine Zelle auf einen getrimmten String oder None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_lv(raw):
    """Zerlegt die LV-Angabe in Grundnummer, Teilsatz und Fassung."""
    out = {"lv": raw, "lvBase": None, "lvPart": None, "lvVariant": None}
    if not raw:
        return out
    match = RE_LV_PLAIN.match(raw)
    if match:
        out["lvBase"] = int(match.group(1))
        return out
    match = RE_LV_PART.match(raw)
    if match:
        out["lvBase"] = int(match.group(1))
        out["lvPart"] = int(match.group(2))
        return out
    match = RE_LV_VARIANT.match(raw)
    if match:
        out["lvBase"] = int(match.group(1))
        out["lvVariant"] = match.group(2)
    return out


def parse_print(raw):
    """Zerlegt die Druck-Sigle in Jahr, laufende Nummer und Teil.

    "part" (etwa "I" in 1575-3/I) wird nur von derive_prints gebraucht und
    nicht an den Eintrag uebernommen.
    """
    if not raw:
        return {"firstPrint": None, "firstPrintYear": None, "firstPrintNo": None, "part": None}
    match = RE_PRINT.match(raw)
    if not match:
        return {"firstPrint": raw, "firstPrintYear": None, "firstPrintNo": None, "part": None}
    return {
        "firstPrint": raw,
        "firstPrintYear": int(match.group(1)),
        "firstPrintNo": int(match.group(2)),
        "part": match.group(3),
    }


def parse_voices(raw):
    """Liest die Stimmenzahl als Ganzzahl, behaelt den Rohwert bei Abweichung."""
    if not raw:
        return None, None
    if raw.isdigit():
        return int(raw), None
    return None, raw


def parse_title(raw):
    """Trennt die Teilsatz-Markierung vom eigentlichen Titel.

    Liefert den Titel ohne Markierung und die Nummer aus der Markierung (oder
    None). Die Markierung selbst wird nicht gespeichert, da sie der
    Teilsatznummer der LV-Angabe entspricht; read_source prueft das.
    """
    if not raw:
        return None, None
    match = RE_TITLE_PART.match(raw)
    stripped = RE_TITLE_PART.sub("", raw).strip()
    return (stripped or None), (int(match.group(1)) if match else None)


def parse_source_type(raw):
    """Macht die Quellenart mit Teilfeldern lesbar.

    Stimmbuecher stehen in der Quelle als "$a[Stimmbücher]$b[6]$c[C, A, T, B, 5, 6]":
    $a Art, $b Anzahl der Stimmbuecher, $1 Gesamtzahl ("(von 5)"), $c die
    vorhandenen Stimmen ("?" unbekannt), $d Zusatz. Daraus wird
    "Stimmbücher (6): C, A, T, B, 5, 6". Eckige Klammern (vom Bearbeiter
    ergaenzt) entfallen, auch um Klartext wie "[Chorbuch]".
    """
    def unwrap(value):
        value = value.strip()
        if value.startswith("[") and value.endswith("]") or value.startswith("(") and value.endswith(")"):
            value = value[1:-1].strip()
        return value

    if not raw:
        return raw
    if "$" not in raw:
        return unwrap(raw) if raw.startswith("[") else raw
    fields = {key: unwrap(value) for key, value in RE_SUBFIELD.findall(raw)}
    text = fields.get("a") or ""
    count = " ".join(v for v in (fields.get("b"), fields.get("1")) if v and v != "?")
    if count:
        text += " ({0})".format(count)
    if fields.get("c") and fields["c"] != "?":
        voices = [VOICE_NAMES.get(v.strip(), v.strip()) for v in fields["c"].split(",")]
        text += ": " + ", ".join(voices)
    if fields.get("d"):
        text += "; " + fields["d"]
    return text.strip() or raw


def natural_key(dataset, lv, first_print, seen):
    """Bildet den fachlichen Wiedererkennungsschluessel einer Zeile.

    Die LV-Nummer allein genuegt nicht, da dasselbe Werk in mehreren Drucken
    erscheinen kann und dann mehrfach im Katalog steht. Erst LV plus Erstdruck
    identifiziert eine Zeile; bei echten Wiederholungen haengt ein Zaehler an.
    Der Titel geht bewusst nicht ein, damit eine spaetere Titelkorrektur die
    Zeile nicht zu einem neuen Datensatz macht.
    """
    base = "{0}|{1}|{2}".format(
        dataset, lv or "ohne-lv", first_print or "ohne-druck"
    )
    key = base
    counter = 2
    while key in seen:
        key = "{0}|{1}".format(base, counter)
        counter += 1
    seen.add(key)
    return key


def natural_key_manuscript(dataset, lv, lv_anh, lv_part, rism, shelfmark, seen):
    """Fachlicher Wiedererkennungsschluessel einer Handschriften-Zeile.

    Eine physische Quelle (RISM-Sigel plus Signatur) kann mehrere
    Lasso-Stuecke enthalten, und dasselbe Stueck kann in mehreren Quellen
    ueberliefert sein. Erst das Werk (LV oder LVanh, ggf. mit Teilsatz)
    zusammen mit der Quelle identifiziert eine Zeile eindeutig und bleibt
    ueber spaetere Importe hinweg stabil. Eigene Funktion statt Wiederverwendung
    von natural_key: die Felder unterscheiden sich, und eine Aenderung an
    natural_key wuerde sonst versehentlich auch die laengst vergebenen
    Schluessel der Drucke verschieben.
    """
    base = "{0}|{1}|{2}|{3}|{4}|{5}".format(
        dataset,
        lv or "ohne-lv",
        lv_anh if lv_anh is not None else "ohne-anh",
        lv_part if lv_part is not None else "ohne-teil",
        rism or "ohne-rism",
        shelfmark or "ohne-signatur",
    )
    key = base
    counter = 2
    while key in seen:
        key = "{0}|{1}".format(base, counter)
        counter += 1
    seen.add(key)
    return key


def load_registry():
    """Laedt die Zuordnung von fachlichem Schluessel zu interner ID.

    Einmal vergebene IDs bleiben dadurch ueber alle spaeteren Importe hinweg
    stabil, auch wenn Zeilen dazukommen, wegfallen oder umsortiert werden.
    Ohne diese Datei wuerde jeder Lauf neu durchzaehlen und alle Verweise
    auf bereits veroeffentlichte IDs brechen.
    """
    if not REGISTRY_PATH.exists():
        return {"nextId": 1, "assigned": {}}
    with REGISTRY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def assign_id(registry, key):
    """Liefert die interne ID zu einem Schluessel, vergibt sie bei Bedarf neu."""
    assigned = registry["assigned"]
    if key in assigned:
        return assigned[key], False
    new_id = registry["nextId"]
    assigned[key] = new_id
    registry["nextId"] = new_id + 1
    return new_id, True


def save_registry(registry):
    """Schreibt die Registry sortiert zurueck, fuer lesbare Git-Diffs."""
    payload = {
        "comment": (
            "Zuordnung fachlicher Schluessel zu interner laufender ID. "
            "Nicht von Hand aendern. Einmal vergebene IDs werden nie neu "
            "vergeben, auch wenn ein Datensatz spaeter entfaellt."
        ),
        "nextId": registry["nextId"],
        "assigned": dict(sorted(registry["assigned"].items(), key=lambda kv: kv[1])),
    }
    with REGISTRY_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_source(spec, registry):
    """Liest eine registrierte Excel-Quelle und liefert kanonische Eintraege."""
    path = RAW_DIR / spec["file"]
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = workbook[spec["sheet"]]
    rows = sheet.iter_rows(values_only=True)
    header = [clean(c) for c in next(rows)]

    mapping = spec["columns"]
    unmapped = [h for h in header if h and h not in mapping]
    if unmapped:
        print("  Hinweis: nicht gemappte Spalten nach 'extra': {0}".format(unmapped))

    entries = []
    seen_keys = set()
    new_ids = 0
    for row_no, row in enumerate(rows, start=2):
        record = {}
        extra = {}
        for column, value in zip(header, row):
            if column is None:
                continue
            cleaned = clean(value)
            if column in mapping:
                record[mapping[column]] = cleaned
            elif cleaned is not None:
                extra[column] = cleaned

        if not any(record.get(key) for key in ("lv", "title")):
            continue  # vollstaendig leere Zeile

        lv_parts = parse_lv(record.get("lv"))
        print_parts = parse_print(record.get("firstPrint"))
        voices, voices_raw = parse_voices(record.get("voices"))
        title, title_part = parse_title(record.get("title"))
        if title_part is not None and title_part != lv_parts["lvPart"]:
            print("  Hinweis: Zeile {0}, Teilsatzmarke [{1}] im Titel passt nicht zu LV {2}".format(
                row_no, title_part, lv_parts["lv"]
            ))
        key = natural_key(
            spec["id"], lv_parts["lv"], print_parts["firstPrint"], seen_keys
        )
        internal_id, is_new = assign_id(registry, key)
        if is_new:
            new_ids += 1

        entry = {
            "@id": "entry:{0:05d}".format(internal_id),
            "@type": "CatalogueEntry",
            "lv": lv_parts["lv"],
            "lvBase": lv_parts["lvBase"],
            "lvPart": lv_parts["lvPart"],
            "lvVariant": lv_parts["lvVariant"],
            "title": title,
            "normalizedTitle": record.get("normalizedTitle"),
            "normalizedTitleBasis": record.get("normalizedTitleBasis"),
            "voices": voices,
            "firstPrint": print_parts["firstPrint"],
            "firstPrintYear": print_parts["firstPrintYear"],
            "firstPrintNo": print_parts["firstPrintNo"],
            "textAuthor": record.get("textAuthor"),
            # Gesetzt von derive_persons, hier nur fuer die Feldreihenfolge.
            "textAuthorPerson": None,
            "textAuthorUncertain": False,
            "textSource": record.get("textSource"),
            "completeEdition": record.get("completeEdition"),
            "note": record.get("note"),
            "genre": record.get("genre"),
            "language": record.get("language"),
        }
        if voices_raw:
            entry["voicesRaw"] = voices_raw
        if extra:
            entry["extra"] = extra
        entries.append(entry)

    workbook.close()
    return entries, new_ids


def read_manuscripts(spec, registry):
    """Liest eine registrierte Handschriften-Quelle und liefert Zeugnisse.

    Anders als bei den Drucken steckt die Teilsatznummer nicht in der
    LV-Schreibweise ("100-2"), sondern in einer eigenen Spalte (Unternummer),
    und es gibt keine Fassungskennzeichnung wie "74 (IV)". Fehlt die
    LV-Nummer, verweist das Freitextfeld "Weitere Teile" manchmal auf eine
    Nummer im LV-Anhang (etwa "vgl. LVanh 98"); die wird hier erkannt, damit
    auch diese Stuecke spaeter zu einem Werk gruppiert werden koennen. Fehlen
    beide, bleibt die Zeile unverknuepft, wird aber nicht verworfen.
    """
    path = RAW_DIR / spec["file"]
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = workbook[spec["sheet"]]
    rows = sheet.iter_rows(values_only=True)
    header = [clean(c) for c in next(rows)]

    mapping = spec["columns"]
    unmapped = [h for h in header if h and h not in mapping]
    if unmapped:
        print("  Hinweis: nicht gemappte Spalten nach 'extra': {0}".format(unmapped))

    manuscripts = []
    seen_keys = set()
    new_ids = 0
    for row in rows:
        record = {}
        extra = {}
        for column, value in zip(header, row):
            if column is None:
                continue
            cleaned = clean(value)
            if column in mapping:
                record[mapping[column]] = cleaned
            elif cleaned is not None:
                extra[column] = cleaned

        if not record.get("title"):
            continue  # vollstaendig leere Zeile

        lv_base = int(record["lv"]) if record.get("lv") else None
        lv_part = int(record["lvPart"]) if record.get("lvPart") else None
        lv = None
        if lv_base is not None:
            lv = "{0}-{1}".format(lv_base, lv_part) if lv_part else str(lv_base)

        note = record.get("note")
        lv_anh = None
        if lv is None and note:
            match = RE_LVANH.search(note)
            if match:
                lv_anh = int(match.group(1))

        voices, voices_raw = parse_voices(record.get("voices"))

        key = natural_key_manuscript(
            spec["id"],
            lv,
            lv_anh,
            lv_part,
            record.get("rismSiglum"),
            record.get("shelfmark"),
            seen_keys,
        )
        internal_id, is_new = assign_id(registry, key)
        if is_new:
            new_ids += 1

        manuscript = {
            "@id": "manuscript:{0:05d}".format(internal_id),
            "@type": "ManuscriptWitness",
            "lv": lv,
            "lvBase": lv_base,
            "lvPart": lv_part,
            "lvAnh": lv_anh,
            "title": record.get("title"),
            "voices": voices,
            "dating": record.get("dating"),
            "rismSiglum": record.get("rismSiglum"),
            "link": record.get("link"),
            "place": record.get("place"),
            "library": record.get("library"),
            "shelfmark": record.get("shelfmark"),
            "shelfmarkAlt": record.get("shelfmarkAlt"),
            "sourceType": parse_source_type(record.get("sourceType")),
            "provenance": record.get("provenance"),
            "sourceNote": record.get("sourceNote"),
            "literature": record.get("literature"),
            "note": note,
        }
        if voices_raw:
            manuscript["voicesRaw"] = voices_raw
        if extra:
            manuscript["extra"] = extra
        manuscripts.append(manuscript)

    workbook.close()
    return manuscripts, new_ids


def read_print_appearances(spec):
    """Liest die Drucknachweise: welches Werk in welchem Druck.

    Das Register fuehrt Werke nur mit der Grundnummer, nicht mit Teilsaetzen;
    die Nachweise gehoeren daher zum Gesamtwerk. Zeilen ohne Drucksigle
    (Handschriften o. Ae. in der Druckspalte) werden uebergangen.
    """
    path = RAW_DIR / spec["file"]
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows = workbook[spec["sheet"]].iter_rows(values_only=True)
    header = [clean(c) for c in next(rows)]
    appearances = []
    for row in rows:
        record = dict(zip(header, (clean(v) for v in row)))
        siglum = record.get("Sigle")
        if not siglum:
            continue
        appearances.append({
            "lv": record.get("LV"),
            "lvAnh": int(record["LV-Anhang"]) if record.get("LV-Anhang") else None,
            "siglum": siglum,
            "piece": record.get("Stück"),
            "approximate": record.get("Datierung") == "ca.",
            "note": record.get("Zusatz"),
        })
    workbook.close()
    return appearances


def read_print_descriptions(spec):
    """Liefert Sigle -> Angaben aus dem Druckeverzeichnis (Abschnitt 26).

    Die Spalten fuellt scripts/tex_drucke.py aus den TeX-Dateien. Die Verweise
    stehen in einer Spalte je Verzeichnis ("Verweis RISM", "Verweis
    Boetticher", ...) und werden zu einem Objekt mit einem Feld je Verzeichnis.
    """
    path = RAW_DIR / spec["file"]
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows = workbook[spec["sheet"]].iter_rows(values_only=True)
    header = [clean(c) for c in next(rows)]
    descriptions = {}
    for row in rows:
        record = dict(zip(header, (clean(v) for v in row)))
        if not record.get("Sigle"):
            continue
        descriptions[record["Sigle"]] = {
            "description": record.get("Beschreibung"),
            "references": {
                column[len(REFERENCE_PREFIX):]: value
                for column, value in record.items()
                if column and column.startswith(REFERENCE_PREFIX) and value
            },
            "rism": record.get(RISM_COLUMN),
            "title": record.get("Titel"),
            "partbooks": record.get("Stimmbücher"),
        }
    workbook.close()
    return descriptions


def attach_print_appearances(works, appearances):
    """Haengt die Drucknachweise als printAppearances an das jeweilige Werk.

    Gibt die Nachweise zurueck, deren Werk es nicht gibt (LV weder in
    Werke.xlsx noch in den Handschriften); sie werden nur gezaehlt.
    """
    by_id = {work["@id"]: work for work in works}
    unattached = []
    for item in appearances:
        if item["lv"]:
            work_id = "work:" + item["lv"]
        else:
            work_id = "work:anh-{0}".format(item["lvAnh"])
        work = by_id.get(work_id)
        if work is None:
            unattached.append(item)
            continue
        appearance = {"inPrint": "print:" + item["siglum"], "piece": item["piece"]}
        if item["note"]:
            appearance["note"] = item["note"]
        work["printAppearances"].append(appearance)
    for work in works:
        work["printAppearances"].sort(key=lambda a: print_sort_key(a["inPrint"][6:]))
    return unattached


def print_sort_key(siglum):
    """Sortiert Siglen nach Jahr, laufender Nummer und Teil."""
    parsed = parse_print(siglum)
    return (
        parsed["firstPrintYear"] or 0,
        parsed["firstPrintNo"] or 0,
        roman_to_int(parsed["part"]) if parsed["part"] else 0,
        siglum,
    )


def derive_works(entries, manuscripts):
    """Gruppiert Eintraege und Handschriften-Zeugnisse zu Werken.

    Schluessel ist zunaechst die LV-Nummer aus den Drucken, wie bisher. Zwei
    Faelle kommen durch die Handschriften hinzu: eine LV-Nummer, die im
    Druckkatalog gar nicht vorkommt (das Werk ist nur handschriftlich
    ueberliefert, erhaelt hier aber trotzdem einen Wertrag, wie im Katalog
    selbst ueblich), oder eine Nummer aus dem LV-Anhang fuer Stuecke ganz
    ausserhalb des Haupt-LV-Katalogs. Handschriften ohne LV und ohne
    Anhangsnummer bleiben unverknuepft; sie stehen trotzdem in
    manuscripts.json.

    Eintraege mit Fassungskennzeichnung wie "74 (IV)" bilden kein eigenes
    Werk, sondern eine Expression (FRBR) des Werks mit der Grundnummer, siehe
    derive_expressions und docs/entscheidungen.md, Abschnitt 17.
    """
    works = {}

    def new_work(lv, lv_base, lv_part, lv_anh):
        slug_source = lv if lv is not None else "anh-{0}".format(lv_anh)
        slug = re.sub(r"[^A-Za-z0-9]+", "-", slug_source).strip("-")
        return {
            "@id": "work:" + slug,
            "@type": "Work",
            "lv": lv,
            "lvBase": lv_base,
            "lvPart": lv_part,
            "lvAnh": lv_anh,
            "isPartOf": None,
            "hasPart": [],
            "titles": [],
            "voiceCounts": [],
            "prints": [],
            "printAppearances": [],
            "textAuthors": [],
            "uncertainTextAuthors": [],
            "textSources": [],
            "completeEditions": [],
            "genres": [],
            "languages": [],
            "entries": [],
            "manuscripts": [],
            "expressions": [],
        }

    for entry in entries:
        key = entry["lv"]
        if key is None or entry["lvVariant"] is not None:
            continue  # Fassungen werden in derive_expressions behandelt
        work = works.get(key)
        if work is None:
            work = new_work(key, entry["lvBase"], entry["lvPart"], None)
            works[key] = work
        collect_values(work, entry)
        work["entries"].append(entry["@id"])

    # Jede Fassung braucht ihr Werk, auch wenn die Grundnummer selbst in
    # keinem Druck vorkommt. Derzeit ist das nie der Fall, der Fall wird
    # trotzdem abgedeckt, damit keine Fassung ohne Werk bleibt.
    for entry in entries:
        if entry["lvVariant"] is not None:
            key = str(entry["lvBase"])
            if key not in works:
                works[key] = new_work(key, entry["lvBase"], None, None)

    by_anh = {}
    for manuscript in manuscripts:
        key = manuscript["lv"]
        if key is not None:
            work = works.get(key)
            if work is None:
                work = new_work(key, manuscript["lvBase"], manuscript["lvPart"], None)
                works[key] = work
        elif manuscript["lvAnh"] is not None:
            lv_anh = manuscript["lvAnh"]
            work = by_anh.get(lv_anh)
            if work is None:
                work = new_work(None, None, None, lv_anh)
                by_anh[lv_anh] = work
        else:
            continue  # keiner Nummer zuzuordnen, bleibt unverknuepft

        title = manuscript["title"]
        if title and title not in work["titles"]:
            work["titles"].append(title)
        voices = manuscript["voices"]
        if voices is not None and voices not in work["voiceCounts"]:
            work["voiceCounts"].append(voices)
        work["manuscripts"].append(manuscript["@id"])

    for work in by_anh.values():
        works[work["@id"]] = work  # eigener Namensraum (work:anh-*), keine Kollision mit LV-Schluesseln

    for work in works.values():
        work["voiceCounts"].sort()

    result = sorted(
        works.values(),
        key=lambda w: (
            0 if w["lvAnh"] is None else 1,
            w["lvBase"] or 0,
            w["lvPart"] or 0,
            w["lvAnh"] or 0,
        ),
    )
    link_parts(result)
    entry_by_id = {entry["@id"]: entry for entry in entries}
    manuscript_by_id = {manuscript["@id"]: manuscript for manuscript in manuscripts}
    for work in result:
        mark_uncertain_authors(work, entry_by_id)
    return [split_titles(work, entry_by_id, manuscript_by_id) for work in result]


def mark_uncertain_authors(item, entry_by_id):
    """Fuellt uncertainTextAuthors mit den Personen, deren Zuschreibung in
    allen Eintraegen des Werks bzw. der Fassung unsicher ist.

    textAuthors fuehrt Personen-IDs, nicht Rohwerte, und verliert damit das
    Fragezeichen aus einem Rohwert wie "Ludwig Helmbold?". Diese Liste haelt
    die Unsicherheit auf Werkebene fest. Bestaetigt auch nur ein Eintrag die
    Zuschreibung ohne Vorbehalt, gilt sie fuer das Werk als sicher.
    """
    for person_id in item["textAuthors"]:
        flags = [
            entry_by_id[entry_id]["textAuthorUncertain"]
            for entry_id in item["entries"]
            if entry_by_id[entry_id]["textAuthorPerson"] == person_id
        ]
        if flags and all(flags):
            item["uncertainTextAuthors"].append(person_id)


def link_parts(works):
    """Haelt die Teil-Beziehung ausdruecklich fest: isPartOf und hasPart.

    Ein Teilsatz wie "100-2" gehoert zum Werk mit der Grundnummer, "100".
    Bisher ergab sich das nur aus der Nummernlogik (lvBase/lvPart), die jeder
    Leser selbst nachbauen musste. Die Werke muessen bereits nach Teilnummer
    sortiert sein, damit hasPart in Katalogreihenfolge steht.
    """
    by_id = {work["@id"]: work for work in works}
    for work in works:
        if work["lvPart"] is None:
            continue
        base_id = "work:{0}".format(work["lvBase"])
        base = by_id.get(base_id)
        if base is None:
            raise ValueError(
                "Teil {0} ohne Gesamtwerk {1}".format(work["@id"], base_id)
            )
        work["isPartOf"] = base_id
        base["hasPart"].append(work["@id"])


def split_titles(item, entry_by_id, manuscript_by_id):
    """Ersetzt die Titelliste durch bevorzugten Titel und Varianten.

    Bevorzugt ist der normalisierte Titel der Eintraege, sofern alle
    Eintraege mit einem solchen Titel denselben tragen (Abschnitt 21).
    Andernfalls gilt der Titel des fruehesten Drucks (nach Jahr, dann
    laufender Nummer im Jahr), bei Werken ohne Druck der Titel der ersten
    Handschrift (Abschnitt 18). Die Titel der Drucke und Handschriften bleiben
    vollstaendig als Varianten in Quellreihenfolge erhalten.
    Gibt ein neues Objekt zurueck, damit die beiden Felder an der Stelle der
    bisherigen Titelliste stehen und die Ausgabe lesbar bleibt.
    """
    printed = sorted(
        (entry_by_id[entry_id] for entry_id in item["entries"]),
        key=lambda e: (
            e["firstPrintYear"] if e["firstPrintYear"] is not None else float("inf"),
            e["firstPrintNo"] if e["firstPrintNo"] is not None else float("inf"),
        ),
    )
    handwritten = [manuscript_by_id[m_id] for m_id in item.get("manuscripts", [])]
    candidates = [e["title"] for e in printed] + [m["title"] for m in handwritten]
    preferred = next((title for title in candidates if title), None)
    basis = "earliestSource" if preferred else None
    normalized = {e["normalizedTitle"] for e in printed if e.get("normalizedTitle")}
    if len(normalized) == 1:
        preferred = normalized.pop()
        basis = "normalized"

    result = {}
    for key, value in item.items():
        if key == "titles":
            result["preferredTitle"] = preferred
            result["preferredTitleBasis"] = basis
            result["variantTitles"] = [title for title in value if title != preferred]
        else:
            result[key] = value
    return result


# Felder eines Eintrags, die Werk und Expression als Liste ohne Dubletten
# sammeln: Eintragsfeld -> Listenfeld.
AGGREGATED_FIELDS = (
    ("title", "titles"),
    ("voices", "voiceCounts"),
    ("firstPrint", "prints"),
    ("textAuthorPerson", "textAuthors"),
    ("textSource", "textSources"),
    ("completeEdition", "completeEditions"),
    ("genre", "genres"),
    ("language", "languages"),
)


def collect_values(target, entry):
    """Uebernimmt die mehrwertigen Felder eines Eintrags ohne Dubletten."""
    for field, key in AGGREGATED_FIELDS:
        value = entry.get(field)
        if value is not None and value not in target[key]:
            target[key].append(value)


def derive_expressions(entries, works):
    """Bildet die Fassungen als Expressions (FRBR) und haengt sie ans Werk.

    Die Quelle kennzeichnet Fassungen mit einer roemischen Ziffer hinter der
    Grundnummer, etwa "193 (II)". Die Ziffer bezeichnet den Teil (Pars) des
    Werks, von dem eine abweichende Fassung existiert, meist in einem anderen
    Druck und mit anderer Stimmenzahl: "193 (II)" ist der zweite Teil von LV
    193 in sechsstimmiger Fassung von 1564, waehrend "193-2" denselben Teil
    fuenfstimmig im Druck von 1566 bringt.

    Die Expression verweist auf das Gesamtwerk (realizationOf), nicht auf den
    einzelnen Teil-Datensatz: Die Ziffer laesst sich nicht verlaesslich auf
    eine Teilnummer abbilden. Bei LV 74 etwa ist der Datensatz "74" die
    Ueberschrift "Sestina:", sodass "74 (III)" dem Teil "74-3" nicht
    entspricht, sondern "74-4". Die Ziffer bleibt als pars erhalten.
    """
    works_by_id = {work["@id"]: work for work in works}
    expressions = {}

    for entry in entries:
        variant = entry["lvVariant"]
        if variant is None:
            continue
        key = entry["lv"]
        expression = expressions.get(key)
        if expression is None:
            work_id = "work:{0}".format(entry["lvBase"])
            expression = {
                "@id": "expression:{0}-{1}".format(entry["lvBase"], variant),
                "@type": "Expression",
                "lv": key,
                "lvBase": entry["lvBase"],
                "pars": variant,
                "realizationOf": work_id,
                "titles": [],
                "voiceCounts": [],
                "prints": [],
                "textAuthors": [],
                "uncertainTextAuthors": [],
                "textSources": [],
                "completeEditions": [],
                "genres": [],
                "languages": [],
                "entries": [],
            }
            expressions[key] = expression
        collect_values(expression, entry)
        expression["entries"].append(entry["@id"])

    result = sorted(
        expressions.values(),
        key=lambda e: (e["lvBase"], roman_to_int(e["pars"])),
    )
    # Erst nach dem Sortieren verknuepfen, damit das Werk seine Fassungen in
    # Teilreihenfolge auflistet (III vor IV) statt in Quellreihenfolge.
    for expression in result:
        expression["voiceCounts"].sort()
        works_by_id[expression["realizationOf"]]["expressions"].append(expression["@id"])
    entry_by_id = {entry["@id"]: entry for entry in entries}
    for expression in result:
        mark_uncertain_authors(expression, entry_by_id)
    return [split_titles(expression, entry_by_id, {}) for expression in result]


def roman_to_int(numeral):
    """Wandelt eine roemische Ziffer in eine Zahl, fuer die Sortierung."""
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    for current, following in zip(numeral, numeral[1:] + " "):
        value = values[current]
        total += -value if values.get(following, 0) > value else value
    return total


def derive_prints(entries, appearances, descriptions):
    """Sammelt die Drucke als eigene Entitaet.

    Grundlage sind die Erstdrucke aus Werke.xlsx (entryCount) und alle Drucke
    aus den Drucknachweisen (auch Nachdrucke). Beschreibung, Verweise,
    RISM-Link, Titel und Stimmbuecher kommen aus dem Druckeverzeichnis.
    """
    prints = {}

    def get(siglum):
        item = prints.get(siglum)
        if item is None:
            parsed = parse_print(siglum)
            item = {
                "@id": "print:" + siglum,
                "@type": "Print",
                "siglum": siglum,
                "year": parsed["firstPrintYear"],
                "part": parsed["part"],
                "dateApproximate": False,
                "description": None,
                "references": {},
                "rism": None,
                "title": None,
                "partbooks": None,
                "entryCount": 0,
            }
            item.update(descriptions.get(siglum, {}))
            prints[siglum] = item
        return item

    for entry in entries:
        if entry.get("firstPrint"):
            get(entry["firstPrint"])["entryCount"] += 1
    for appearance in appearances:
        item = get(appearance["siglum"])
        if appearance["approximate"]:
            item["dateApproximate"] = True
    return sorted(prints.values(), key=lambda p: print_sort_key(p["siglum"]))


PERSON_AUTHORITIES_PATH = RAW_DIR / "personen_normdaten.json"


def load_person_authorities():
    """Laedt die manuell kuratierte GND/VIAF-Zuordnung fuer Textdichter.

    Eine reine Namensform-Zusammenfuehrung waere eine Zeichenkettenoperation;
    eine Normdatenverknuepfung ist dagegen eine fachliche Feststellung ueber
    eine bestimmte historische Person und wird deshalb nicht automatisch aus
    den Rohwerten erraten, siehe die Begruendung in docs/entscheidungen.md.
    Fehlt die Datei, laeuft der Import trotzdem durch, nur ohne Verknuepfung.
    """
    if not PERSON_AUTHORITIES_PATH.exists():
        return {}
    with PERSON_AUTHORITIES_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return {key: value for key, value in data.items() if not key.startswith("$")}


def derive_persons(entries):
    """Bildet die Textdichter als Personen und verknuepft die Eintraege damit.

    Rohwerte, die personen_normdaten.json einer GND zuordnet, werden zu einer
    Person mit festgelegter Anzeigeform (preferredName) zusammengefuehrt; ihre
    Schreibweisen aus der Quelle bleiben als variantNames erhalten. Die
    Zusammenfuehrung folgt allein dieser kuratierten Zuordnung, nie einem
    Namensvergleich, siehe docs/entscheidungen.md, Abschnitte 8, 15 und 19.
    Rohwerte ohne Zuordnung bleiben je eine eigene Person.

    Setzt an jedem Eintrag textAuthorPerson (Personen-ID) und
    textAuthorUncertain (Rohwert mit nachgestelltem "?"). Das "?" gehoert zur
    Zuschreibung, nicht zur Person, und entfaellt deshalb im Personennamen.
    Der Rohwert selbst bleibt in textAuthor unveraendert stehen.
    """
    person_by_raw = {}
    persons = {}
    for gnd, authority in load_person_authorities().items():
        person = {
            "@id": "person:gnd-" + gnd,
            "@type": "Person",
            "preferredName": authority["preferredName"],
            "variantNames": [],
            "gnd": "https://d-nb.info/gnd/" + gnd,
            "viaf": "https://viaf.org/viaf/" + authority["viaf"] if authority.get("viaf") else None,
        }
        persons[person["@id"]] = person
        for variant in authority["variants"]:
            if variant in person_by_raw:
                raise SystemExit(
                    "Rohwert {0!r} ist in personen_normdaten.json mehreren "
                    "Personen zugeordnet".format(variant)
                )
            person_by_raw[variant] = person

    used_raw = set()
    for entry in entries:
        name = entry.get("textAuthor")
        entry["textAuthorPerson"] = None
        entry["textAuthorUncertain"] = bool(name) and name.rstrip().endswith("?")
        if not name:
            continue
        name = name.rstrip().rstrip("?").rstrip()
        used_raw.add(name)
        person = person_by_raw.get(name)
        if person is None:
            # Ohne kuratierte Zuordnung: eine Person je Rohwert. Zwei Rohwerte,
            # die auf dieselbe ID fielen (etwa "G. Guéroult" und "G.Guéroult"),
            # wuerden sonst stillschweigend verschmolzen, daher der Abbruch.
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            person_id = "person:" + slug
            person = persons.get(person_id)
            if person is None:
                person = {
                    "@id": person_id,
                    "@type": "Person",
                    "preferredName": name,
                    "variantNames": [],
                    "gnd": None,
                    "viaf": None,
                }
                persons[person_id] = person
                person_by_raw[name] = person
            elif person["preferredName"] != name:
                raise SystemExit(
                    "Rohwerte {0!r} und {1!r} ergeben dieselbe Personen-ID {2}; "
                    "bitte in personen_normdaten.json zuordnen".format(
                        person["preferredName"], name, person_id
                    )
                )
        if name != person["preferredName"] and name not in person["variantNames"]:
            person["variantNames"].append(name)
        entry["textAuthorPerson"] = person["@id"]

    unused = sorted(set(person_by_raw) - used_raw)
    if unused:
        print("  Hinweis: Rohwerte aus personen_normdaten.json ohne Eintrag: {0}".format(unused))
    used_ids = {entry["textAuthorPerson"] for entry in entries}
    result = [person for person in persons.values() if person["@id"] in used_ids]
    for person in result:
        person["variantNames"].sort(key=str.lower)
    return sorted(result, key=lambda p: p["preferredName"].lower())


def validate_entries(entries):
    """Prueft jeden erzeugten Eintrag gegen schema/entry.schema.json.

    Bricht den Import ab, statt eine Datei zu schreiben, die dem eigenen
    Schema widerspricht. Ohne diese Pruefung waere das Schema nur
    Dokumentation, siehe die Diskussion dazu: ein Fehler im Mapping einer
    kuenftigen zweiten Quelle wuerde sonst still ein ungueltiges entries.json
    erzeugen, statt sofort aufzufallen.
    """
    with ENTRY_SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = jsonschema.Draft202012Validator(schema)

    errors = []
    for entry in entries:
        for error in validator.iter_errors(entry):
            errors.append((entry.get("@id"), error.message))

    if errors:
        print()
        print("Schema-Pruefung fehlgeschlagen, {0} Fehler:".format(len(errors)))
        for entry_id, message in errors[:20]:
            print("  {0}: {1}".format(entry_id, message))
        if len(errors) > 20:
            print("  ... und {0} weitere".format(len(errors) - 20))
        raise SystemExit(1)

    print("Schema-Pruefung bestanden, {0} Eintraege gegen {1}.".format(
        len(entries), ENTRY_SCHEMA_PATH.relative_to(ROOT)
    ))


def validate_manuscripts(manuscripts):
    """Prueft jedes Handschriften-Zeugnis gegen schema/manuscript.schema.json.

    Analog zu validate_entries, siehe dort fuer die Begruendung.
    """
    with MANUSCRIPT_SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = jsonschema.Draft202012Validator(schema)

    errors = []
    for manuscript in manuscripts:
        for error in validator.iter_errors(manuscript):
            errors.append((manuscript.get("@id"), error.message))

    if errors:
        print()
        print("Schema-Pruefung (Handschriften) fehlgeschlagen, {0} Fehler:".format(len(errors)))
        for manuscript_id, message in errors[:20]:
            print("  {0}: {1}".format(manuscript_id, message))
        if len(errors) > 20:
            print("  ... und {0} weitere".format(len(errors) - 20))
        raise SystemExit(1)

    print("Schema-Pruefung (Handschriften) bestanden, {0} Zeugnisse gegen {1}.".format(
        len(manuscripts), MANUSCRIPT_SCHEMA_PATH.relative_to(ROOT)
    ))


def write_json(filename, payload):
    """Schreibt stabil sortiertes, lesbares JSON fuer saubere Git-Diffs."""
    path = OUT_DIR / filename
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def main():
    OUT_DIR.mkdir(exist_ok=True)
    registry = load_registry()
    known_before = len(registry["assigned"])

    entries = []
    for spec in SOURCES:
        print("Lese {0} / {1}".format(spec["file"], spec["sheet"]))
        source_entries, new_ids = read_source(spec, registry)
        print(
            "  {0} Eintraege, davon {1} mit neu vergebener ID".format(
                len(source_entries), new_ids
            )
        )
        entries.extend(source_entries)

    manuscripts = []
    for spec in MANUSCRIPT_SOURCES:
        print("Lese {0} / {1}".format(spec["file"], spec["sheet"]))
        source_manuscripts, new_ids = read_manuscripts(spec, registry)
        print(
            "  {0} Zeugnisse, davon {1} mit neu vergebener ID".format(
                len(source_manuscripts), new_ids
            )
        )
        manuscripts.extend(source_manuscripts)

    spec = PRINT_APPEARANCE_SOURCE
    print("Lese {0} / {1}".format(spec["file"], spec["sheet"]))
    appearances = read_print_appearances(spec)
    print("  {0} Drucknachweise".format(len(appearances)))
    spec = PRINT_SOURCE
    print("Lese {0} / {1}".format(spec["file"], spec["sheet"]))
    print_descriptions = read_print_descriptions(spec)
    print("  {0} Drucke".format(len(print_descriptions)))

    # Nach der laufenden Nummer in der @id, numerisch, damit die Reihenfolge
    # auch ueber fuenf Stellen hinaus stimmt.
    entries.sort(key=lambda e: int(e["@id"].split(":")[1]))
    manuscripts.sort(key=lambda m: int(m["@id"].split(":")[1]))
    # Vor der Schema-Pruefung, weil derive_persons die Personenfelder an den
    # Eintraegen setzt und diese mitgeprueft werden sollen.
    persons = derive_persons(entries)
    validate_entries(entries)
    validate_manuscripts(manuscripts)
    save_registry(registry)

    works = derive_works(entries, manuscripts)
    expressions = derive_expressions(entries, works)
    unattached = attach_print_appearances(works, appearances)
    prints = derive_prints(entries, appearances, print_descriptions)
    unclassified_count = len([m for m in manuscripts if m["lv"] is None and m["lvAnh"] is None])

    write_json("entries.json", {"@context": CONTEXT_URL, "items": entries})
    write_json("manuscripts.json", {"@context": CONTEXT_URL, "items": manuscripts})
    write_json("works.json", {"@context": CONTEXT_URL, "items": works})
    write_json("expressions.json", {"@context": CONTEXT_URL, "items": expressions})
    write_json("prints.json", {"@context": CONTEXT_URL, "items": prints})
    write_json("persons.json", {"@context": CONTEXT_URL, "items": persons})

    multi = [w for w in works if len(w["entries"]) > 1]
    with_manuscripts = [w for w in works if w["manuscripts"]]
    print()
    print("Eintraege     : {0}".format(len(entries)))
    print("Handschriften : {0}, davon {1} ohne Zuordnung".format(
        len(manuscripts), unclassified_count
    ))
    print(
        "Werke         : {0}, davon {1} in mehreren Drucken, {2} mit Handschriften bezeugt".format(
            len(works), len(multi), len(with_manuscripts)
        )
    )
    print("Fassungen     : {0} (Expressions zu {1} Werken)".format(
        len(expressions), len({e["realizationOf"] for e in expressions})
    ))
    print("Drucke        : {0}, davon {1} Erstdrucke lt. Werke.xlsx".format(
        len(prints), len([p for p in prints if p["entryCount"]])
    ))
    print("Drucknachweise: {0} an Werken, {1} ohne Werk ({2})".format(
        len(appearances) - len(unattached), len(unattached),
        ", ".join(sorted({a["lv"] or "anh-{0}".format(a["lvAnh"]) for a in unattached})[:10]) or "-",
    ))
    print("Textdichter   : {0}".format(len(persons)))
    print(
        "Interne IDs   : {0} vergeben, {1} davon neu, naechste freie ID {2}".format(
            len(registry["assigned"]),
            len(registry["assigned"]) - known_before,
            registry["nextId"],
        )
    )
    print("Geschrieben nach {0}".format(OUT_DIR))


if __name__ == "__main__":
    main()
