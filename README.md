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

## Validierung

`entries.json` trägt zusätzlich `$schema`, einen Verweis auf
`schema/entries-file.schema.json`. Das ist die Hülle um die Datei, mit
`@context` und `items`; die einzelnen Einträge darin sind über `$ref` an
`schema/entry.schema.json` gebunden, das eigentliche Modell eines
Katalogeintrags. Ein Editor mit JSON-Schema-Unterstützung, etwa VS Code,
prüft `entries.json` damit beim Öffnen automatisch und live, ganz ohne
Skriptaufruf.

Das Importskript prüft zusätzlich jeden erzeugten Eintrag selbst gegen
`entry.schema.json`, bevor es irgendetwas schreibt. Ein Mapping-Fehler bei
einer künftigen zweiten Quelle bricht den Import damit sofort mit einer
Fehlermeldung ab, statt still eine ungültige Datei zu erzeugen.

## Import ausführen

Voraussetzung ist Python mit openpyxl und jsonschema.

```bash
pip install -r scripts/requirements.txt
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
- LV 74 legt eine Lücke im automatischen Gruppieren offen: die Einträge
  `74-4` und `74-5` tragen als einzige der ganzen Tabelle eine Bemerkung, die
  auf einen früheren Erstdruck verweist als den der Zeile selbst. Die Titel
  von `74 (III)` und `74 (IV)`, jeweils unter ihrem eigenen, früheren
  Erstdruck katalogisiert, stimmen fast wörtlich mit denen von `74-4` und
  `74-5` überein. Vermutlich sind es dieselben Stücke, einmal unter der
  späteren Sammeldrucknummer, einmal unter der früheren Einzeldrucknummer.
  `works.json` gruppiert aber strikt nach der wörtlichen LV-Zeichenkette und
  hält sie deshalb für vier getrennte Werke statt für zwei. Eine inhaltliche
  Prüfung und gegebenenfalls eine explizite Verknüpfung stehen aus.
- Das Blatt `Hinweise` in `raw/Werke.xlsx` behauptet `Datensätze: 309`. Das
  deckt sich mit keiner in den Daten nachvollziehbaren Zählung, weder mit den
  1979 Zeilen insgesamt, noch mit den 1209 Hauptzeilen ohne Bindestrich, noch
  mit den 137 Drucken oder den 1945 Werken. Vermutlich ein Überbleibsel aus
  einem früheren Stand der Quelldatei, nicht durch den Import verursacht.

## Lizenz

Die Daten in `raw/` und `data/` stehen unter CC BY 4.0, siehe `LICENSE`. Das
Importskript in `scripts/` steht unter der MIT-Lizenz. Bei Nachnutzung der Daten
bitte das Repository und die zugrunde liegende Katalogquelle nennen.
