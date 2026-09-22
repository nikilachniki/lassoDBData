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
MANUSCRIPT_SCHEMA_PATH = SCHEMA_DIR / "manuscript.schema.json"

# Pfad, unter dem entries.json ihr Schema findet. Relativ statt als GitHub-URL,
# damit die Pruefung im Editor auch offline funktioniert und nicht von der
# Erreichbarkeit von GitHub abhaengt. Zeigt auf das Huellenschema, nicht direkt
# auf entry.schema.json: dieses beschreibt einen einzelnen Eintrag, nicht die
# Datei mit @context und items drumherum.
ENTRIES_FILE_SCHEMA_RELATIVE = "../schema/entries-file.schema.json"
MANUSCRIPTS_FILE_SCHEMA_RELATIVE = "../schema/manuscripts-file.schema.json"

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
            "Quellenart": "sourceDescription",
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


def read_manuscripts(spec, registry):
    """Liest eine registrierte Handschriften-Quelle und liefert Zeugnisse.

    Anders als bei den Drucken steckt die Teilsatznummer nicht in der
    LV-Schreibweise ("100-2"), sondern in einer eigenen Spalte (Unternummer),
    und es gibt keine Fassungskennzeichnung wie "74 (IV)". Fehlt die
    LV-Nummer, verweist das Freitextfeld "Weitere Teile" manchmal auf eine
    Nummer im LV-Anhang (etwa "vgl. LVanh 98"); die wird hier erkannt, damit
    auch diese Stuecke spaeter zu einem Werk gruppiert werden koennen. Fehlen
    beide, bleibt die Zeile unverknuepft, wird aber nicht verworfen, siehe
    write_unclassified_report.
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
            "id": internal_id,
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
            "sourceDescription": record.get("sourceDescription"),
            "provenance": record.get("provenance"),
            "sourceNote": record.get("sourceNote"),
            "literature": record.get("literature"),
            "note": note,
            "source": {
                "dataset": spec["id"],
                "file": spec["file"],
                "row": row_no,
                "key": key,
            },
        }
        if voices_raw:
            manuscript["voicesRaw"] = voices_raw
        if extra:
            manuscript["extra"] = extra
        manuscripts.append(manuscript)

    workbook.close()
    return manuscripts, new_ids


def derive_works(entries, manuscripts):
    """Gruppiert Eintraege und Handschriften-Zeugnisse zu Werken.

    Schluessel ist zunaechst die LV-Nummer aus den Drucken, wie bisher. Zwei
    Faelle kommen durch die Handschriften hinzu: eine LV-Nummer, die im
    Druckkatalog gar nicht vorkommt (das Werk ist nur handschriftlich
    ueberliefert, erhaelt hier aber trotzdem einen Wertrag, wie im Katalog
    selbst ueblich), oder eine Nummer aus dem LV-Anhang fuer Stuecke ganz
    ausserhalb des Haupt-LV-Katalogs. Handschriften ohne LV und ohne
    Anhangsnummer bleiben unverknuepft; sie stehen trotzdem in
    manuscripts.json, siehe write_unclassified_report.
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

    def new_work(lv, lv_base, lv_part, lv_variant, lv_anh):
        slug_source = lv if lv is not None else "anh-{0}".format(lv_anh)
        slug = re.sub(r"[^A-Za-z0-9]+", "-", slug_source).strip("-")
        return {
            "@id": "work:" + slug,
            "@type": "Work",
            "lv": lv,
            "lvBase": lv_base,
            "lvPart": lv_part,
            "lvVariant": lv_variant,
            "lvAnh": lv_anh,
            "titles": [],
            "voiceCounts": [],
            "prints": [],
            "textAuthors": [],
            "textSources": [],
            "completeEditions": [],
            "entries": [],
            "manuscripts": [],
        }

    for entry in entries:
        key = entry["lv"]
        if key is None:
            continue
        work = works.get(key)
        if work is None:
            work = new_work(key, entry["lvBase"], entry["lvPart"], entry["lvVariant"], None)
            works[key] = work
        for field, target in collect:
            value = entry.get(field)
            if value is not None and value not in work[target]:
                work[target].append(value)
        work["entries"].append(entry["@id"])

    by_anh = {}
    for manuscript in manuscripts:
        key = manuscript["lv"]
        if key is not None:
            work = works.get(key)
            if work is None:
                work = new_work(key, manuscript["lvBase"], manuscript["lvPart"], None, None)
                works[key] = work
        elif manuscript["lvAnh"] is not None:
            lv_anh = manuscript["lvAnh"]
            work = by_anh.get(lv_anh)
            if work is None:
                work = new_work(None, None, None, None, lv_anh)
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
        work["entryCount"] = len(work["entries"])
        work["voiceCounts"].sort()

    return sorted(
        works.values(),
        key=lambda w: (
            0 if w["lvAnh"] is None else 1,
            w["lvBase"] or 0,
            w["lvPart"] or 0,
            w["lvVariant"] or "",
            w["lvAnh"] or 0,
        ),
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
    """Sammelt die Textdichter als Rohwerte.

    Abweichende Schreibweisen werden bewusst nicht automatisch zusammengefuehrt.
    Das bleibt eine redaktionelle Entscheidung. Fuer namentlich eindeutig
    identifizierte Personen liefert personen_normdaten.json GND und VIAF,
    siehe load_person_authorities.
    """
    authorities = load_person_authorities()
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
            authority = authorities.get(name, {})
            item = {
                "@id": "person:" + slug,
                "@type": "Person",
                "nameRaw": name,
                "role": "textAuthor",
                "gnd": authority.get("gnd"),
                "viaf": authority.get("viaf"),
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
            errors.append((manuscript.get("id"), manuscript.get("@id"), error.message))

    if errors:
        print()
        print("Schema-Pruefung (Handschriften) fehlgeschlagen, {0} Fehler:".format(len(errors)))
        for internal_id, manuscript_id, message in errors[:20]:
            print("  id {0} ({1}): {2}".format(internal_id, manuscript_id, message))
        if len(errors) > 20:
            print("  ... und {0} weitere".format(len(errors) - 20))
        raise SystemExit(1)

    print("Schema-Pruefung (Handschriften) bestanden, {0} Zeugnisse gegen {1}.".format(
        len(manuscripts), MANUSCRIPT_SCHEMA_PATH.relative_to(ROOT)
    ))


def write_unclassified_report(manuscripts):
    """Schreibt eine Liste der Handschriften-Zeilen ohne LV- oder
    Anhangsnummer nach docs/, damit sie spaeter von Hand zugeordnet werden
    koennen, statt beim Import stillschweigend zu verschwinden.

    Wird bei jedem Lauf ueberschrieben. Kein Ort fuer manuelle Ergaenzungen:
    eine Zuordnung gehoert in raw/lasso_handschriften.xlsx selbst, als
    LV-Nummer oder als Verweis auf eine LVanh-Nummer in "Weitere Teile".
    """
    unclassified = [m for m in manuscripts if m["lv"] is None and m["lvAnh"] is None]
    lines = [
        "# Handschriften ohne LV- oder Anhangsnummer",
        "",
        "Automatisch erzeugt von `scripts/import_excel.py`, bei jedem Import",
        "ueberschrieben. Nicht von Hand bearbeiten. Eine Zuordnung gehoert in",
        "`raw/lasso_handschriften.xlsx`, entweder als Eintrag in der Spalte",
        "LV oder als Verweis auf eine LVanh-Nummer in der Spalte 'Weitere Teile'.",
        "",
        "{0} von {1} Handschriften-Zeugnissen sind (noch) keinem Werk zugeordnet.".format(
            len(unclassified), len(manuscripts)
        ),
        "",
        "| Titel | Ort | Bibliothek | Signatur | Stimmen |",
        "| --- | --- | --- | --- | --- |",
    ]
    for manuscript in sorted(unclassified, key=lambda m: (m["title"] or "").lower()):
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} |".format(
                (manuscript["title"] or "").replace("|", "\\|"),
                (manuscript["place"] or "").replace("|", "\\|"),
                (manuscript["library"] or "").replace("|", "\\|"),
                (manuscript["shelfmark"] or "").replace("|", "\\|"),
                manuscript["voices"] if manuscript["voices"] is not None else "",
            )
        )

    path = ROOT / "docs" / "handschriften-ohne-zuordnung.md"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return path, len(unclassified)


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

    manuscripts = []
    for spec in MANUSCRIPT_SOURCES:
        path = RAW_DIR / spec["file"]
        print("Lese {0} / {1}".format(spec["file"], spec["sheet"]))
        source_manuscripts, new_ids = read_manuscripts(spec, registry)
        print(
            "  {0} Zeugnisse, davon {1} mit neu vergebener ID".format(
                len(source_manuscripts), new_ids
            )
        )
        manuscripts.extend(source_manuscripts)
        provenance.append(
            {
                "dataset": spec["id"],
                "file": spec["file"],
                "sheet": spec["sheet"],
                "sha256": file_digest(path),
                "entries": len(source_manuscripts),
            }
        )

    entries.sort(key=lambda e: e["id"])
    manuscripts.sort(key=lambda m: m["id"])
    validate_entries(entries)
    validate_manuscripts(manuscripts)
    save_registry(registry)

    works = derive_works(entries, manuscripts)
    prints = derive_prints(entries)
    persons = derive_persons(entries)
    report_path, unclassified_count = write_unclassified_report(manuscripts)

    write_json(
        "entries.json",
        {
            "$schema": ENTRIES_FILE_SCHEMA_RELATIVE,
            "@context": CONTEXT_URL,
            "items": entries,
        },
    )
    write_json(
        "manuscripts.json",
        {
            "$schema": MANUSCRIPTS_FILE_SCHEMA_RELATIVE,
            "@context": CONTEXT_URL,
            "items": manuscripts,
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
                "manuscripts": len(manuscripts),
                "manuscriptsUnclassified": unclassified_count,
                "works": len(works),
                "worksFromManuscriptsOnly": len(
                    [w for w in works if not w["entries"] and w["manuscripts"]]
                ),
                "worksInAppendix": len([w for w in works if w["lvAnh"] is not None]),
                "prints": len(prints),
                "persons": len(persons),
                "idsAssigned": len(registry["assigned"]),
                "nextId": registry["nextId"],
            },
            "sources": provenance,
        },
    )

    multi = [w for w in works if w["entryCount"] > 1]
    with_manuscripts = [w for w in works if w["manuscripts"]]
    print()
    print("Eintraege     : {0}".format(len(entries)))
    print("Handschriften : {0}, davon {1} ohne Zuordnung ({2})".format(
        len(manuscripts), unclassified_count, report_path.relative_to(ROOT)
    ))
    print(
        "Werke         : {0}, davon {1} in mehreren Drucken, {2} mit Handschriften bezeugt".format(
            len(works), len(multi), len(with_manuscripts)
        )
    )
    print("Drucke        : {0}".format(len(prints)))
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
