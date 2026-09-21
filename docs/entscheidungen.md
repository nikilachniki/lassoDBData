# Technologieentscheidungen

Begründungsprotokoll zum Projekt einer Werkdatenbank für Orlando di Lasso.
Festgehalten am 20. September 2026. Das Dokument beschreibt den Stand nach der
Einrichtung des Datenrepositories und deckt beide Repositories ab,
[lassoDBData](https://github.com/nikilachniki/lassoDBData) für den Datenbestand
und [lassoDB](https://github.com/nikilachniki/lassoDB) für die Anwendung.

Jeder Abschnitt nennt die Entscheidung, die verworfenen Alternativen, die
tragende Begründung und den dafür in Kauf genommenen Preis.

---

## 1. Zwei Repositories statt eines

**Entscheidung.** Daten und Anwendung liegen getrennt.

**Alternative.** Ein gemeinsames Repository mit Unterordnern.

**Begründung.** Der Datenbestand ist ein eigenständiges wissenschaftliches
Ergebnis und soll unabhängig von der Anwendung versioniert, getaggt und später
über Zenodo mit einer DOI zitierbar gemacht werden können. Ein Fehler im
Stylesheet darf die Datenversion nicht verschieben. Hinzu kommen die
unterschiedlichen Lizenzen, CC BY 4.0 für die Daten und MIT für den Code, die
sich in getrennten Repositories eindeutig ausdrücken lassen. Fachliche
Korrekturen erreichen das Projekt als Pull Request, ohne dass Beitragende den
Anwendungscode ansehen müssen. Schließlich überlebt der Datenbestand die
Oberfläche: Frontends werden neu geschrieben, das Verzeichnis bleibt.

**Preis.** Der Build der Anwendung muss die Daten aus dem anderen Repository
beziehen, was einen zusätzlichen Checkout und einen Auslöser für den Rebuild
erfordert. Änderungen, die Schema und Oberfläche gleichzeitig betreffen, lassen
sich nicht in einem Commit abbilden. In der frühen Phase wird deshalb
ungepinnt gegen den Hauptzweig gebaut, erst bei stabilem Schema gegen ein Tag.

---

## 2. Keine relationale Datenbank

**Entscheidung.** Der Datenbestand liegt als versionierte JSON-LD-Dateien in Git,
nicht in PostgreSQL oder einem vergleichbaren System.

**Alternativen.** PostgreSQL, ursprünglich empfohlen. Ein RDF-Triplestore. Die
Excel-Dateien unmittelbar als führendes System.

**Begründung.** Ausschlaggebend war nicht die vermeintliche Starrheit
relationaler Schemata, denn die ist in der Praxis gering: Spalten lassen sich
ergänzen, und semistrukturierte Anteile können in JSONB-Feldern liegen.
Entscheidend war die Hostingbedingung. Eine rein statische Auslieferung ohne
Server schließt eine live angebundene Datenbank aus. Dazu kommt, dass Git für
einen wachsenden geisteswissenschaftlichen Datenbestand Eigenschaften mitbringt,
die eine Datenbank nicht ohne Zusatzaufwand bietet, nämlich lückenlose
Änderungshistorie, lesbare Differenzen und ein Begutachtungsverfahren über
Pull Requests.

Gegen einen vollwertigen Triplestore sprach der Aufwand. SPARQL, Serverbetrieb
und eine eigene Werkzeugkette sind für eine Einzelperson eine erhebliche Hürde
und stehen in keinem Verhältnis zum Umfang von rund zweitausend Datensätzen.
Gegen Excel als führendes System sprach, dass Tabellendateien sich nicht sinnvoll
versionieren und vergleichen lassen und von einer Weboberfläche nicht direkt
gelesen werden können.

**Warum JSON-LD.** Es vereint drei Eigenschaften. Es ist für das JavaScript-
Frontend das native Format. Über den Kontext in `schema/context.jsonld` bildet es
die Felder auf etablierte Vokabulare ab, hier Dublin Core Terms und schema.org,
und ist damit jederzeit verlustfrei nach RDF überführbar. Und es erlaubt
Erweiterungen je Datensatz, ohne dass eine Migration nötig wird.

**Preis.** Keine Abfragesprache, keine referenzielle Integrität auf
Datenbankebene, keine gleichzeitige Mehrbenutzerbearbeitung. Validierung muss
über JSON Schema und das Importskript erfolgen statt über Datenbankconstraints.

---

## 3. Git als Versionierungs- und Nachweisschicht

**Entscheidung.** Die Versionsverwaltung übernimmt zugleich die Funktion eines
editorischen Apparats.

**Begründung.** Nachvollziehbarkeit der Provenienz ist eine fachliche Anforderung,
keine technische Bequemlichkeit. Wer wann welche Angabe geändert hat, ist in der
Commit-Historie dokumentiert und ohne Zusatzsystem prüfbar. Für eine
wissenschaftliche Edition ist das ein inhaltliches Argument und nicht bloß ein
Nebeneffekt der Werkzeugwahl.

**Preis.** Die Historie ist nur so aussagekräftig wie die Commit-Disziplin.
Große maschinell erzeugte Differenzen können die Lesbarkeit beeinträchtigen,
weshalb die Ausgabedateien stabil sortiert und eingerückt geschrieben werden.

---

## 4. Quelldateien bleiben unverändert erhalten

**Entscheidung.** Die Original-Excel-Dateien liegen unangetastet in `raw/`. Zu
jeder Quelle wird in `data/meta.json` eine SHA-256-Prüfsumme festgehalten.

**Begründung.** Die Umwandlung soll jederzeit reproduzierbar und überprüfbar
sein. Alle Normalisierungen geschehen ausschließlich im Importskript und
sind dort nachlesbar. Rohwerte bleiben zusätzlich erhalten, etwa in den Feldern
`titleRaw` und `voicesRaw`.

---

## 5. Wiederholbarer Import statt einmaliger Migration

**Entscheidung.** `scripts/import_excel.py` ist ein beliebig oft ausführbarer
Transformationsschritt. Quellen werden in einer Liste registriert, jede mit
eigenem Mapping von Spaltenkopf auf kanonisches Feld.

Spalten ohne Mapping werden nicht verworfen, sondern im
Feld `extra` mitgeführt und können später in das Kernmodell übernommen werden.
Die Aufnahme einer weiteren Quelle kostet damit einen Listeneintrag und keine
Umstellung.

**Preis.** Die Ausgabedateien sind erzeugte Artefakte und dürfen nicht von Hand
bearbeitet werden. Diese Regel muss eingehalten werden, sonst gehen Änderungen
beim nächsten Lauf verloren.

---

## 6. Ein Datensatz ist ein Werk in einem Druck

**Entscheidung.** `entries.json` bildet die Quelle zeilengetreu ab. Die
Zusammenfassung zu Werken in `works.json` ist davon abgeleitet.

**Befund.** Die Analyse der vorhandenen Tabelle ergab, dass die LV-Nummer kein
eindeutiger Schlüssel ist. Von 1945 LV-Nummern kommen 32 mehrfach vor, einzelne
bis zu dreimal, weil dieselbe Komposition in mehreren Drucken erscheint. LV 90
etwa steht fünfstimmig im Druck 1560-4 und zweistimmig im Druck 1560-8, mit
abweichender Schreibung des Textdichters.

**Begründung.** Die Zeile beschreibt genau genommen das Vorkommen eines Werks in
einem Druck. Diese Unterscheidung entspricht fachlich der Trennung zwischen Werk
und Manifestation, wie sie FRBR und darauf aufbauend FRBRoo formulieren. Das
vollständige Modell wurde nicht übernommen, wohl aber die Unterscheidung. Die
verlustfreie Ebene bleibt die zitierfähige Grundlage, die abgeleiteten Ebenen
sind Bequemlichkeiten für die Oberfläche und jederzeit neu berechenbar.

**Preis.** Zwei Ebenen müssen gepflegt und erklärt werden. Wer naiv über
LV-Nummern zählt, erhält falsche Ergebnisse.

---

## 7. Interne fortlaufende Kennung mit dauerhafter Registry

**Entscheidung.** Jeder Datensatz erhält eine fortlaufende Ganzzahl. Die
Zuordnung wird in `data/id-registry.json` festgehalten. Einmal vergebene Nummern
werden nie erneut vergeben, auch nicht, wenn ein Datensatz entfällt.

**Alternativen.** Ein zusammengesetzter Schlüssel aus LV-Nummer und Drucksigle.
Ein schlichtes Neudurchzählen bei jedem Import.

**Begründung.** Da die LV-Nummer nicht eindeutig ist, wird eine eigene Kennung
gebraucht. Ein zusammengesetzter Schlüssel wäre unhandlich zu zitieren und würde
sich ändern, sobald eine Druckzuweisung korrigiert wird. Ein bloßes
Neudurchzählen wäre einfacher, hätte aber zur Folge, dass beim Hinzukommen der
zweiten Tabelle sämtliche Nummern verrutschen und veröffentlichte Verweise
ungültig werden. Die Registry löst das, ohne die Einfachheit der laufenden
Nummer aufzugeben.

**Wiedererkennungsschlüssel.** Eine Zeile wird über Herkunftsdatensatz,
LV-Nummer und Erstdruck wiedererkannt, ausdrücklich nicht über den Titel. Eine
spätere Korrektur einer Schreibweise soll keinen neuen Datensatz erzeugen.

**Preis.** Eine zusätzliche Datei, die mitversioniert und niemals von Hand
verändert werden darf. Geht sie verloren, ist die Nummernvergabe nicht
rekonstruierbar.

---

## 8. Keine automatische Normalisierung von Personennamen

**Entscheidung.** Schreibvarianten bleiben nebeneinander bestehen, etwa `Marot`
und `C.Marot`. Die Felder `gnd` und `viaf` sind vorbereitet und leer.

**Begründung.** Ob zwei Namensformen dieselbe Person bezeichnen, ist eine
fachliche Feststellung und keine Zeichenkettenoperation. Eine automatische
Zusammenführung würde eine Setzung verbergen, die begründet und belegt gehören.
Die Verknüpfung mit Normdaten, also GND und VIAF, ist als eigener redaktioneller
Arbeitsschritt vorgesehen.

**Preis.** Die Zahl der Textdichter ist derzeit zu hoch und nicht ohne Vorbehalt
auswertbar.

---

## 9. Oberfläche mit React, MUI und Vite

**Entscheidung.** Eine rein clientseitige Anwendung mit Vite als Build-Werkzeug,
React als Bibliothek und MUI als Komponentenbibliothek.

**Alternativen.** Next.js, ursprünglich empfohlen. Ein statischer
Seitengenerator. Eine handgeschriebene Oberfläche ohne Komponentenbibliothek.

**Begründung.** Next.js entfällt, weil dessen tragende Eigenschaften,
serverseitiges Rendern und API-Routen, auf einer rein statischen Auslieferung
nicht verfügbar sind. React und MUI sind gesetzt, weil die vorhandene Erfahrung
dort liegt und die Datenraster-Komponente von MUI genau den Bedarf einer
sortier- und filterbaren Katalogansicht abdeckt. Die gelegentliche Sorge, das sei
überdimensioniert, hält der Prüfung nicht stand: Eine gleichwertige Tabelle mit
Sortierung, Filterung und Virtualisierung selbst zu schreiben wäre mehr Aufwand,
nicht weniger.

**Suche im Browser.** Der vollständige Bestand ist komprimiert rund 94 Kilobyte
groß. Er lässt sich vollständig laden und im Browser durchsuchen. Ein
Suchdienst wie Elasticsearch oder eine serverseitige Volltextsuche wäre bei
dieser Größenordnung nicht zu rechtfertigen.

**Preis.** Keine serverseitig gerenderten Seiten, was die Auffindbarkeit durch
Suchmaschinen einschränkt. Die Startzeit enthält das Laden des gesamten
Datenbestands.

---

## 10. Auslieferung über GitHub Pages

**Entscheidung.** Die Anwendung wird als statische Seite über GitHub Pages
ausgeliefert, gebaut über GitHub Actions.

**Begründung.** Kein Server, keine laufenden Kosten, kein Betriebsaufwand. Für
ein Projekt ohne institutionelle Infrastruktur ist das ein
Nachhaltigkeitsargument und keine Sparmaßnahme. Eine statische Seite nebst
Git-Repository hat eine erheblich längere realistische Lebensdauer als eine
Anwendung, die auf einen gepflegten und bezahlten Server angewiesen ist. Diese
Bedingung ist zugleich die Ursache für die Entscheidungen 2 und 9.

**Preis.** Keine serverseitige Logik, keine geschützten Bereiche, keine
Bearbeitung über die Oberfläche. Redaktionelle Arbeit läuft über Git.

---

## 11. Datenanbindung zur Bauzeit statt zur Laufzeit

**Entscheidung.** Die Anwendung lädt die Daten nicht zur Laufzeit von einem
fremden Dienst, sondern bindet sie zur Bauzeit ein. Ein Skript,
`scripts/sync-data.mjs` in lassoDB, kopiert die JSON-LD-Dateien aus
lassoDBData vor jedem Entwicklungs- und Build-Lauf nach `src/data/`, von wo
Vite sie ins Bundle übernimmt. Der GitHub-Actions-Workflow in lassoDB checkt
dafür lassoDBData zusätzlich aus und übergibt den Pfad als Umgebungsvariable.

**Alternative.** Laufzeitabruf über einen Auslieferungsdienst für
GitHub-Inhalte wie jsDelivr, damit Datenänderungen ohne Neubau der Anwendung
sichtbar werden.

**Begründung.** Der Bauzeitweg ist reproduzierbar, jeder veröffentlichte
Stand der Anwendung ist einem genau bestimmbaren Datenstand zugeordnet und
unabhängig von der Verfügbarkeit eines dritten Dienstes. Das war in
Abschnitt 1 als offener Punkt benannt und ist damit entschieden. Diese damit
verbundene Entscheidung war zugleich, keine eigene Kopie der Daten im
Anwendungsrepository zu versionieren, `src/data/` ist entsprechend von der
Versionsverwaltung ausgeschlossen. Eine zweite Kopie neben der eigentlichen
Quelle hätte sonst auseinanderlaufen können.

**Preis.** Eine Datenänderung wird erst nach einem Neubau der Anwendung
sichtbar, nicht sofort. Ein lokaler Checkout ohne das Geschwisterrepository
lassoDBData kann die Anwendung nicht bauen, das Sync-Skript bricht dann mit
einer Fehlermeldung ab, statt still mit veralteten oder leeren Daten
fortzufahren.

---

## 12. Suche über die native Filterfunktion der Datengrid-Komponente

**Entscheidung.** Die Volltextsuche läuft über die in MUI X DataGrid
eingebaute Schnellfilterfunktion, keine zusätzliche Suchbibliothek.

**Alternative.** Fuse.js für eine unscharfe, tippfehlertolerante Suche, wie
zuvor besprochen.

**Begründung.** Die DataGrid-Komponente war ohnehin gesetzt, ihre eingebaute
Filterung deckt eine einfache Stichwortsuche über alle sichtbaren Spalten ab,
ohne eine weitere Abhängigkeit einzuführen. Fuse.js bleibt eine Option, sobald
tatsächlich unscharfe Suche gebraucht wird, etwa über abweichende
Schreibweisen von Textdichternamen, siehe Abschnitt 8.

**Ehrlicher Nebenpunkt.** Das ausgelieferte JavaScript-Bündel ist nach
Kompression rund 360 Kilobyte groß, spürbar mehr als die 94 Kilobyte des
Datenbestands allein. Der überwiegende Teil davon ist MUI und die
DataGrid-Komponente selbst, nicht die Daten. Für die angestrebte
Projektgröße ist das weiterhin vertretbar, wird aber nicht kleiner, wenn der
Bestand wächst, sondern bleibt konstant, weil er von der Bibliothek und nicht
von den Daten dominiert wird.

---

## 13. Info-Dialog statt Popover für den Projekttext

**Entscheidung.** Der Info-Button in der Kopfzeile öffnet einen modalen Dialog
(MUI `Dialog`) mit drei Abschnitten statt eines kleinen, an den Button
verankerten Popovers: eine Einordnung der Datenbank samt Quellenangabe zum
LV-Katalog, eine Beschreibung des Digital Lab der Gesellschaft für Bayerische
Musikgeschichte e. V. mit Verweis auf dessen Projektseite, sowie Angaben zu
Lizenz und Repositories. Der Dialog liegt als eigene Komponente
`src/InfoDialog.tsx` vor, nicht inline in `App.tsx`, um die ohnehin schon
umfangreiche Wurzelkomponente nicht weiter wachsen zu lassen. Der Abschnitt
zum Digital Lab nennt zusätzlich dessen Leitung (Dr. Moritz Kelber), dass es
allen Interessierten zur Mitarbeit offensteht, sowie die Teamgröße seit
Anfang 2026 (vier Wissenschaftler*innen); Personenbezeichnungen sind
durchgängig mit Sternchen gegendert. Der erste Abschnitt beschreibt die
gedruckte Überlieferung des LV-Katalogs und die handschriftliche
Überlieferung der Lasso-Handschriften-Datenbank
([lasso-handschriften.badw.de](https://lasso-handschriften.badw.de/)) als
bereits zusammengeführt, ohne genaue Zähldaten zu nennen. Die beiden
Quellenangaben stehen dafür nicht mehr im Fließtext, sondern als
nummerierte Fußnoten, auf die hochgestellte Ziffern im Text verweisen.

**Alternative.** Das bisherige kleine Popover mit einem einzelnen Absatz. Bei
den Quellenangaben: ein unmarkierter Zitationsblock ohne Fußnotenziffern im
Fließtext, verworfen, weil bei zwei Quellen zu unterschiedlichen
Teilaussagen (Drucke, Handschriften) sonst unklar bliebe, welche Aussage
sich auf welche Quelle stützt.

**Begründung.** Der ursprüngliche Text nannte nur den Trägerverein und einen
Link auf lassoDBData, ohne Einordnung von Lasso, Quelle der LV-Zählung oder
Bezug zum Digital Lab. Ein einzeiliges Popover bietet dafür zu wenig Platz und
wirkt bei mehreren Absätzen beengt. Inhaltlich orientiert sich der erste
Abschnitt am Beschreibungstext der Lasso-Handschriften-Datenbank der
Bayerischen Akademie der Wissenschaften, angepasst auf die gedruckte
Überlieferung und den LV-Katalog von Leuchtmann/Schmid, die dieser
Werkdatenbank tatsächlich zugrunde liegt. Der zweite Abschnitt paraphrasiert
die Projektbeschreibung des Digital Lab unter
[gfbm-online.de/laufende-editionsprojekte/digitallab](https://gfbm-online.de/laufende-editionsprojekte/digitallab/),
das Lasso und Hassler explizit als eines seiner Einzelprojekte nennt.

**Preis.** Der Dialog verdeckt beim Öffnen die gesamte Ansicht statt nur einen
kleinen Bereich daneben, und ein Abschnitt hängt inhaltlich von einer
externen, nicht versionierten Webseite ab und kann bei deren Überarbeitung
veralten. Der Text zur Datenbank beschreibt die Zusammenführung von Drucken
und Handschriften bewusst als Zielzustand des Projekts, obwohl `entries.json`
laut Abschnitt „Datenmodell“ im README bislang ausschließlich Einträge aus
der gedruckten Überlieferung enthält (Quelle `Werke.xlsx`, siehe `meta.json`);
die zweite Tabelle mit den Handschriften ist als offener Punkt dort weiterhin
vermerkt. Diese Vereinfachung ist eine bewusste redaktionelle Entscheidung
des Projektinhabers, keine Aussage über den tatsächlichen Datenbestand.

---

## Bewusst nicht übernommene Standards

- **MEI**, die Music Encoding Initiative, ist für die Codierung von Notentext
  gedacht, nicht für Katalogmetadaten. Sie wird erst einschlägig, wenn Notentexte
  selbst erfasst werden sollen.
- **CIDOC-CRM und FRBRoo** zielen auf sammlungsübergreifende Interoperabilität
  von Institutionen. Der Modellierungsaufwand steht für ein Projekt dieser Größe
  in keinem Verhältnis. Die zugrunde liegende Unterscheidung von Werk und
  Manifestation wurde gleichwohl übernommen, siehe Abschnitt 6.
- **Triplestore und SPARQL** wurden aufgeschoben. Der JSON-LD-Kontext hält den
  Weg dorthin offen, ohne ihn jetzt gehen zu müssen.
- **RISM, GND und VIAF** sind als Felder vorgesehen und noch unbefüllt. Die
  Verknüpfung ist ein eigener Arbeitsschritt und setzt redaktionelle
  Entscheidungen voraus.

---

## Offene Punkte

- Die zweite Tabelle liegt noch nicht vor. Ihr Spaltenmapping steht aus.
- In den Repository-Einstellungen von lassoDB muss einmalig manuell GitHub
  Actions als Quelle für GitHub Pages eingestellt werden, das lässt sich nicht
  aus der Anwendung heraus auslösen.
- Die Versionspinnung zwischen Anwendung und Daten soll erst nach Stabilisierung
  des Schemas eingeführt werden.
- Eine Veröffentlichung des Datensatzes über Zenodo mit DOI ist vorgesehen, aber
  noch nicht eingerichtet.
- Einzelne Titel enthalten Zeichen aus der TeX-Vorlage, deren Bedeutung zu klären
  ist, etwa ein nachgestelltes Kreuz und eine auffällige Leerstelle.

---

## Kennzahlen zum Zeitpunkt der Festschreibung

| Größe | Wert |
| --- | --- |
| Datensätze | 1979 |
| Werke nach LV-Nummer | 1945 |
| davon in mehreren Drucken | 32 |
| Drucke | 137 |
| Textdichter als Rohwerte | 85 |
| Datensätze ohne Stimmenangabe | 75 |
| Datenbestand komprimiert | 94 KB |
