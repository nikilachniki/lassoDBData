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

import hashlib
import json
import re
from datetime import date
from pathlib import Path

import jsonschema
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
OUT_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schema"
REGISTRY_PATH = OUT_DIR / "id-registry.json"
ENTRY_SCHEMA_PATH = SCHEMA_DIR / "entry.schema.json"

# Pfad, unter dem entries.json ihr Schema findet. Relativ statt als GitHub-URL,
# damit die Pruefung im Editor auch offline funktioniert und nicht von der
# Erreichbarkeit von GitHub abhaengt. Zeigt auf das Huellenschema, nicht direkt
# auf entry.schema.json: dieses beschreibt einen einzelnen Eintrag, nicht die
# Datei mit @context und items drumherum.
ENTRIES_FILE_SCHEMA_RELATIVE = "../schema/entries-file.schema.json"

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
        },
    },
]

# LV-Nummer: Grundnummer, optionaler Teilsatz (1-2), optionale Fassung (74 (IV))
RE_LV_PART = re.compile(r"^(\d+)-(\d+)$")
RE_LV_VARIANT = re.compile(r"^(\d+)\s*\(([IVXLC]+)\)$")
RE_LV_PLAIN = re.compile(r"^(\d+)$")
# Erstdruck-Sigle: Jahr und laufende Nummer innerhalb des Jahres, z.B. 1555-1
RE_PRINT = re.compile(r"^(\d{4})-(\d+)$")
# Fuehrende Teilsatz-Markierung im Titel, z.B. "[2] Tengan dunque"
RE_TITLE_PART = re.compile(r"^\[(\d+)\]\s*")


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
    """Zerlegt die Erstdruck-Sigle in Jahr und laufende Nummer."""
    if not raw:
        return {"firstPrint": None, "firstPrintYear": None, "firstPrintNo": None}
    match = RE_PRINT.match(raw)
    if not match:
        return {"firstPrint": raw, "firstPrintYear": None, "firstPrintNo": None}
    return {
        "firstPrint": raw,
        "firstPrintYear": int(match.group(1)),
        "firstPrintNo": int(match.group(2)),
    }


def parse_voices(raw):
    """Liest die Stimmenzahl als Ganzzahl, behaelt den Rohwert bei Abweichung."""
    if not raw:
        return None, None
    if raw.isdigit():
        return int(raw), None
    return None, raw


def parse_title(raw):
    """Trennt die Teilsatz-Markierung vom eigentlichen Titel."""
    if not raw:
        return None, None
    stripped = RE_TITLE_PART.sub("", raw).strip()
    return (stripped or None), raw


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
        title, title_raw = parse_title(record.get("title"))
        key = natural_key(
            spec["id"], lv_parts["lv"], print_parts["firstPrint"], seen_keys
        )
        internal_id, is_new = assign_id(registry, key)
        if is_new:
            new_ids += 1

        entry = {
            "@id": "entry:{0:05d}".format(internal_id),
            "@type": "CatalogueEntry",
            "id": internal_id,
            "lv": lv_parts["lv"],
            "lvBase": lv_parts["lvBase"],
            "lvPart": lv_parts["lvPart"],
            "lvVariant": lv_parts["lvVariant"],
            "title": title,
            "titleRaw": title_raw,
            "voices": voices,
            "firstPrint": print_parts["firstPrint"],
            "firstPrintYear": print_parts["firstPrintYear"],
            "firstPrintNo": print_parts["firstPrintNo"],
            "textAuthor": record.get("textAuthor"),
            "textSource": record.get("textSource"),
            "completeEdition": record.get("completeEdition"),
            "note": record.get("note"),
            "source": {
                "dataset": spec["id"],
                "file": spec["file"],
                "row": row_no,
                "key": key,
            },
        }
        if voices_raw:
            entry["voicesRaw"] = voices_raw
        if extra:
            entry["extra"] = extra
        entries.append(entry)

    workbook.close()
    return entries, new_ids


def derive_works(entries):
    """Gruppiert die Eintraege zu Werken.

    Schluessel ist die LV-Nummer, die dieselbe Komposition ueber mehrere
    Drucke hinweg zusammenhaelt.
    """
    works = {}
    collect = (
        ("title", "titles"),
        ("voices", "voiceCounts"),
        ("firstPrint", "prints"),
        ("textAuthor", "textAuthors"),
        ("textSource", "textSources"),
        ("completeEdition", "completeEditions"),
    )

    for entry in entries:
        key = entry["lv"]
        if key is None:
            continue
        work = works.get(key)
        if work is None:
            slug = re.sub(r"[^A-Za-z0-9]+", "-", key).strip("-")
            work = {
                "@id": "work:" + slug,
                "@type": "Work",
                "lv": key,
                "lvBase": entry["lvBase"],
                "lvPart": entry["lvPart"],
                "lvVariant": entry["lvVariant"],
                "titles": [],
                "voiceCounts": [],
                "prints": [],
                "textAuthors": [],
                "textSources": [],
                "completeEditions": [],
                "entries": [],
            }
            works[key] = work
        for field, target in collect:
            value = entry.get(field)
            if value is not None and value not in work[target]:
                work[target].append(value)
        work["entries"].append(entry["@id"])

    for work in works.values():
        work["entryCount"] = len(work["entries"])
        work["voiceCounts"].sort()

    return sorted(
        works.values(),
        key=lambda w: (w["lvBase"] or 0, w["lvPart"] or 0, w["lvVariant"] or ""),
    )


