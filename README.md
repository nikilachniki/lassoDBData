# lassoDBData

Datenbestand zum Werkverzeichnis von Orlando di Lasso. Dieses Repository enthält
ausschließlich die Daten, das Importskript und das Schema. Die Weboberfläche
liegt getrennt in [lassoDB](https://github.com/nikilachniki/lassoDB).

## Aufbau

| Ordner    | Inhalt                                                          |
| --------- | --------------------------------------------------------------- |
| `raw/`    | Quelldateien des Imports: drei Excel-Tabellen und die GND-Zuordnung |
| `scripts/`| Importskript, das aus `raw/` die Dateien in `data/` erzeugt, und die ID-Registry |
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

Analog dazu ist ein Datensatz in `manuscripts.json` **ein Werk in einer
Handschrift**, ebenfalls nicht das Werk selbst. Eine Handschriften-Quelle
(RISM-Sigel plus Signatur) kann mehrere Lasso-Stücke enthalten, und dasselbe
Stück kann in mehreren Handschriften überliefert sein.

Eindeutig ist allein die **interne ID**, eine fortlaufende Nummer, für Drucke
und Handschriften gemeinsam vergeben. Sie steht in der `@id` des Datensatzes,
etwa `entry:00001` oder `manuscript:01980`. Sie wird in `scripts/id-registry.json`
festgehalten und bleibt über alle späteren Importe hinweg stabil. Einmal
vergebene IDs werden nie neu vergeben, auch dann nicht, wenn ein Datensatz
später entfällt. Nur so bleiben veröffentlichte Verweise gültig, wenn neue
Daten dazukommen.

**LV-Anhang.** Nicht jedes handschriftlich überlieferte Stück steht im
Haupt-LV-Katalog. Für diese Fälle verweist die Quelltabelle im Freitext auf
eine Nummer aus dem LV-Anhang (Boetticher), etwa „vgl. LVanh 98“. Solche Werke
tragen `lv: null` und stattdessen `lvAnh`, ihre `@id` beginnt mit `work:anh-`
statt mit der LV-Nummer. Bleibt auch das aus, ist die Handschriften-Zeile
keinem Werk zuzuordnen; sie geht dadurch nicht verloren, sondern erscheint in
`manuscripts.json` mit `lv: null` und `lvAnh: null`. Zuordnen lässt sie sich
in `raw/lasso_handschriften.xlsx`, gefiltert nach leerer Spalte „LV“.

Erzeugte Dateien:

- `entries.json` ist der verlustfreie Kern der Drucküberlieferung, eine Zeile
  der Quelle je Datensatz.
- `manuscripts.json` ist das Gegenstück für die handschriftliche
  Überlieferung, ebenfalls eine Zeile der Quelle je Datensatz. Neben den
  RISM-Angaben trägt jedes Zeugnis, sofern in der Quelle vorhanden,
  `dating`, `link`, `shelfmarkAlt`, `provenance`, `sourceNote` und
  `literature`, siehe Abschnitt 16 in `docs/entscheidungen.md`. `sourceType`
  nennt die Quellenart, bei Stimmbüchern mit Anzahl und vorhandenen Stimmen,
  etwa „Stimmbücher (6): C, A, T, B, Quintus, Sextus“ (Abschnitt 33).
- `works.json` fasst Einträge und Handschriften-Zeugnisse über die LV-Nummer
  (oder die Anhangsnummer) zu Werken zusammen. `entries` und `manuscripts`
  verweisen dort getrennt auf die jeweiligen Zeugnisse, `expressions` auf die
  Fassungen des Werks. Teilsätze wie `100-2` verweisen mit `isPartOf` auf ihr
  Gesamtwerk, das sie in `hasPart` auflistet. Jedes Werk trägt einen
  `preferredTitle`, den normalisierten Werktitel nach MGG oder, wo keiner
  vorliegt, den Titel des frühesten Drucks (`preferredTitleBasis` sagt,
  welcher), und die Titel der Drucke und Handschriften als `variantTitles`.
  Siehe Abschnitte 18 und 21 in `docs/entscheidungen.md`.
- `expressions.json` enthält die Fassungen, die die Quelle mit einer römischen
  Ziffer kennzeichnet, etwa `193 (II)`, als Expression im Sinne von FRBR. Jede
  verweist über `realizationOf` auf ihr Werk und trägt die Ziffer als `pars`,
  den Teil des Werks, den sie in abweichender Gestalt bringt. Siehe Abschnitt
  17 in `docs/entscheidungen.md`.
- `prints.json` listet die Erstdrucke als eigene Entität.
- `persons.json` listet die Textdichter als Personen. Schreibvarianten mit
  kuratierter GND-Zuordnung sind zu einer Person mit festgelegter
  `preferredName` und `variantNames` zusammengeführt; die Einträge behalten
  den Rohwert in `textAuthor` und verweisen über `textAuthorPerson` auf die
  Person. Siehe Abschnitt 19 in `docs/entscheidungen.md`.

Alle Dateien tragen einen Verweis auf `schema/context.jsonld` und sind damit als
JSON-LD lesbar. Sie lassen sich mit Standardwerkzeugen nach RDF überführen, ohne
dass im Alltag ein Triple Store betrieben werden muss.

## Validierung

Das Importskript prüft jeden erzeugten Eintrag gegen
`schema/entry.schema.json` und jedes Handschriften-Zeugnis gegen
`schema/manuscript.schema.json`, bevor es irgendetwas schreibt. Ein
Mapping-Fehler bricht den Import damit sofort mit einer Fehlermeldung ab,
statt still eine ungültige Datei zu erzeugen. `works.json`, `prints.json` und
`persons.json` sind dagegen nicht schemabewehrt; sie sind rein abgeleitet und
werden bei jedem Import ohnehin vollständig neu berechnet.

## Import ausführen

Voraussetzung ist Python mit openpyxl und jsonschema.

```bash
pip install -r scripts/requirements.txt
python scripts/import_excel.py
```

Das Skript ist wiederholbar. Ein erneuter Lauf über unveränderte Quellen erzeugt
identische Ausgaben und vergibt keine neuen IDs.

## Quelldateien

Der Import liest genau diese Dateien aus `raw/`; alle werden von Hand gepflegt:

| Datei | Blatt | Inhalt |
| --- | --- | --- |
| `Werke.xlsx` | LV-Katalog | eine Zeile je Werk in seinem Erstdruck |
| `Drucke.xlsx` | Drucknachweise | eine Zeile je Werk und Druck, auch Nachdrucke |
| `Drucke.xlsx` | Drucke | eine Zeile je Druck mit den Angaben aus dem Druckeverzeichnis |
| `lasso_handschriften.xlsx` | Werke | eine Zeile je Werk in einer Handschrift |
| `personen_normdaten.json` | – | GND/VIAF-Zuordnung der Textdichter |

Die Spalten *Beschreibung*, *Titel*, *Stimmbücher*, *Verweis …* (eine je
Verzeichnis) und *RISM* (Link auf RISM Online) im Blatt *Drucke* stammen aus
dem Druckeverzeichnis. Sie werden mit `python scripts/tex_drucke.py` gefüllt;
das Skript schreibt nur in leere Zellen, Korrekturen von Hand bleiben also
erhalten. Die TeX-Dateien liegen lokal in `texDateien/` und werden nicht
veröffentlicht (`.gitignore`). Siehe Abschnitt 26.

## Eine weitere Excel-Tabelle aufnehmen

Tabellen mit abweichenden Spalten sind vorgesehen, solange sie fachlich
dasselbe sind wie die bestehenden Drucke, also ein Werk in einer Quelle mit
LV-Nummer, Titel, Stimmen und Erstdruck. Nötig sind zwei Schritte:

1. Die Datei nach `raw/` legen.
2. In `scripts/import_excel.py` einen Eintrag zu `SOURCES` ergänzen, mit eigener
   `id`, Dateiname, Blattname und einem `columns`-Mapping von Spaltenkopf auf
   kanonisches Feld.

Spalten, die im Mapping fehlen, gehen nicht verloren. Sie landen im Feld `extra`
des jeweiligen Datensatzes und können später in das Kernmodell hochgezogen
werden. Ein Schemawechsel oder eine Migration ist dafür nicht nötig.

Trägt die Tabelle dagegen fachlich andere Informationen, wie die
Handschriften-Überlieferung mit RISM-Sigel, Bibliothek und Signatur statt
Drucksigle, passt sie nicht in das `CatalogueEntry`-Modell der Drucke. Dafür
gibt es ein zweites, eigenständiges Muster: `MANUSCRIPT_SOURCES` mit
eigenem `columns`-Mapping, eine eigene Lesefunktion (`read_manuscripts`), ein
eigenes Schema (`manuscript.schema.json`) und eine eigene Ausgabedatei
(`manuscripts.json`). `derive_works` verknüpft beide Quellen anschließend über
die LV-Nummer zum gemeinsamen `Work`. Eine dritte, wiederum andersartige
Quelle bekäme auf demselben Weg ihr eigenes Tripel aus Mapping, Schema und
Ausgabedatei, statt eines der bestehenden Modelle zu verbiegen.

## Offene redaktionelle Punkte

- Textdichter ohne GND-Zuordnung stehen weiter als Rohwerte nebeneinander.
  Eine automatische Zusammenführung wäre eine inhaltliche Entscheidung und
  unterbleibt bewusst; zusammengeführt wird nur über
  `raw/personen_normdaten.json`, siehe Abschnitte 15 und 19 in
  `docs/entscheidungen.md`.
- Einzelne Titel enthalten ein Kreuzzeichen aus der TeX-Vorlage, etwa
  `Moresca quarta D'orlando.†`. Die Bedeutung ist zu klären, bevor es entfernt
  wird.
- Ein Titel enthält eine auffällige Leerstelle, `Rendz moy mo cœ ur à cinq`.
  Vermutlich ein Artefakt der Vorlage.
- Das Feld `rism` in `prints.json` wird aus den bestätigten Zuordnungen im
  Blatt *Drucke* von `raw/Drucke.xlsx` gefüllt. Bisher ist keine bestätigt.
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
- `rismSiglum` in `manuscripts.json` wird unverändert übernommen, ohne
  Prüfung gegen eine RISM-Normdatei. Tippfehler oder veraltete Sigel fallen
  dadurch nicht automatisch auf.
- Die 161 Werke aus dem LV-Anhang (`lvAnh`, `@id` beginnend mit `work:anh-`)
  entstehen rein aus einem Textmuster („LVanh N“) im Freitextfeld „Weitere
  Teile“ der Handschriften-Tabelle, ohne fachliche Prüfung gegen die
  gedruckte LV-Anhang-Literatur. Eine Verifikation steht aus.
- 311 Handschriften-Zeugnisse ließen sich weder einer LV- noch einer
  Anhangsnummer zuordnen und warten auf manuelle Zuordnung in
  `raw/lasso_handschriften.xlsx`.

## Lizenz

Die Daten in `raw/` und `data/` stehen unter CC BY 4.0, siehe `LICENSE`. Das
Importskript in `scripts/` steht unter der MIT-Lizenz. Bei Nachnutzung der Daten
bitte das Repository und die zugrunde liegende Katalogquelle nennen.
