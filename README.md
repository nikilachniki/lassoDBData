# lassoDBData

Datenbestand zum Werkverzeichnis von Orlando di Lasso. Dieses Repository enthält
ausschließlich die Daten, die Importwerkzeuge und das Schema. Die Weboberfläche
liegt getrennt in [lassoDB](https://github.com/nikilachniki/lassoDB).

## Aufbau

| Ordner    | Inhalt                                                          |
| --------- | --------------------------------------------------------------- |
| `raw/`    | Original-Excel-Dateien, unverändert als Quellennachweis          |
| `scripts/`| Importskript, das aus `raw/` die Dateien in `data/` erzeugt      |
| `schema/` | JSON-LD-Kontext und JSON-Schema                                  |
| `data/`   | Erzeugte JSON-LD-Dateien, der eigentliche Datenbestand           |
| `docs/`   | Begründung der Technologieentscheidungen                         |

Warum das Projekt so aufgebaut ist, wie es aufgebaut ist, steht in
[docs/entscheidungen.md](docs/entscheidungen.md).

Die Dateien in `data/` werden vom Importskript geschrieben und nicht von Hand
bearbeitet. Korrekturen gehören in die Quelldatei oder in das Mapping des
Importskripts, danach wird der Import erneut ausgeführt.

## Datenmodell

Ein Datensatz in `entries.json` ist **ein Werk in einem Druck**, nicht ein Werk.
Das ist der wichtigste Punkt am Modell: Die LV-Nummer ist nicht eindeutig. 32
LV-Nummern kommen mehrfach vor, weil dieselbe Komposition in mehreren Drucken
erscheint, teils mit abweichender Stimmenzahl und abweichender Titelschreibung.

Eindeutig ist allein die **interne ID**, eine fortlaufende Nummer. Sie wird in
`data/id-registry.json` festgehalten und bleibt über alle späteren Importe
hinweg stabil. Einmal vergebene IDs werden nie neu vergeben, auch dann nicht,
wenn ein Datensatz später entfällt. Nur so bleiben veröffentlichte Verweise
gültig, wenn neue Daten dazukommen.

Erzeugte Dateien:

- `entries.json` ist der verlustfreie Kern, eine Zeile der Quelle je Datensatz.
- `works.json` fasst Einträge über die LV-Nummer zu Werken zusammen.
- `prints.json` listet die Erstdrucke als eigene Entität.
- `persons.json` listet die Textdichter, vorerst als Rohwerte.
- `meta.json` enthält Zählungen, Erzeugungsdatum und Prüfsummen der Quellen.

Alle Dateien tragen einen Verweis auf `schema/context.jsonld` und sind damit als
JSON-LD lesbar. Sie lassen sich mit Standardwerkzeugen nach RDF überführen, ohne
dass im Alltag ein Triple Store betrieben werden muss.

## Import ausführen

Voraussetzung ist Python mit openpyxl.

```bash
pip install openpyxl
python scripts/import_excel.py
```

Das Skript ist wiederholbar. Ein erneuter Lauf über unveränderte Quellen erzeugt
identische Ausgaben und vergibt keine neuen IDs.

## Eine weitere Excel-Tabelle aufnehmen

Tabellen mit abweichenden Spalten sind vorgesehen. Nötig sind zwei Schritte:

1. Die Datei nach `raw/` legen.
2. In `scripts/import_excel.py` einen Eintrag zu `SOURCES` ergänzen, mit eigener
   `id`, Dateiname, Blattname und einem `columns`-Mapping von Spaltenkopf auf
   kanonisches Feld.

Spalten, die im Mapping fehlen, gehen nicht verloren. Sie landen im Feld `extra`
des jeweiligen Datensatzes und können später in das Kernmodell hochgezogen
werden. Ein Schemawechsel oder eine Migration ist dafür nicht nötig.

## Offene redaktionelle Punkte

- Textdichter stehen als Rohwerte nebeneinander, etwa `Marot` und `C.Marot`.
  Eine automatische Zusammenführung wäre eine inhaltliche Entscheidung und
  unterbleibt bewusst. Die Felder `gnd` und `viaf` in `persons.json` sind für
  die spätere Normdatenverknüpfung vorbereitet und derzeit leer.
- Einzelne Titel enthalten ein Kreuzzeichen aus der TeX-Vorlage, etwa
  `Moresca quarta D'orlando.†`. Die Bedeutung ist zu klären, bevor es entfernt
  wird.
- Ein Titel enthält eine auffällige Leerstelle, `Rendz moy mo cœ ur à cinq`.
  Vermutlich ein Artefakt der Vorlage.
- Das Feld `rism` in `prints.json` ist für die Verknüpfung mit dem
  Répertoire International des Sources Musicales vorgesehen und noch leer.

## Lizenz

Die Daten in `raw/` und `data/` stehen unter CC BY 4.0, siehe `LICENSE`. Das
Importskript in `scripts/` steht unter der MIT-Lizenz. Bei Nachnutzung der Daten
bitte das Repository und die zugrunde liegende Katalogquelle nennen.