def derive_prints(entries):
    """Sammelt die Erstdrucke als eigene Entitaet."""
    prints = {}
    for entry in entries:
        siglum = entry.get("firstPrint")
        if not siglum:
            continue
        item = prints.get(siglum)
        if item is None:
            item = {
                "@id": "print:" + siglum,
                "@type": "Print",
                "siglum": siglum,
                "year": entry.get("firstPrintYear"),
                "no": entry.get("firstPrintNo"),
                "rism": None,
                "entryCount": 0,
            }
            prints[siglum] = item
        item["entryCount"] += 1
    return sorted(
        prints.values(), key=lambda p: (p["year"] or 0, p["no"] or 0, p["siglum"])
    )


def derive_persons(entries):
    """Sammelt die Textdichter als Rohwerte.

    Abweichende Schreibweisen werden bewusst nicht automatisch zusammengefuehrt.
    Das bleibt eine redaktionelle Entscheidung und gehoert spaeter in eine
    gepflegte Normdatei mit GND- und VIAF-Verknuepfung.
    """
    persons = {}
    for entry in entries:
        name = entry.get("textAuthor")
        if not name:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            continue
        item = persons.get(slug)
        if item is None:
            item = {
                "@id": "person:" + slug,
                "@type": "Person",
                "nameRaw": name,
                "role": "textAuthor",
                "gnd": None,
                "viaf": None,
                "entryCount": 0,
            }
            persons[slug] = item
        item["entryCount"] += 1
    return sorted(persons.values(), key=lambda p: p["nameRaw"].lower())


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
            errors.append((entry.get("id"), entry.get("@id"), error.message))

    if errors:
        print()
        print("Schema-Pruefung fehlgeschlagen, {0} Fehler:".format(len(errors)))
        for internal_id, entry_id, message in errors[:20]:
            print("  id {0} ({1}): {2}".format(internal_id, entry_id, message))
        if len(errors) > 20:
            print("  ... und {0} weitere".format(len(errors) - 20))
        raise SystemExit(1)

    print("Schema-Pruefung bestanden, {0} Eintraege gegen {1}.".format(
        len(entries), ENTRY_SCHEMA_PATH.relative_to(ROOT)
    ))


def write_json(filename, payload):
    """Schreibt stabil sortiertes, lesbares JSON fuer saubere Git-Diffs."""
    path = OUT_DIR / filename
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def file_digest(path):
    """Pruefsumme der Quelldatei, damit die Herkunft nachvollziehbar bleibt."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    registry = load_registry()
    known_before = len(registry["assigned"])

    entries = []
    provenance = []
    for spec in SOURCES:
        path = RAW_DIR / spec["file"]
        print("Lese {0} / {1}".format(spec["file"], spec["sheet"]))
        source_entries, new_ids = read_source(spec, registry)
        print(
            "  {0} Eintraege, davon {1} mit neu vergebener ID".format(
                len(source_entries), new_ids
            )
        )
        entries.extend(source_entries)
        provenance.append(
            {
                "dataset": spec["id"],
                "file": spec["file"],
                "sheet": spec["sheet"],
                "sha256": file_digest(path),
                "entries": len(source_entries),
            }
        )

    entries.sort(key=lambda e: e["id"])
    validate_entries(entries)
    save_registry(registry)

    works = derive_works(entries)
    prints = derive_prints(entries)
    persons = derive_persons(entries)

    write_json(
        "entries.json",
        {
            "$schema": ENTRIES_FILE_SCHEMA_RELATIVE,
            "@context": CONTEXT_URL,
            "items": entries,
        },
    )
    write_json("works.json", {"@context": CONTEXT_URL, "items": works})
    write_json("prints.json", {"@context": CONTEXT_URL, "items": prints})
    write_json("persons.json", {"@context": CONTEXT_URL, "items": persons})
    write_json(
        "meta.json",
        {
            "generated": date.today().isoformat(),
            "generator": "scripts/import_excel.py",
            "context": CONTEXT_URL,
            "counts": {
                "entries": len(entries),
                "works": len(works),
                "prints": len(prints),
                "persons": len(persons),
                "idsAssigned": len(registry["assigned"]),
                "nextId": registry["nextId"],
            },
            "sources": provenance,
        },
    )

    multi = [w for w in works if w["entryCount"] > 1]
    print()
    print("Eintraege   : {0}".format(len(entries)))
    print(
        "Werke       : {0}, davon {1} in mehreren Drucken".format(
            len(works), len(multi)
        )
    )
    print("Drucke      : {0}".format(len(prints)))
    print("Textdichter : {0}".format(len(persons)))
    print(
        "Interne IDs : {0} vergeben, {1} davon neu, naechste freie ID {2}".format(
            len(registry["assigned"]),
            len(registry["assigned"]) - known_before,
            registry["nextId"],
        )
    )
    print("Geschrieben nach {0}".format(OUT_DIR))


if __name__ == "__main__":
    main()
