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

**Entscheidung.** Die Original-Excel-Dateien liegen unangetastet in `raw/`.
Welcher Stand der Quellen zu welchen Daten gehört, belegt Git: Quellen und
erzeugte Daten werden im selben Commit versioniert (bis Abschnitt 32 stand
dafür zusätzlich eine Prüfsumme je Quelle in `data/meta.json`).

**Begründung.** Die Umwandlung soll jederzeit reproduzierbar und überprüfbar
sein. Alle Normalisierungen geschehen ausschließlich im Importskript und
sind dort nachlesbar. Rohwerte bleiben zusätzlich erhalten, wo die
Normalisierung Information verwirft, etwa im Feld `voicesRaw`. Ein eigenes
Feld für den unveränderten Titel entfiel später, siehe Abschnitt 28.

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
Zuordnung wird in `scripts/id-registry.json` festgehalten (bis Abschnitt 32
unter `data/`). Einmal vergebene Nummern
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
und `C.Marot`. Die Felder `gnd` und `viaf` waren zum Zeitpunkt dieser
Entscheidung vorbereitet und leer; die Verknüpfung selbst ist inzwischen
nachgezogen, siehe Abschnitt 15.

**Begründung.** Ob zwei Namensformen dieselbe Person bezeichnen, ist eine
fachliche Feststellung und keine Zeichenkettenoperation. Eine automatische
Zusammenführung würde eine Setzung verbergen, die begründet und belegt gehören.
Die Verknüpfung mit Normdaten, also GND und VIAF, ist als eigener redaktioneller
Arbeitsschritt vorgesehen, siehe Abschnitt 15 für dessen Umsetzung.

**Preis.** Die Zahl der Textdichter ist derzeit zu hoch und nicht ohne Vorbehalt
auswertbar.

**Nachtrag.** Für Personen mit kuratierter GND-Zuordnung sind die
Schreibvarianten inzwischen zu einer Person mit festgelegter Anzeigeform
zusammengeführt, siehe Abschnitt 19. Die Entscheidung gegen eine
*automatische* Normalisierung gilt weiter: Zusammengeführt wird nur, was
`raw/personen_normdaten.json` ausdrücklich zuordnet.

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
der gedruckten Überlieferung enthält (Quelle `Werke.xlsx`);
die zweite Tabelle mit den Handschriften ist als offener Punkt dort weiterhin
vermerkt. Diese Vereinfachung ist eine bewusste redaktionelle Entscheidung
des Projektinhabers, keine Aussage über den tatsächlichen Datenbestand.

---

## 14. Handschriften als eigene Entität statt erweiterter Katalogeintrag

**Entscheidung.** Die neu hinzugekommene Tabelle der Lasso-Handschriften
(ursprünglich `raw/werke_aus_handschriften.xlsx`, seit Abschnitt 16 durch
`raw/lasso_handschriften.xlsx` ersetzt, 8961 Zeilen, 1417 Quellen aus 131
Bibliotheken) wird nicht in `entry.schema.json` eingepasst, sondern als
eigenständige Entität `ManuscriptWitness` mit eigenem Schema
(`schema/manuscript.schema.json`) und eigener Ausgabedatei
(`data/manuscripts.json`) geführt. `Work` bekommt dafür ein Feld
`manuscripts`, parallel zu `entries`.

**Alternative.** `entry.schema.json` um die Felder RISM-Sigel, Bibliothek,
Signatur und Quellenart erweitern, wie ursprünglich erwogen.

**Begründung.** `entry.schema.json` beschreibt laut eigener Definition „ein
Werk in einem Druck“, siehe Abschnitt 6. Eine Handschrift ist keine
Abwandlung eines Drucks, sondern eine andere Art von Quelle mit anderen
Feldern; die meisten Druckfelder (Erstdruck-Jahr und -Nummer) wären für
Handschriften leer, und umgekehrt die meisten Handschriftenfelder für Drucke.
Das Projekt kennt dieses Muster bereits: `works.json`, `prints.json` und
`persons.json` sind schon eigenständige, über IDs verknüpfte Kollektionen.
Eine vierte fügt sich sauber ein.

**Drei Fälle beim Verknüpfen mit `works.json`.** Die Analyse der Tabelle ergab
drei Gruppen von Zeilen:

1. Die meisten (7938 von 8193 Zeilen mit LV-Angabe) verweisen auf ein Werk,
   das bereits aus dem Druckkatalog besteht.
2. 65 weitere LV-Zeichenketten (341 Zeilen), teils ganz neue Grundnummern wie
   105 und 106, teils zusätzliche Teilsätze bestehender Werke wie 26-2,
   kommen im Druckkatalog nicht vor. Für sie legt der Import jetzt neue
   Werke an, die ausschließlich handschriftlich bezeugt sind.
3. 768 Zeilen tragen gar keine LV-Nummer. Davon verweisen 444 im Freitextfeld
   „Weitere Teile“ auf eine Nummer aus dem LV-Anhang (Boetticher), erkennbar
   am Muster „LVanh N“. Für diese 161 Anhangsnummern legt der Import
   ebenfalls eigene Werke an (`@id` beginnend mit `work:anh-`, `lv: null`,
   stattdessen `lvAnh` gesetzt).

**Die verbleibenden 311 Zeilen bleiben bewusst unverknüpft, nicht als Werk.**
Ohne LV- oder Anhangsnummer fehlt der fachliche Schlüssel. Eine Gruppierung
über den Titel wurde verworfen: kurze, generische Titel wie „Laudate pueri“
oder „Kyrie“ könnten zufällig gleich lauten, ohne dasselbe Stück zu sein, und
eine automatische Zusammenführung würde das stillschweigend unterstellen.
Manche dieser Zeilen sind zudem explizit mit „LV ?“ markiert, die Forschung
selbst ist sich über die Zuschreibung an Lasso also nicht sicher. Ein
Werk-Eintrag würde das fälschlich als gesichert ausweisen, siehe die
Unterscheidung von Werk und Bezeugung in Abschnitt 6. Die Zeilen selbst gehen
trotzdem nicht verloren: Sie stehen weiterhin in `manuscripts.json` (mit
`lv: null` und `lvAnh: null`). Die zusätzliche, bei jedem Import erzeugte
Liste `docs/handschriften-ohne-zuordnung.md` entfiel später (Abschnitt 36).

**Was unverändert als Rohtext bleibt.** Die Spalte „Quellenart“ enthält
teils MARC-artige Teilfelder (etwa `$aStimmbücher$b1$c[5]`) und wird ohne
Zerlegung als `sourceDescription` übernommen (seit Abschnitt 33 lesbar
aufbereitet als `sourceType`). Das RISM-Sigel wird ohne
Prüfung gegen eine Normdatei übernommen. Beides folgt demselben Muster wie
die unnormalisierten Textdichter-Rohwerte in Abschnitt 8: die inhaltliche
Aufbereitung ist ein eigener redaktioneller Arbeitsschritt, keine
Automatisierung im Importskript.

**Registry.** Handschriften-Zeugnisse erhalten ihre interne ID aus derselben
`id-registry.json` wie Katalogeinträge, über einen eigenen fachlichen
Schlüssel aus Werk (LV oder LVanh, ggf. mit Teilsatz) und Quelle
(RISM-Sigel plus Signatur), damit eine Quelle mit mehreren Lasso-Stücken pro
Zeile eine eigene, stabile ID bekommt.

**Darstellung im Frontend.** Auf der Werk-Detailseite erscheinen die
Handschriften-Zeugnisse nicht als dichte Tabelle wie die Druckfassungen,
sondern als je ein ausklappbares Panel (Accordion) im gleichen Fact-Stil wie
der Werkeintrag selbst, geschlossen mit Ort, Bibliothek und Signatur als
Kurzbeschreibung. Handschriften tragen mehr uneinheitliche und teils lange
Freitextfelder (Quellenart, Bemerkung) als Druckeinträge, bei zugleich
typischerweise wenigen Zeugnissen pro Werk; eine Tabelle mit entsprechend
vielen oder breiten Spalten wäre entweder abgeschnitten oder unübersichtlich
breit.

**Preis.** Zwei weitere Ebenen im Datenmodell, die erklärt werden müssen: die
Unterscheidung Druck- und Handschriftenbezeugung, und innerhalb der
Handschriften die Unterscheidung Haupt-LV-Katalog und LV-Anhang. Die
Zuordnung der 161 Anhangswerke beruht bislang allein auf dem Textmuster
„LVanh N“ im Quelldokument, nicht auf einer eigenen fachlichen Prüfung gegen
die zugrunde liegende Literatur.

---

## 15. Manuell kuratierte GND/VIAF-Verknüpfung statt automatischer Auflösung

**Entscheidung.** `raw/personen_normdaten.json` ordnet einzelnen
Textdichter-Rohwerten aus `persons.json` eine GND- und VIAF-ID zu. Die Datei
wird von Hand gepflegt, nicht vom Importskript erzeugt; `derive_persons` liest
sie nur und reichert `data/persons.json` beim Import damit an. Seit Abschnitt
19 ist die Datei nach GND geordnet und nennt je Person eine Anzeigeform und
die zugehörigen Rohwerte.

**Alternative.** Automatischer Abgleich aller 84 Rohwerte gegen die
GND-Suche, etwa nach bestem Treffer.

**Begründung.** Eine Normdatenverknüpfung ist, wie in Abschnitt 8 festgehalten,
eine fachliche Feststellung über eine bestimmte historische Person, keine
Zeichenkettenoperation. Das gilt für eine automatische GND-Zuordnung
genauso wie für das Zusammenführen von Schreibvarianten, mit einem
zusätzlichen Risiko: Die GND enthält für gängige Namen oft mehrere
Personen, und ein automatisch gewählter „bester Treffer" kann die falsche
Person eindeutig und dauerhaft mit dem Werk verknüpfen. Jede der 36
aufgenommenen Zuordnungen wurde deshalb einzeln über die GND-Suche
(lobid.org) geprüft, anhand von Lebensdaten und Beruf gegen das mögliche
Wirkungsfenster Lassos (1532–1594) abgeglichen. Zwei Beispiele für die dabei
aufgetretene Mehrdeutigkeit: Zu „B. Guarini" existieren in der GND zwei
Personen dieses Namens, ein Humanist (1435–1505) und der Dichter und
Librettist (1538–1612); nur letzterer passt zeitlich. Zu „Seneca" existieren
Vater (Rhetor) und Sohn (Philosoph und Dramatiker); ohne weitere Angabe
wurde der Sohn gewählt, da „Seneca" ohne Zusatz in der Rezeption fast immer
ihn meint.

**Darstellung im Frontend.** Der Textdichter-Name bleibt schlichter Text; GND
und VIAF erscheinen, wenn vorhanden, als je ein kleines Badge-Icon direkt
daneben (`GND`/`VIAF`, verlinkt auf `d-nb.info` bzw. `viaf.org`). Nicht der
Name selbst wird verlinkt, damit beide Verknüpfungen unabhängig voneinander
sichtbar sind, statt sich einen von zwei möglichen Zielen zu teilen. Die
Komponente dafür (`AuthorOrSourceText`) ist zwischen Werk-Detailseite und
Katalog-Übersichtstabelle geteilt, sodass die Badges an beiden Stellen
gleich aussehen und ein neu verknüpfter Textdichter nicht nur an einer davon
sichtbar wird.

**Deckungsgrad.** 36 von 84 Rohwerten sind verknüpft (mehrere Rohwerte pro
Person bei Schreibvarianten, etwa `Marot`, `Cl. Marot`, `C.Marot` und
`Clément Marot`), das deckt aber die meisten Nennungen ab: Petrarca allein
66 von rund 260 zugeordneten Einträgen. Zwei Fälle wurden geprüft und
bewusst nicht aufgenommen: „Berno von Cluny" findet in der GND keinen
passenden Treffer unter diesem Namen, nur einen gleichnamigen Abt von
Reichenau (Berno Augiensis, 978–1048) unter abweichender Zuschreibung, was
eine Verwechslung im Ausgangsmaterial nahelegt, aber nicht sicher auflöst.
„Pierre Grognet" findet nur einen Treffer unter der abweichenden Schreibung
„Grosnet", ebenfalls nicht sicher genug für eine Gleichsetzung. Beide Fälle
sind hier festgehalten, damit sie bei einer künftigen Prüfung nicht erneut
von vorn recherchiert werden müssen.

**Warum keine Datei in `data/`.** `personen_normdaten.json` liegt in `raw/`,
nicht in `data/`, weil sie wie `bibel_abkuerzungen.json` eine kuratierte
Referenz ist und keine automatisch erzeugte Ausgabe; Abschnitt 5s Regel, dass
Dateien in `data/` nicht von Hand bearbeitet werden dürfen, gilt für sie
nicht.

**Preis.** Die Zuordnung ist nur so vollständig und aktuell wie die manuelle
Pflege der Datei. Ein neuer, bislang unverknüpfter Textdichter-Rohwert bleibt
ohne GND/VIAF, bis jemand ihn von Hand recherchiert und ergänzt; das
Importskript weist nicht darauf hin, welche Rohwerte noch fehlen.

---

## 16. Handschriften-Quelle um sechs Spalten erweitert

**Entscheidung.** Die Handschriften-Tabelle wurde durch eine umfangreichere
Exportdatei ersetzt, `raw/lasso_handschriften.xlsx` statt
`raw/werke_aus_handschriften.xlsx`, bei unveränderter Zeilenzahl (8961) und
unveränderten Werten in allen bereits gemappten Spalten. Neu hinzugekommen
sind sechs Spalten, alle in `MANUSCRIPT_SOURCES` auf neue Felder in
`ManuscriptWitness` gemappt statt nach `extra` durchgereicht: `Datierung` auf
`dating` (8926 von 8961 Zeilen befüllt), `Link` auf `link` (3663, überwiegend
Verweise auf den RISM-Onlinekatalog, vereinzelt auf andere
Bibliothekskataloge wie den der Bayerischen Staatsbibliothek), `Weitere
Signatur` auf `shelfmarkAlt` (582), `Provenienz` auf `provenance` (3400),
`Bemerkung (Quelle)` auf `sourceNote` (1625) und `Literatur` auf `literature`
(5667).

**Alternative.** Die neuen Spalten unklassifiziert im Feld `extra` belassen,
wie es das Importskript für jede nicht gemappte Spalte ohnehin automatisch
tut, siehe Abschnitt 5.

**Begründung.** Alle sechs Spalten sind fachlich derselben Art wie die
bereits gemappten Handschriften-Felder, nämlich Angaben zur Quelle selbst,
und in mehr als der Hälfte der Fälle befüllt (bei `Datierung` in fast allen
Zeilen). Sie im Feld `extra` zu belassen hätte sie für die Oberfläche
faktisch unsichtbar gemacht, obwohl sie genau dort hingehören, wo bereits
`rismSiglum`, `place`, `library` und `shelfmark` stehen. Ein eigenes Feld je
Spalte macht sie stattdessen sortier- und darstellbar wie die übrigen
Handschriften-Angaben.

**Warum `sourceNote` und nicht `note`.** Die Spalte „Bemerkung (Quelle)“
ist inhaltlich von der bereits vorhandenen Spalte „Weitere Teile“ (Feld
`note`) zu unterscheiden, obwohl beide Freitext sind: `note` bezieht sich auf
das einzelne Lasso-Stück in dieser Quelle, etwa fehlende Stimmen oder einen
Verweis auf eine LVanh-Nummer, den `read_manuscripts` per Regex ausliest.
„Bemerkung (Quelle)“ bezieht sich dagegen auf die Handschrift als
physisches Objekt, etwa Schreibervermerke oder Datierungsnotizen im
Manuskript selbst, siehe das Beispiel zu CH-Bu F. IX. 49. Ein gemeinsames
Feld hätte diese beiden Ebenen vermischt und zugleich riskiert, den
LVanh-Verweis-Mechanismus durch einen zweiten, unerwarteten Freitext in
derselben Spalte zu stören.

**Warum `shelfmarkAlt` und nicht ein weiteres Element in `shelfmark`.**
„Weitere Signatur“ bezeichnet laut Quelle eine zusätzliche oder frühere
Signatur derselben Bibliothek, keine zweite unabhängige Fundstelle. Ein
eigenes Feld hält diese Unterscheidung sichtbar, statt sie in einer Liste zu
verstecken, die suggerieren würde, beide Signaturen seien gleichrangig.

**Preis.** `ManuscriptWitness` wächst von zwölf auf achtzehn fachliche Felder
(ohne `@id`, `@type`, `id`, `source` und `extra` mitgezählt), was Abschnitt
14s Argument, eine Handschrift habe „andere Felder“ als ein
Druck, weiter verstärkt. Wie bei `sourceDescription` und `rismSiglum` werden
auch die neuen Felder unverändert als Rohtext übernommen, ohne Zerlegung
(`Datierung` etwa bleibt Freitext wie „um 1590 - 1605“ oder „17. Jh.“, nicht
in Jahr oder Zeitraum geparst) und ohne Prüfung gegen eine Normdatei (`Link`
wird nicht auf Erreichbarkeit getestet). Die ID-Registry blieb von diesem
Import unberührt, da sich an den für den Wiedererkennungsschlüssel
verwendeten Feldern (LV, LVanh, Unternummer, RISM-Sigel, Signatur) nichts
geändert hat, 0 neue IDs bei 8939 unveränderten Zeugnissen.

---

## 17. Fassungen als Expression statt als eigenes Werk

**Entscheidung.** Einträge mit Fassungskennzeichnung, etwa `74 (IV)` oder
`193 (II)`, bilden kein eigenes Werk mehr. Sie werden als `Expression` in der
neuen Datei `expressions.json` geführt und verweisen über `realizationOf` auf
das Werk mit der Grundnummer. Das Werk listet seine Fassungen umgekehrt in
`expressions`. Das Feld `lvVariant` entfällt in `works.json`, in
`entries.json` bleibt es als Teil der zeilengetreuen Quelle erhalten.

**Befund.** Die römische Ziffer zählt nicht Fassungen durch, sondern
bezeichnet den Teil (Pars) des Werks, von dem eine abweichende Fassung
existiert, jeweils in einem anderen Druck und mit anderer Stimmenzahl.
`193 (II)` ist der zweite Teil von LV 193 sechsstimmig im Druck 1564-7,
`193-2` derselbe Teil fünfstimmig im Druck 1566-8. Ebenso entspricht
`326 (II)` dreistimmig dem sechsstimmigen `326-2`. Betroffen sind 9 Einträge
zu 7 Werken (LV 74, 100, 182, 193, 246, 326, 327).

**Begründung.** Bisher erschien jede Fassung als eigenes Werk mit eigener
Detailseite, obwohl sie fachlich dieselbe Komposition in anderer Gestalt ist.
FRBR und IFLA LRM fassen genau das als Expression: eine bestimmte
Realisierung eines Werks, hier in abweichender Besetzung. Damit wird nach
Werk und Manifestation (Abschnitt 6) eine weitere Ebene des Modells
übernommen, beschränkt auf den Fall, den die Quelle ausdrücklich kennzeichnet.

**Zuordnung zum Gesamtwerk.** Die Expression verweist auf das Gesamtwerk,
nicht auf den einzelnen Teil-Datensatz, und behält die Ziffer als `pars`. Die
Ziffer lässt sich nicht verlässlich auf eine Teilnummer abbilden: Bei LV 74
war der Datensatz `74` die Überschrift „Sestina:“, sodass `74 (III)`
(„Secchi vedransi“) nicht `74-3` entsprach, sondern `74-4`. Seit die
Überschriftzeile entfernt ist (Abschnitt 21), stimmen beide überein; die
Zuordnung zum Gesamtwerk bleibt dennoch, weil dieselbe Verschiebung bei
künftigen Korrekturen erneut auftreten kann. Eine Zuordnung über den Titel
wurde aus demselben Grund wie in Abschnitt 7 verworfen.

**Alternativen.** Eine Expression für jedes Werk, auch ohne Fassung, wie es
FRBR streng genommen verlangt. Das hätte rund 2000 inhaltsleere Datensätze
erzeugt. Ebenso ließen sich die 32 LV-Nummern, die in mehreren Drucken mit
abweichender Stimmenzahl stehen (Abschnitt 6, etwa LV 90), als Expressions
fassen. Das bleibt offen, weil die Quelle diese Fälle nicht als Fassung
kennzeichnet und die Abgrenzung fachlich zu prüfen ist.

**Preis.** Die Kennung `@id` der neun früheren Fassungs-Werke (etwa
`work:74-IV`) entfällt; sie heißen jetzt `expression:74-IV`. Interne IDs der
Einträge sind nicht betroffen, die Registry bleibt unverändert. Wer Werke
zählt, erhält 2161 statt bisher 2170.

---

## 18. Teil-Beziehung und bevorzugter Titel ausdrücklich im Datensatz

**Entscheidung.** Zwei Angaben, die sich bisher nur erschließen ließen,
stehen jetzt ausdrücklich in `works.json`:

- **Teil-Beziehung.** Ein Teilsatz wie `100-2` trägt `isPartOf: "work:100"`,
  das Gesamtwerk umgekehrt `hasPart` mit seinen Teilen in Katalogreihenfolge.
  Beide Felder sind auf `dcterms:isPartOf` und `dcterms:hasPart` abgebildet.
- **Bevorzugter Titel.** Die Titelliste `titles` ist ersetzt durch
  `preferredTitle` und `variantTitles`, in `works.json` wie in
  `expressions.json`. Bevorzugt ist der Titel des frühesten Drucks, nach Jahr
  und laufender Nummer im Jahr, bei Werken ohne Druck der Titel der ersten
  Handschrift. Alle übrigen Titel stehen als Varianten in Quellreihenfolge.

**Begründung.** FRBR und IFLA LRM sehen Beziehungen zwischen Werken als
eigene Aussage vor, nicht als Folgerung aus einer Nummernsyntax. Bisher
musste jede Anwendung die Logik von `lvBase` und `lvPart` selbst nachbauen,
die Oberfläche tat das an drei Stellen. Ebenso verlangt das Modell einen
bevorzugten Titel neben den Varianten. Der Haupttitel ergab sich bisher nur
daraus, dass der Import zuerst die Titel der Drucke einsammelt, eine
Eigenschaft der Schleifenreihenfolge, die eine spätere Änderung des Skripts
stillschweigend hätte brechen können.

**Ergebnis.** Alle 803 Teile haben ein Gesamtwerk. Fehlt es künftig einmal,
bricht der Import ab, statt einen Teil ohne Bezug zu schreiben. Die Regel für
den bevorzugten Titel liefert beim derzeitigen Bestand für alle 2161 Werke
denselben Titel wie bisher `titles[0]`; sie macht die geltende Praxis
ausdrücklich, ohne sie zu ändern.

**Preis.** `lvBase` und `lvPart` bleiben zusätzlich erhalten, die Teil-
Beziehung steht also doppelt im Datensatz. Das ist gewollt: Die Nummern sind
Teil der Katalogangabe und werden für Sortierung und Anzeige gebraucht. Wer
`titles` gelesen hat, muss auf die beiden neuen Felder umstellen.

---

## 19. Festgelegte Schreibweise je Person, Rohwert bleibt am Eintrag

**Entscheidung.** Rohwerte, die `raw/personen_normdaten.json` derselben GND
zuordnet, bilden in `persons.json` eine einzige Person. Sie trägt die ID
`person:gnd-<GND>`, eine festgelegte Anzeigeform `preferredName` und die
abweichenden Schreibweisen der Quelle als `variantNames`. Die Normdatei ist
dafür nach GND geordnet:

```json
"118731122": {
  "preferredName": "Clément Marot",
  "viaf": "59086239",
  "variants": ["Cl. Marot", "C.Marot", "Marot", "Clément Marot"]
}
```

Der Katalogeintrag behält den Rohwert in `textAuthor` und verweist zusätzlich
über `textAuthorPerson` auf die Person. Werk und Fassung führen in
`textAuthors` Personen-IDs statt Rohwerte. Rohwerte ohne Zuordnung bleiben je
eine eigene Person, mit dem Rohwert als `preferredName`.

**Anlass.** Werk und Fassung sammeln die Textdichter ihrer Einträge. Stand
ein Name in zwei Drucken verschieden, hatte das Werk scheinbar zwei
Textdichter: LV 90 und 94 (`Marot` und `C.Marot`), LV 98 (`G. Guéroult` und
`G.Guéroult`). Kein Werk hat tatsächlich mehrere Textdichter. Dabei fiel ein
Fehler auf: Die Personen-ID wurde aus dem Rohwert gebildet, wobei alles außer
a–z und 0–9 zu `-` wurde. `G. Guéroult` und `G.Guéroult` ergaben dieselbe ID,
die zweite Schreibweise verschwand stillschweigend aus `persons.json` und
konnte so auch keine GND erhalten.

**Alternativen.** Die Rohwerte im Eintrag durch die Anzeigeform ersetzen.
Oder die Varianten erst in der Oberfläche über die GND gruppieren.

**Begründung.** Abschnitt 8 lehnt eine *automatische* Normalisierung ab, weil
die Gleichsetzung zweier Namensformen eine fachliche Feststellung ist. Mit
der kuratierten GND-Zuordnung aus Abschnitt 15 ist diese Feststellung für die
verknüpften Personen getroffen und belegt; die Zusammenführung folgt allein
dieser Datei, nie einem Namensvergleich. Das entspricht dem Modell der
Normdaten (FRAD, IFLA LRM): eine Person mit einer bevorzugten und mehreren
abweichenden Namensformen. Den Rohwert zu ersetzen, hätte die Quellentreue
aus Abschnitt 4 verletzt, denn wie ein Druck den Namen schreibt, ist selbst
eine Angabe. Eine Gruppierung nur in der Oberfläche hätte jede weitere
Anwendung der Daten das Problem erneut lösen lassen.

**Anzeigeform.** Natürliche Reihenfolge (Vorname Name), im Deutschen übliche
Formen wie „Horaz“, „Vergil“ und „Thomas von Aquin“. Die GND-Ansetzung
(„Marot, Clément“, „Horatius Flaccus, Quintus“) ist für eine Werkliste
schlechter lesbar und bleibt über den GND-Link erreichbar.

**Unsichere Zuschreibung.** Ein Rohwert mit nachgestelltem Fragezeichen wie
„Ludwig Helmbold?“ setzt am Eintrag `textAuthorUncertain`. Weil Werk und
Fassung nur noch Personen-IDs führen, ginge das Fragezeichen dort verloren;
`uncertainTextAuthors` hält deshalb die Personen fest, deren Zuschreibung in
allen Einträgen des Werks unsicher ist.

**Absicherung.** Der Import bricht ab, wenn zwei verschiedene Rohwerte ohne
Zuordnung dieselbe Personen-ID ergäben oder ein Rohwert mehreren Personen
zugeordnet ist. Rohwerte in der Normdatei, die in keinem Eintrag vorkommen,
meldet er als Hinweis.

**Preis.** Die Personen-IDs der zusammengeführten Rohwerte, etwa
`person:c-marot` und `person:marot`, entfallen zugunsten von
`person:gnd-118731122`; eine Weiterleitung gibt es nicht, da die IDs bisher
nirgends referenziert waren. `nameRaw` in `persons.json` ist durch
`preferredName` und `variantNames` ersetzt. Die Anzeigeformen sind eine
redaktionelle Setzung und bei Bedarf in der Normdatei zu korrigieren.

---

## 20. Gattung und Sprache als Rohwerte am Eintrag

**Entscheidung.** Die neuen Spalten „Gattung“ und „Sprache“ in
`raw/Werke.xlsx` werden als `genre` und `language` an den Katalogeintrag
übernommen, unverändert wie in der Quelle. Werk und Fassung sammeln sie wie
Textprovenienz und Gesamtausgabe als Listen ohne Dubletten (`genres`,
`languages`).

**Alternative.** Ein festes Vokabular (Aufzählung im Schema) oder
Sprachcodes nach ISO 639.

**Begründung.** Die Spalten sind beim Anlegen noch leer, die tatsächlich
vorkommenden Werte stehen also noch nicht fest. Ein Vokabular vorab
festzulegen, hieße die Erfassung vorwegzunehmen. Wie bei den übrigen Feldern
(Abschnitt 4) bleibt der Rohwert erhalten; eine Normalisierung kann folgen,
sobald die Daten vorliegen.

**Preis.** Werte in mehreren Schreibweisen (etwa „lat.“ und „Latein“) oder
mehrere Sprachen in einer Zelle erscheinen als verschiedene Werte, auch im
Filter der Oberfläche. Werke, die nur handschriftlich überliefert sind,
haben vorerst keine Gattung und Sprache, da die Handschriften-Quelle diese
Spalten nicht führt.

---

## 21. Normalisierter Werktitel nach MGG, Drucktitel bleibt am Eintrag

**Entscheidung.** `raw/Werke.xlsx` erhält die Spalten „Titel normalisiert“
und „Titel normalisiert (Grundlage)“. Der Import übernimmt sie als
`normalizedTitle` und `normalizedTitleBasis` an den Katalogeintrag. Das Werk
(und die Fassung) trägt diesen Titel als `preferredTitle`, sofern alle seine
Einträge mit normalisiertem Titel denselben haben; `preferredTitleBasis`
nennt dann `normalized`, sonst `earliestSource` mit der Regel aus
Abschnitt 18. Der Eintrag behält seinen Titel in der Schreibung des Drucks,
alle Drucktitel stehen am Werk als `variantTitles`.

**Begründung.** Der Eintrag beschreibt ein Werk in einem bestimmten Druck
(Abschnitt 6), sein Titel ist Teil dieser Überlieferung und wird nicht
angetastet. Das Werk dagegen ist eine Abstraktion über alle Drucke und
Handschriften; ihm steht ein einheitlicher Titel zu, wie ihn IFLA LRM als
bevorzugten Namen (nomen) und die Bibliothekspraxis als Werktitel kennen. Der
Titel des frühesten Drucks taugte dafür nur bedingt: Er folgt der Orthographie
des 16. Jahrhunderts (`Gvarda'l mio stat'a`), ist oft abgekürzt und mitunter
eine Überschrift statt eines Titels (`Sestina:`, `Lectio prima.`).

**Quelle.** Grundlage ist `raw/Werke_MK.xlsx`, eine zeilengleiche
Arbeitskopie von `Werke.xlsx`, in der jeder LV-Nummer der Eintrag aus dem
Werkverzeichnis der MGG zugeordnet und dieser mit Grove abgeglichen ist. Die
Zuordnung zu MGG läuft über die LV-Nummer, nicht über den Titel. MGG wurde
dem früheren Abgleich mit IMSLP (`scripts/match_imslp.py`) vorgezogen, weil
dieser nur heuristisch über Titel, Band und Jahr zuordnen konnte und IMSLP
selbst Grove folgt, also keine eigenständige Quelle ist.

Nach der Übernahme wurde `Werke.xlsx` von Hand korrigiert: Zeilen, die nur
ein beim Umbruch der TeX-Vorlage abgetrennter Titelrest (249-2 „qu esiui“)
oder eine Überschrift (74 „Sestina:“) waren, sind entfernt und die
Folgezeilen neu nummeriert. Damit ist `Werke.xlsx` nicht mehr zeilengleich
mit `Werke_MK.xlsx` und für die normalisierten Titel maßgeblich. Das Skript
schreibt seither nicht mehr in `Werke.xlsx`, sondern leitet die Titel nur
noch zur Kontrolle ab; MGG und Grove ordnet es dazu wie die Formeln in
`Werke_MK.xlsx` über die LV-Nummer zu, aus deren Blättern *MGG-Werke* und
*Grove-Werke*. Abweichungen zwischen Tabelle und Regel weist
`docs/titel-normalisierung.md` gesondert aus.

**Ableitungsregeln** (`scripts/normalize_titles.py`):

- Der MGG-Titel wird ohne Anführungszeichen und ohne vorangestellte MGG-
  Zählnummer übernommen (`6. Litaniae …` wird `Litaniae …`).
- Messen erhalten „Missa“ vorangestellt, da MGG nur den Beinamen nennt
  (`Iager` wird `Missa Iager`). Magnificat, Nunc dimittis und Benedictus,
  die MGG nur mit der Tonart führt (`Primi toni`), erhalten den Namen des
  Canticums (`Magnificat primi toni`).
- Teile, die MGG nicht einzeln führt, werden in der Teilangabe des
  Gesamtwerks gesucht, ersatzweise in der Teilangabe von Grove, und zwar über
  den Titel, nicht über die Teilnummer. Die Teilnummer im LV deckt sich nicht
  verlässlich mit der Pars-Zählung in MGG, weil der LV mitunter eine
  Überschrift als eigene Zeile führt (Abschnitt 17). Aus demselben Grund
  ordnete das Skript 28 Teile neu zu, bei denen `Werke_MK.xlsx` über die
  Nummer einen benachbarten Teil getroffen hatte (etwa LV 74-4
  „Secchi vedransi“, dort „Io vo fuggendo“). Nach Entfernen der
  Überschriftzeile bei LV 74 sind es noch 23.
- Für die zwölf untextierten Bicinien nennt MGG nur den Sammeltitel; sie
  bleiben ohne normalisierten Titel.

**Alternativen.** Den Werktitel in einer eigenen Werktabelle pflegen statt
als Spalte an jeder Druckzeile. Das wäre sauberer, weil der Titel dann nur
einmal je Werk stünde, verlangt aber eine zweite Tabelle mit eigener Pflege;
die Spalte hält die Erfassung bei einer Datei. Widersprechen sich die Zeilen
eines Werks, fällt der Import auf die bisherige Regel zurück, statt einen
Titel zu wählen. Ebenso verworfen wurde, Titel ohne Treffer automatisch aus
dem Drucktitel zu normalisieren (u/v, i/j, Abkürzungen): Das wäre eine eigene
Edition und keine Übernahme einer zitierfähigen Quelle.

**Preis.** 280 Zeilen bleiben ohne normalisierten Titel, überwiegend die
Abschnitte von Offizien, Matthäuspassion, Bußpsalmen, Stabat mater und
Litanei, die MGG nicht einzeln nennt; 492 Werke behalten deshalb den Titel des
frühesten Drucks. Die normalisierte Schreibung ist die der MGG, mit deren
Eigenheiten und gelegentlichen Fehlern (LV 122-2 „Cum dederit delictis
suis“). Alle offenen und auffälligen Fälle stehen in
`docs/titel-normalisierung.md`, ebenso die Abweichungen bei Stimmenzahl und
Erstdruck gegenüber MGG und Grove.

---

## 22. Eigener Gesamttitel als Zeile `N`, erster Teil als `N-1`

**Entscheidung.** Bei mehrteiligen Werken gibt es in `Werke.xlsx` zwei
Fälle, die jetzt unterschiedlich erfasst werden:

- **Der erste Teil trägt zugleich den Titel des Gesamtwerks**, etwa
  LV 74 „Non ha tante serene“. Die Zeile `N` ist dann Gesamtwerk und erster
  Teil in einem, die Teilzählung beginnt mit `N-2`. So war es bisher für
  alle Werke.
- **Das Gesamtwerk hat einen eigenen Titel**, der nicht der Anfang des
  ersten Teils ist, etwa die Offizien LV 530 bis 533 („Officium Natalis
  Christi“) oder LV 1061. Die Zeile `N` trägt dann nur den Gesamttitel, der
  erste Teil steht als eigene Zeile `N-1` (bei LV 530 der Introitus „Puer
  natus est nobis“). LV 534, die Matthäuspassion, war schon vorher so
  erfasst.

**Befund.** Bisher stand bei den Offizien in der Zeile `N` der Titel des
Introitus als Drucktitel, als normalisierter Titel aber der Offiziumstitel
aus MGG. Dieselbe Zeile beschrieb also zwei verschiedene Dinge, und der
Introitus erschien in der Teilliste des Werks nicht als eigener Teil.

**Begründung.** Gesamtwerk und Teil sind nach Abschnitt 18 eigene Werke mit
`isPartOf`/`hasPart`. Fällt der Titel des ersten Teils mit dem Gesamttitel
zusammen, wäre eine zusätzliche Zeile `N-1` eine reine Dublette. Hat das
Gesamtwerk dagegen einen eigenen Titel, braucht der erste Teil einen eigenen
Datensatz, sonst geht er als Teil verloren. Der Import musste dafür nicht
geändert werden: `N-1` wird wie jeder andere Teil an `work:N` gehängt.

**Alternativen.** Einheitlich für alle mehrteiligen Werke eine Zeile `N-1`
anzulegen hätte bei rund 350 Werken eine Zeile erzeugt, deren Titel mit dem
des Gesamtwerks identisch wäre. Eine eigene Spalte, die den Fall kennzeichnet,
wurde verworfen, weil die Nummernsyntax ihn bereits eindeutig ausdrückt und
der Import dafür keine zusätzliche Regel braucht.

**Weitere Korrekturen im selben Arbeitsgang.** Die Zeilen 370-2 bis 370-13
sind entfernt. „Al dolce suon“ ist ein Gemeinschaftszyklus, und diese
Zeilen waren die Abschnitte der übrigen Beteiligten. Die Namen in ihrer
Spalte Textdichter (Gioseffo Guami, Simon Gatto, Massimo Troiano u. a.)
waren keine Textdichter, sondern die Komponisten dieser Abschnitte. Damit
entfallen zehn Personen aus `persons.json`. Die Teile von LV 534 tragen
jetzt den Erstdruck 1575-3/I, der bisher nur an der Zeile `534` stand.

**Preis.** Weil die Registry Zeilen über LV-Nummer und Erstdruck
wiedererkennt (Abschnitt 7), behalten die Zeilen 531 bis 533 ihre interne ID,
bezeichnen aber jetzt das Offizium statt des Introitus; der Introitus erhält
als `N-1` eine neue ID. Bei LV 530 ist es ebenso. Die 36 Teile von LV 534
erhalten wegen des nachgetragenen Erstdrucks neue IDs, ihre alten verwaisen,
ebenso die IDs der entfernten Zeilen. Insgesamt wurden 46 IDs neu vergeben.
Wer eine der betroffenen IDs bereits zitiert hat, landet damit beim
Gesamtwerk oder bei einer verwaisten Nummer. Nach einer förmlichen
Veröffentlichung, etwa über Zenodo, wären solche Korrekturen nur noch mit
einer Zuordnungsliste alter auf neue IDs vertretbar.

---

## 23. Drucknachweise als eigene Quelle, Zuordnung zu RISM über den Inhalt

**Entscheidung.** Drei zusammenhängende Festlegungen:

1. **Drucknachweise als eigene Quelle.** Die aus dem Gesamtregister
   (`raw/LASSTEST.TEX`) abgeleitete Tabelle `raw/Gesamtregister_Drucke.xlsx`
   wird als dritte Quelle importiert, nicht in `Werke.xlsx` übertragen. Jedes
   Werk erhält `printAppearances` (Druck und Stücknummer), `prints.json`
   führt alle 479 Drucke statt nur der 142 Erstdrucke.
2. **Redaktionelle Entscheidungen in eigener Datei.** Die 23 Erstdruck-Siglen,
   die `Werke.xlsx` anders zählt als das Register, werden in
   `raw/siglen_konkordanz.json` entschieden (`gleicherDruck`,
   `geltendeSigle`), nicht in der erzeugten Tabelle.
3. **RISM-Zuordnung über den Inhalt.** Die RISM-Kennung eines Drucks wird
   nicht über das Druckeverzeichnis oder die Sigle gesucht, sondern über die
   Menge der enthaltenen LV-Nummern im selben Jahr. Vorschläge stehen in
   `raw/drucke_rism.json` und werden erst nach Bestätigung importiert.

**Begründung zu 1.** Werk und Druck stehen in einer n:m-Beziehung: 7669
Nachweise zu 1175 Werken, im Schnitt sechs bis sieben Drucke je Werk. In
`Werke.xlsx`, eine Zeile je Werk, ließe sich das nur durch vervielfachte
Zeilen oder Listen in einer Zelle abbilden. Zudem ist `Werke.xlsx` von Hand
gepflegt, die Drucknachweise sind maschinell abgeleitet; vermischt ließe sich
die Ableitung nicht mehr neu erzeugen, ohne Handarbeit zu überschreiben
(Abschnitte 4 und 5). Die Nachweise sind keine eigenen Datensätze, sondern
Angaben am Werk, und erhalten deshalb keine ID in der Registry (Abschnitt 7).
Das Register führt Werke nur mit der Grundnummer; die Nachweise hängen daher
am Gesamtwerk, nicht an den Teilen.

**Begründung zu 2.** `Gesamtregister_Drucke.xlsx` wird bei jedem Lauf neu
geschrieben. Eine Entscheidung in einer Spalte dieser Tabelle ginge beim
nächsten Lauf verloren. Das Muster folgt `raw/personen_normdaten.json`
(Abschnitt 15): Das Skript ergänzt offene Fälle, Entscheidungen trifft und
ändert nur die Redaktion. Bestätigt `gleicherDruck` eine Gleichsetzung,
führen Import und Register beide Siglen als einen Druck unter der geltenden
Sigle, die andere steht in `siglumVariants`. 1069 der 1128 rot markierten
Zeilen der Registertabelle gehen allein auf diese 23 Fälle zurück.

**Begründung zu 3.** Das Druckeverzeichnis nennt zu jedem Druck die
RISM-Nummer, liegt aber nur als fehlerbehaftete Texterkennung vor (verlorene
hochgestellte Ziffern der B/I-Zählung). Die Siglen des Verzeichnisses
(etwa 1600-4) zählen anders als RISM B/I (1600/18) und lassen sich nicht
umrechnen. RISM selbst führt die Lasso-Drucke dagegen mit LV-Nummern an den
Einzelstücken (etwa A/I L 955 mit LV 848–879). Die Menge der LV-Nummern ist
damit ein Schlüssel, der in beiden Quellen unabhängig vorliegt und von
Schreibweisen nicht abhängt. Stücke, die RISM ohne LV-Nummer führt, zählen,
wenn die ersten drei Wörter ihres Titels mit einem Titel eines Werks im
jeweiligen Registerdruck übereinstimmen; verglichen wird nur innerhalb des
Paares, nicht gegen den ganzen Katalog, um Fehltreffer bei häufigen
Textanfängen gering zu halten. Maß ist der Jaccard-Index; eindeutig ist ein
Treffer ab 0,8 mit mindestens 0,15 Abstand zum zweitbesten Kandidaten, und
nur, wenn derselbe RISM-Druck nicht auch einem anderen Registerdruck am
besten entspricht.

**Datenstand.** Die RISM-Daten werden über die Such-API von RISM Online
(JSON-LD) abgerufen und als datierter Auszug in
`raw/rism/rism_lasso_drucke.json` abgelegt (`scripts/harvest_rism.py`), damit
der Abgleich auf einem festen, zitierbaren Stand beruht. RISM-Daten stehen
unter CC BY 4.0.

**Alternativen.** Die RISM-Nummern aus dem Druckeverzeichnis herauszulösen,
verworfen wegen der Fehler der Texterkennung; als Gegenprobe bleibt der Weg
offen. Der monatliche MARCXML-Gesamtexport von RISM wäre unabhängig von der
Erreichbarkeit der API, umfasst aber weit über eine Million Datensätze, von
denen 340 gebraucht werden. Eine Zuordnung über Titel und Drucker der
Druckausgabe scheitert daran, dass das Register keine Drucktitel enthält.

**Ergebnis (Stand 23.10.2026).** RISM liefert 340 Drucke mit Lasso als
Komponist von 1550 bis 1700, davon 282 mit A/I- und 99 mit B/I-Nummer. Von
den 478 Registerdrucken sind 75 eindeutig, 18 geteilt, 39 teilweise und 53
schwach zuzuordnen, 293 ohne Kandidaten. Für 7 der 23 Siglen-Fälle zeigt
RISM, dass beide Siglen denselben Druck meinen. Einzelheiten in
`docs/rism-abgleich.md`.

**Preis.** 193 RISM-Drucke führen ihren Inhalt nicht stückweise und lassen
sich über den Inhalt nicht vergleichen; sie bleiben der Handarbeit
überlassen, der Bericht nennt sie als Anhaltspunkt beim jeweiligen Jahr.
Nachdrucke mit gleichem Inhalt im selben Jahr sind am Inhalt nicht zu
unterscheiden. Die Drucknachweise werden importiert, obwohl die
Registertabelle noch nicht durchgesehen ist; ihre Prüfhinweise werden nicht
mit übernommen. `works.json` wächst dadurch von rund 2,0 auf 2,7 MB.

---

## 24. Erstdruck-Siglen in Werke.xlsx nach dem Register korrigiert

**Entscheidung.** Bei abweichend gezählten Erstdruck-Siglen (Abschnitt 23)
gilt die Sigle des Gesamtregisters. Die Korrektur erfolgt in `Werke.xlsx`
selbst, nicht über `raw/siglen_konkordanz.json`. Ein Teil wurde von Hand
korrigiert (u. a. 1560-1, 1562-5, 1585-7), 146 Zeilen per Skript:
Ersterscheinung 1566-10, 1567-2, 1567-8, 1567-11, 1569-12, 1570-20, 1581-4,
1582-4, 1585-1, 1586-7, 1590-1 und 1607-1 jeweils um eins erhöht, dazu
einzeln LV 508 (1573-9 → 1574-5), LV 743 (1583-4 → 1583-3) und LV 1148
(1610-1 → 1610-2). Geprüft wurde, dass sich außer diesen Zellen der Spalte
Ersterscheinung nichts geändert hat.

**Befund.** Die Abweichungen sind keine Verschiebung ganzer Jahrgänge,
sondern betreffen jeweils einen einzelnen Druck, dessen Nummer um eins zu
niedrig ist, während die Nachbarn stimmen (1582-3, 1582-6, 1582-7 gleich,
1582-4 statt 1582-5). Die richtige Nummer kommt in `Werke.xlsx` nie vor, und
die falsche hat dort kein einziges korrekt zugeordnetes Werk. Für sieben
Fälle bestätigt RISM über den Inhalt, dass beide Siglen denselben Druck
meinen (Abschnitt 23).

**Vermutete Ursache.** `Werke.xlsx` wurde maschinell aus dem nach
Erstdrucken geordneten LV-TeX (`LVTEX1.TEX`) erzeugt, mit der Regel „Eine
neue Drucknummer beendet die Gruppe“. Erkennt das Umwandlungsskript die
Überschrift eines Drucks nicht, erhalten dessen Werke die Nummer der
vorangehenden Überschrift, typischerweise eines Nachdrucks ohne eigene
Erstdrucke. Das erklärt beide Beobachtungen. Belegt ist es nicht, da
`LVTEX1.TEX` nicht vorliegt; mit der Datei ließe sich prüfen, ob dieselbe
Ursache weitere, bislang unauffällige Fehler erzeugt hat.

**Begründung.** Die Korrektur in der Quelle statt über eine Gleichsetzung in
`siglen_konkordanz.json` ist angemessen, weil es sich um Fehler der
Umwandlung handelt, nicht um zwei gleichberechtigte Zählungen. Bei den drei
Einzelfällen wäre eine Gleichsetzung zudem falsch: 1573-9, 1583-4 und 1610-1
sind echte Drucke mit weiteren, korrekt zugeordneten Werken; falsch war nur
die Zuordnung je eines Werks.

**Gleichgesetzt statt korrigiert.** Für LV 535–537 nennt das Register den
Druck 1575-3 ohne Band, `Werke.xlsx` 1575-3/III. Es ist derselbe Druck; die
Stückangabe des Registers („III/1“) bestätigt den dritten Band. Hier ist
`Werke.xlsx` genauer und bleibt unverändert; `siglen_konkordanz.json` setzt
beide Siglen gleich, mit 1575-3/III als geltender Sigle. Die Gleichsetzung
wirkt nur auf diese drei Werke, da 1575-3 ohne Band im Register sonst nicht
vorkommt.

**Einzeln geprüft.** Bei drei Fällen war der Vorschlag des Skripts keine
Angabe des Registers, sondern nur der früheste Druck, den das Register für die
Werke nennt. Sie wurden am Druckeverzeichnis geprüft, statt den Vorschlag zu
übernehmen:

- LV 1048–1060 (1599-4 → 1600-1) und LV 1066–1070 (1601-3 → 1602-1): Das
  Jahr wechselt, es handelt sich um Umdatierungen. Das Register hat recht;
  `Werke.xlsx` wurde korrigiert.
- LV 182: `Werke.xlsx` nannte 1570-4 als ersten vollständigen Druck, der
  Vorschlag 1564-3 ist nur der Druck des ersten Teils (Fassung `182 (I)`).
  Das Register führt 1570-4 bei LV 182 aber gar nicht; 1570-4 enthält dort
  ältere Werke (LV 74, 137–148), und die LV-Nummer ordnet das Werk den
  Drucken um 1564/65 zu, nicht 1570. Nach Prüfung am Druckeverzeichnis gilt
  1570-5, das auch das Register nennt. Der Fall zeigt, dass ein Wert aus
  `Werke.xlsx` wegen ihrer maschinellen Herkunft kein unabhängiger Beleg ist.

**Preis.** Da der Erstdruck zum Wiedererkennungsschlüssel gehört (Abschnitt
7), erhielten die korrigierten Zeilen neue interne IDs, zusammen mit den
übrigen Korrekturen dieses Arbeitsgangs 253; die alten IDs verwaisen. Die
roten Prüfhinweise der Registertabelle gingen von 1128 auf 0 zurück; jede
Erstdruck-Sigle aus `Werke.xlsx` kommt nun beim jeweiligen Werk auch im
Register vor.

---

## 25. Vorverarbeitung abgeschlossen, Excel-Tabellen sind die gepflegte Quelle

**Entscheidung.** Die Vorverarbeitung, aus der die Excel-Tabellen
entstanden sind, gilt als abgeschlossen und wird nicht mehr reproduziert. Im
Repository liegen nur noch die Dateien, die der Import liest: `Werke.xlsx`,
`Drucke.xlsx`, `lasso_handschriften.xlsx` und `personen_normdaten.json`.
Korrekturen werden unmittelbar in diesen Tabellen vorgenommen.

**Was entfiel.** Die Hilfsskripte `normalize_titles.py` und `match_imslp.py`
(Abschnitt 21), `parse_gesamtregister.py`, `harvest_rism.py` und
`match_rism.py` (Abschnitt 23), ihre Berichte (`titel-normalisierung.md`,
`imslp-abgleich.md`, `rism-abgleich.md`), ihre Ausgangsmaterialien
(`LASSTEST.TEX`, `Werke_MK.xlsx`, `Werke aus MGG.docx`,
`imslp_worklist.wiki`, der RISM-Abruf) sowie die Zwischendateien
`siglen_konkordanz.json` und `drucke_rism.json`. Ebenso
`bibel_abkuerzungen.json`, die weder Import noch Oberfläche lesen. Die
Abschnitte 21, 23 und 24 beschreiben diese Schritte weiterhin, als Nachweis,
wie die Tabellen entstanden sind; die genannten Skripte und Dateien sind nicht
versioniert, sondern außerhalb des Repositorys archiviert.

**Neue Datei `Drucke.xlsx`.** Sie ersetzt `Gesamtregister_Drucke.xlsx` und
die beiden JSON-Dateien zu Drucken:

- Blatt *Drucknachweise*: die Registertabelle ohne Prüfspalten, Farben und
  TeX-Zeilennummern, nur mit den Spalten, die fachlich etwas aussagen. Jahr
  und Nummer stehen nicht mehr gesondert, sondern nur in der Sigle, damit sie
  nicht auseinanderlaufen können. Zwei Korrekturen sind eingearbeitet: bei
  LV 388 „1504-2“ zu 1604-2 (Tippfehler der Vorlage; der Eintrag steht dort
  zwischen 1596 und 1609, gehört zur Nachdruckreihe 1592-1, 1596-1, 1612-1
  mit Stück 77, und im Druck 1604-2 fehlt genau Stück 77), bei LV 535–537
  1575-3 zu 1575-3/III (Abschnitt 24). Damit entfällt auch die Gleichsetzung
  über `siglen_konkordanz.json` und das Feld `siglumVariants`.
- Blatt *Drucke*: eine Zeile je Druck (477) mit der RISM-Zuordnung. Die 75
  eindeutigen Treffer aus Abschnitt 23 stehen mit RISM-Status „Vorschlag“
  und ihrer Grundlage darin, für weitere Drucke die Kandidaten als Hilfe zur
  Prüfung. Der Import übernimmt nur Zeilen mit RISM-Status „bestätigt“.

**Begründung.** Die Vorverarbeitung hat ihren Zweck erfüllt: Die Abweichungen
zwischen den Quellen sind geklärt (Abschnitt 24), weitere Korrekturen sind
fachliche Einzelentscheidungen am Datensatz und gehören in die Tabelle, nicht
in eine Korrekturliste, die bei jedem Neuaufbau angewendet werden müsste.
Eine Tabelle je Gegenstand ist für die redaktionelle Arbeit übersichtlicher
als eine Mischung aus Excel- und JSON-Dateien, und die Prüfung der
RISM-Vorschläge geschieht dort, wo auch die übrigen Angaben gepflegt werden.

**Preis.** Die Herleitung der Tabellen aus TeX-Vorlage, MGG, IMSLP und RISM
lässt sich aus dem Repository heraus nicht mehr nachvollziehen; Abschnitt 4
(Quelldateien bleiben unverändert erhalten) gilt nur noch für den Zustand der
Tabellen selbst, den Git versioniert. Ein erneuter RISM-Abruf, etwa nach
Ergänzungen bei RISM, müsste neu aufgesetzt werden.

---

## 26. Angaben zu den Drucken aus dem Druckeverzeichnis

**Entscheidung.** Aus den TeX-Dateien des Druckeverzeichnisses
(`texDateien/LVtex1.tex` bis `LVTEX9.TEX`) übernimmt
`scripts/tex_drucke.py` je Druck vier Angaben in neue Spalten des Blatts
*Drucke* von `raw/Drucke.xlsx`: die Überschrift unter der Sigle
(*Beschreibung*, etwa „Sammlung mit Erstbelegen“), den Titel des Drucks
(*Titel*), die Stimmbücher (*Stimmbücher*) und die Verweise auf andere
Verzeichnisse, eine Spalte je Verzeichnis (*Verweis RISM* „1581 a [L 924“,
*Verweis Boetticher* „1581 e“, …; nicht zuzuordnende Angaben in *Verweis
sonstige*). Aus der RISM-Nummer im Verweis ermittelt das Skript über die
Suche von RISM Online den Link zum Druck (*RISM laut Druckeverzeichnis*).
Der Import übernimmt alles nach `prints.json` als `description`, `title`,
`partbooks`, `references` (ein Feld je Verzeichnis) und `rismCatalogue`. Das
Skript füllt nur leere Zellen. Die TeX-Dateien selbst werden nicht
veröffentlicht; sie liegen nur lokal und stehen in `.gitignore`.

**RISM-Link.** Gesucht wird die RISM-Nummer als Phrase, „[L 924“ als
„A/I L 924“, „[LL 971 a“ als „A/I LL 971a“, „1565⁸“ als „B/I 1565/8“; nennt
der Verweis beide Reihen, zuerst A/I. Übernommen wird ein Link nur bei
genau einem Treffer. Er steht in einer eigenen Spalte neben der RISM-Zuordnung
über den Inhalt (Abschnitt 23) und ersetzt deren Bestätigung nicht: Stimmen
beide überein, ist das ein starkes Indiz, die Bestätigung bleibt eine
redaktionelle Entscheidung. Damit ist der in Abschnitt 23 verworfene Weg über
die RISM-Nummern des Druckeverzeichnisses doch gangbar geworden, weil jetzt
die TeX-Fassung statt der fehlerhaften Texterkennung vorliegt.

**Begründung.** Die Tabelle bleibt die gepflegte Quelle (Abschnitt 25); das
Skript ist eine einmalige Hilfe beim Befüllen, kein Teil des Imports. Weil
es bestehende Zellen nicht überschreibt, kann es nach einer Korrektur der
TeX-Dateien erneut laufen, ohne Handarbeit in der Tabelle zu zerstören;
Abweichungen meldet es nur. Die Angaben werden so diplomatisch wie möglich
übernommen: Zeilenwechsel des Titelblatts als „|“, Trennstriche „=“ und
Kürzungen („[sic]“, „⟨Drz⟩“) bleiben stehen, Nasalstriche und
übergeschriebenes e werden als kombinierende Unicode-Zeichen wiedergegeben
(m̄, uͤ), hochgestellte Ziffern als Hochzahlen (GA², RISM 1565⁸). Die
Verweise werden je Verzeichnis getrennt, damit sie einzeln auswertbar
sind; die Angabe selbst bleibt unzerlegt, da ihre Form je Verzeichnis
wechselt. Das Verzeichnis wird am Anfang des Verweises erkannt, nach einer
festen Liste im Skript; nennt ein Verweis zwei Verzeichnisse („EitnerV 1555;
EitnerQL 1555“), wird er am Semikolon geteilt.

**Lesart der Vorlage.** Die Dateien sind in DOS-Codepage 437 kodiert. In der
Fraktur-Umschrift steht `*u` für übergeschriebenes e (uͤ), `"u` für ü.
Zwei Fälle verlangen eine Festlegung: 1578-1 bis 1578-9 stehen in LVtex4 und
LVTEX5; es gilt die spätere Datei, deren Abschnitte vollständiger sind. Die
Teile mehrbändiger Drucke (1575-3/I–III, 1578-4/I–II, 1612-2/II) erhalten
die Angaben des Gesamtdrucks, den das Verzeichnis nur einmal beschreibt. Bei
Chorbüchern steht in *Stimmbücher* „Chorbuch“.

**Alternativen.** Die Verweise als eine Liste in einer Zelle zu lassen, so
die erste Fassung; verworfen, weil sich dann nicht nach einem Verzeichnis
filtern oder sortieren lässt. Die bestätigte RISM-Zuordnung automatisch aus
dem Link zu setzen; verworfen, siehe oben.

**Preis.** Die Zuordnung der Absätze folgt ihrer Reihenfolge in der Vorlage
(Verweise vor Titel vor Stimmbüchern). Steht dort Abweichendes, landet es
im falschen Feld. Verzeichnisse, die nicht in der Liste stehen, und
Schreibvarianten („Delmotte 34.“, „Vogel unter Lasso 65.“) landen in
*Verweis sonstige*. Das Skript braucht für den RISM-Link einen Zugang zu
RISM Online; der Stand ist der des Abrufs (23.10.2026). Einzelne Titel enthalten Zusätze des Verzeichnisses (Kolophon,
„Titel nicht erhalten“). Sechs Drucke des Verzeichnisses fehlen im Blatt
*Drucke* (1555-4, 1555-5, 1558-2, 1566-15, 1573-18, 1625-1), zwei Drucke des
Blatts im Verzeichnis (1629-2, 1773-9).

---

## 27. Interne ID nur noch in der `@id`

**Entscheidung.** Katalogeinträge und Handschriften-Zeugnisse tragen die
laufende Nummer aus der Registry (Abschnitt 7) nicht mehr zusätzlich als
Feld `id`, sondern nur noch in ihrer `@id`, etwa `entry:00001` oder
`manuscript:01980`. Das Feld `id` und seine Abbildung auf
`lasso:internalId` im JSON-LD-Kontext entfallen.

**Alternative.** Beide Felder beibehalten, die Zahl also als `xsd:integer`
neben der Kennung führen.

**Begründung.** `id` war vollständig aus `@id` ableitbar und umgekehrt. Zwei
Felder mit demselben Inhalt können auseinanderlaufen, und Lesern des
Datensatzes ist nicht klar, welches maßgeblich ist. Gebraucht wurde die Zahl
nur an zwei Stellen: zum Sortieren im Importskript und in der Oberfläche für
den Ersatztitel „Handschrift N“ bei Zeugnissen ohne Ortsangabe und Titel.
Beides liest die Nummer jetzt aus der `@id`. Die Vergabe und Stabilität der
Nummern ändert sich nicht.

**Preis.** Wer die Nummer als Zahl braucht, muss sie aus der `@id`
herausschneiden. Die `@id` ist fünfstellig mit führenden Nullen; ab der
Nummer 100000 würde eine rein alphabetische Sortierung falsch, deshalb
sortiert der Import numerisch.

---

## 28. Kein eigenes Feld für den Titel mit Teilsatzmarke

**Entscheidung.** Katalogeinträge tragen den Titel nur noch einmal, als
`title` ohne die führende Teilsatzmarke (`[2] Tengan dunque` wird
`Tengan dunque`). Das Feld `titleRaw`, das den Titel mitsamt Marke
unverändert aus der Quelle wiedergab, entfällt. Der Import prüft stattdessen,
dass die Marke zur Teilsatznummer der LV-Angabe passt, und meldet jede
Abweichung.

**Alternative.** `titleRaw` als Rohwert beibehalten, wie in Abschnitt 4
ursprünglich vorgesehen.

**Begründung.** Die Marke wiederholt die Teilsatznummer, die als `lvPart`
ohnehin am Eintrag steht. Geprüft wurde das für alle 2043 Einträge: Bei
2042 war `titleRaw` entweder gleich `title` oder `[N] ` vor `title` mit N
gleich `lvPart`. Die eine Abweichung, LV 419-4 mit der Marke `[2]`
(Druck 1571-4), war ein Fehler der Quelle; die LV-Angabe ist in
`raw/Werke.xlsx` zu 419-2 korrigiert. `titleRaw` enthielt damit keine
Information, die nicht schon in `title` und `lvPart` steht. Der unveränderte
Zellinhalt bleibt in `raw/Werke.xlsx` erhalten und ist über LV-Nummer und
Erstdruck auffindbar, das genügt der Nachprüfbarkeit nach Abschnitt 4. Die Prüfung im
Import sorgt dafür, dass eine künftige Abweichung nicht stillschweigend
verloren geht, sondern auffällt.

**Preis.** Wer den Titel in der Form der Quelle braucht, muss die Marke aus
`lvPart` wieder voranstellen oder die Quelldatei lesen. Durch die Korrektur
erhält die Zeile ihre frühere interne ID `entry:00708` zurück, die ihr unter
dem Schlüssel `419-2` schon bei der ersten Vergabe zugeteilt war;
`entry:00710` (unter `419-4`) entfällt.

---

## 29. Keine Angaben zur Importherkunft am Datensatz

**Entscheidung.** Katalogeinträge und Handschriften-Zeugnisse tragen kein
Feld `source` mehr. Es nannte je Datensatz den Herkunftsdatensatz
(`dataset`), die Quelldatei (`file`), die Zeile darin (`row`) und den
Wiedererkennungsschlüssel der Registry (`key`). Die Felder und ihre
Abbildungen im JSON-LD-Kontext entfallen.

**Alternative.** `source` auf `dataset` und `row` kürzen, da `file` über
`meta.json` und `key` über die ID-Registry ohnehin nachzuschlagen waren.

**Begründung.** Die Daten werden in einem öffentlichen Repository
veröffentlicht und sollen fachliche Aussagen über Lassos Werke und ihre
Überlieferung enthalten. `source` beschrieb dagegen den Importvorgang, also
interne Technik: Das Importskript schrieb das Feld, las es aber selbst nie,
und die Oberfläche benutzte es nicht. Die Zeilennummer galt zudem nur für den
Stand der Quelldatei im selben Commit, da sich die Zeilen der gepflegten
Tabellen (Abschnitt 25) durch Einfügen oder Löschen verschieben.
Nachprüfbar bleibt die Umwandlung trotzdem (Abschnitt 4): Die Quelldateien
liegen im Repository, und jeder Eintrag ist
dort über seine fachlichen Angaben wiederzufinden (LV-Nummer und Erstdruck,
bei Handschriften RISM-Sigel und Signatur), aus denen auch der
Registry-Schlüssel gebildet wird.

**Preis.** Ein Datensatz verweist nicht mehr unmittelbar auf seine
Tabellenzeile. Wer ihn in der Quelle sucht, muss nach den fachlichen Angaben
filtern. Kommt eine zweite Tabelle desselben Typs hinzu (README, „Eine
weitere Excel-Tabelle aufnehmen“), ist am Datensatz nicht mehr zu sehen, aus
welcher er stammt; dann wäre zu entscheiden, ob das eine fachliche Angabe
ist, die wieder ein Feld verdient.

---

## 30. Ungenutzte Zähl- und Konstantfelder entfernt

**Entscheidung.** Entfallen sind `entryCount` an Werken und Personen,
`workCount` und `no` an Drucken sowie `role` an Personen.

**Begründung.** Die Zähler sind aus den Listen am Datensatz bzw. aus den
Einträgen ableitbar, `no` steht schon in der Sigle, und `role` hatte überall
denselben Wert `textAuthor`. Keines der Felder wurde von der Oberfläche
gelesen. Geprüft wurden alle Felder aller Dateien; behalten wurde, was die
Oberfläche nutzt, was der Import intern braucht (`lvVariant`) oder was einen
Rohwert der Quelle trägt (`textAuthor`, `voicesRaw`).

---

## 31. Ein RISM-Link je Druck, aus dem Druckeverzeichnis

**Entscheidung.** Drucke tragen nur noch ein Feld `rism`: den Link auf RISM
Online, den `scripts/tex_drucke.py` aus der RISM-Nummer im Druckeverzeichnis
ermittelt (Abschnitt 26, bisher `rismCatalogue`). Die Zuordnung über den
Inhalt (Abschnitt 23) mit Vorschlag und Bestätigung entfällt, ebenso
`rismSeries`. Im Blatt *Drucke* sind die Spalten *RISM*, *RISM-Reihe*,
*RISM-Status*, *RISM-Grundlage* und *RISM-Kandidaten* gelöscht; *RISM laut
Druckeverzeichnis* heißt jetzt *RISM*.

**Begründung.** Zwei Wege zum selben Ergebnis. Von den 75 Vorschlägen der
Inhaltszuordnung waren 61 identisch mit dem Link aus dem Druckeverzeichnis,
keiner wich ab; bestätigt war keiner, `rism` war also überall leer. Der Link
aus dem Druckeverzeichnis liegt dagegen für 427 von 477 Drucken vor und
beruht auf der RISM-Nummer, die das Verzeichnis selbst nennt.

**Preis.** 14 Vorschläge betrafen Drucke ohne Link im Druckeverzeichnis;
sie sind nur noch in der Git-Historie von `raw/Drucke.xlsx` erhalten. Die in
Abschnitt 26 vorgesehene redaktionelle Bestätigung entfällt.

---

## 32. `data/` enthält nur fachliche Daten

**Entscheidung.** `data/meta.json` entfällt. Die ID-Registry liegt nicht mehr
in `data/`, sondern als `scripts/id-registry.json` beim Importskript.

**Begründung.** `data/` ist der veröffentlichte Datenbestand. `meta.json`
enthielt Erzeugungsdatum, Zählungen und Prüfsummen der Quellen, also
Angaben zum Importlauf; die Oberfläche las sie nicht, die Zählungen ergeben
sich aus den Daten selbst, und den Stand der Quellen belegt Git
(Abschnitt 4). Die Registry ist ebenfalls Importtechnik, muss aber
versioniert bleiben, damit die IDs stabil bleiben (Abschnitt 7); sie gehört
deshalb zum Skript, nicht zu den Daten.

---

## 33. Quellenart lesbar statt mit Teilfeldern

**Entscheidung.** Das Feld `sourceDescription` heißt jetzt `sourceType`
(Spalte „Quellenart“). Bei Stimmbüchern steht die Quellenart in der Tabelle
mit Teilfeldern, etwa `$a[Stimmbücher]$b[6]$c[C, A, T, B, 5, 6]`; der Import
macht daraus `Stimmbücher (6): C, A, T, B, Quintus, Sextus`. Die gezählten
Stimmen 5 bis 8 (auch V bis VIII) werden als Quintus, Sextus, Septimus und
Octavus ausgeschrieben, da eine bloße Ziffer nicht verständlich ist.
Klartext wie „Partitur“ bleibt unverändert.

**Lesart der Teilfelder** (aus den Werten erschlossen): `$a` Art der Quelle,
`$b` Anzahl der Stimmbücher, `$1` Gesamtzahl bei unvollständigem Satz
(„von 5“), `$c` die vorhandenen Stimmen (C, A, T, B = Cantus, Altus, Tenor,
Bassus; 5, 6 bzw. V, VI = Quintus, Sextus; „?“ unbekannt), `$d` Zusatz. Eckige
Klammern, nach bibliothekarischer Konvention Angaben des Bearbeiters,
entfallen; eine unbekannte Anzahl („?“) wird weggelassen.

**Begründung.** Rund 30 % der Zeilen trugen die Teilfelder, die übrigen
Klartext. In der Oberfläche erschien die Teilfeld-Form unverständlich. Ein
lesbarer Text in einem Feld genügt; eine Zerlegung in eigene Felder wäre
mehr, als gebraucht wird. Der Name `sourceDescription` klang zudem nach
Importherkunft (vgl. Abschnitt 29), gemeint ist die Quellenart.

**Korrekturen der Quelle.** In `raw/lasso_handschriften.xlsx` waren 22 Zellen
fehlerhaft gesetzt und sind berichtigt: fehlendes `$c` (11), `$b2]` statt
`$b[2]` (8), `$[c ?]` statt `$c[?]` (2), `$c ?]` statt `$c[?]` (1).

**Preis.** Die Unterscheidung zwischen Angaben der Quelle und des
Bearbeiters (eckige Klammern) geht in den Daten verloren; sie bleibt in der
Tabelle erhalten.

---

## 34. Textgattungen aus der Spalte „Textdichter“ in die Textprovenienz

**Entscheidung.** In `raw/Werke.xlsx` standen in der Spalte „Textdichter“
Angaben, die keine Personen sind, und wurden deshalb zu Personen in
`persons.json`. Sie stehen jetzt in „Textprovenienz“: „Tischgebet“
(LV 579 zweimal, LV 1073), „Gebet?“ (LV 1044) und „Schäfergedicht“
(LV 1047). „Anfang von Psalmus 130, Nachdichtung von Clement Marot“ (LV 155)
ist geteilt in den Textdichter „Clément Marot“, eine der in
`raw/personen_normdaten.json` erfassten Schreibweisen und damit mit der GND
verknüpft, und die Textprovenienz „nach Psalmus 130 (Anfang)“; das „nach“
kennzeichnet wie in den übrigen Zeilen der Spalte die freie Bearbeitung,
hier Marots Nachdichtung. „nach Villon“
(LV 766) bleibt als Textdichter stehen: Es nennt eine Person, nur mit
Einschränkung.

**Begründung.** Eine Person ist ein Mensch, der den Text verfasst hat; eine
Gattung oder Herkunft des Textes gehört in die Textprovenienz. In allen
Fällen war die Textprovenienz leer, es wurde nichts überschrieben.

---

## 35. Unsichere Zuschreibung am Eintrag, nicht im Personennamen

**Entscheidung.** Ein nachgestelltes „?“ im Rohwert des Textdichters
(„de Baif?“) markiert eine unsichere Zuschreibung. Der Import setzt dafür
wie bisher `textAuthorUncertain` am Eintrag (am Werk `uncertainTextAuthors`)
und entfernt das „?“ jetzt beim Bilden der Person. Personen ohne
GND-Zuordnung hießen bisher wie der Rohwert, mitsamt Fragezeichen. In
`raw/personen_normdaten.json` lautet die Schreibweise für Helmbold deshalb
„Ludwig Helmbold“ statt „Ludwig Helmbold?“.

**Begründung.** Unsicher ist, ob die Person den Text verfasst hat, nicht die
Person selbst. Die Oberfläche kann die Unsicherheit so einheitlich aus dem
Feld darstellen statt aus dem Namen.

**Weitere Prüfung der Personen.** Die Schreibweise „G.Guéroult“ kam in der
Quelle nicht mehr vor und ist aus `raw/personen_normdaten.json` gestrichen.
Der Rohwert „Saint Gelais“ (LV 761, „Puis que vivre en serviture“) bleibt
Mellin de Saint-Gelais zugeordnet, nicht seinem Onkel Octavien: Der Text
„Puisque vivre en servitude“, bekannt in der Vertonung von Pierre Sandrin,
wird Mellin zugeschrieben (Katalog der Médiathèque de la Philharmonie de
Paris; IMSLP, Kategorie Saint-Gelais, Mellin de).

---

## 36. Keine erzeugte Liste der Handschriften ohne Zuordnung

**Entscheidung.** Der Import schreibt `docs/handschriften-ohne-zuordnung.md`
nicht mehr; die Datei ist gelöscht. Die Anzahl der Zeilen ohne Zuordnung
nennt er weiterhin in seiner Ausgabe.

**Begründung.** Die Liste wiederholte, was in `manuscripts.json` steht
(`lv` und `lvAnh` leer), und zugeordnet wird ohnehin in
`raw/lasso_handschriften.xlsx`, wo sich die Zeilen über die leere Spalte „LV“
filtern lassen. In `docs/` gehört die Begründung des Projekts, kein
Nebenprodukt des Imports.

---

## 37. Keine Hüllenschemas und kein `$schema` in den Daten

**Entscheidung.** `schema/entries-file.schema.json` und
`schema/manuscripts-file.schema.json` sind gelöscht, ebenso der Verweis
`$schema` am Anfang von `entries.json` und `manuscripts.json`. Die Schemas
für den einzelnen Eintrag und das einzelne Zeugnis bleiben.

**Begründung.** Die Hüllenschemas dienten nur dazu, dass ein Editor die
Dateien beim Öffnen live prüft. Die Dateien werden aber nie von Hand
bearbeitet, und der Import prüft jeden Datensatz ohnehin selbst gegen
`entry.schema.json` und `manuscript.schema.json`, bevor er schreibt. `$schema`
war damit ein technisches Feld in den veröffentlichten Daten ohne Nutzen.

---

## 38. Werk, Expression und Manifestation im Vokabular von FRBR Core

**Entscheidung.** Der JSON-LD-Kontext bildet Werk, Fassung und Druck auf das
Vokabular FRBR Core (`http://purl.org/vocab/frbr/core#`) ab statt auf
projekteigene Begriffe: `Work` auf `frbr:Work`, `Expression` auf
`frbr:Expression`, `Print` auf `frbr:Manifestation`, `realizationOf` auf
`frbr:realizationOf` und die Liste `expressions` am Werk auf
`frbr:realization`. Die Daten selbst ändern sich nicht.

**Begründung.** Das Modell folgt seit Abschnitt 6 und 17 FRBR; die
projekteigenen Begriffe bildeten genau diese Klassen und Beziehungen nach.
Mit dem Standardvokabular ist das Modell auch für Dritte als FRBR erkennbar.

**Alternative.** LRMoo, der Nachfolger von FRBRoo auf Grundlage von
CIDOC CRM. Es verlangt Ereignisse zwischen Werk und Person (etwa
„Expression Creation“ statt eines Feldes Textdichter), zu jedem Werk eine
Expression, da eine Manifestation stets eine Expression verkörpert, und für
vertonte Texte eigene Werke, die die Vertonung aufnimmt. Das hätte Import,
Daten und Oberfläche umgebaut und Struktur verlangt, die die Quelle nicht
hergibt.

**Preis.** FRBR Core von 2005 wird nicht mehr gepflegt. Und FRBR sieht zu
jedem Werk eine Expression vor, während das Projekt nur die neun
gekennzeichneten Fassungen als Expression führt (Abschnitt 17); das Modell ist
damit nicht vollständig ausgeführt, die Begriffe bleiben aber zutreffend.

---

## 39. Weitere Standardbegriffe im Kontext, GND und VIAF als Adresse

**Entscheidung.** Wo ein Begriff aus den bereits verwendeten Vokabularen
genau passt, ersetzt er den projekteigenen:

| Feld | Begriff |
| --- | --- |
| `variantTitles` | `dcterms:alternative` |
| `textAuthors`, `textAuthorPerson` | `schema:lyricist` |
| `genre`, `genres` | `schema:genre` |
| `dating` | `dcterms:date` |
| `provenance` | `dcterms:provenance` |
| `literature` | `dcterms:isReferencedBy` |
| `link`, `rism` | `rdfs:seeAlso` |
| `gnd`, `viaf` | `schema:sameAs` |

`gnd` und `viaf` enthalten dafür die vollständige Adresse
(`https://d-nb.info/gnd/118593234`, `https://viaf.org/viaf/39382430`) statt
der bloßen Nummer; die Oberfläche verlinkt sie unmittelbar.

**Lücke geschlossen.** Die mit Abschnitt 16 hinzugekommenen Felder der
Handschriften (`dating`, `link`, `shelfmarkAlt`, `provenance`, `sourceNote`,
`literature`) standen nicht im Kontext und wären von einem JSON-LD-Programm
stillschweigend verworfen worden. Sie sind jetzt eingetragen; jedes Feld der
Datendateien hat eine Abbildung.

**Was projekteigen bleibt.** LV-Nummern, Stimmenzahl, Siglen, Gesamtausgabe,
Stimmbücher, Textprovenienz, Bibliothek, Signatur und die Verknüpfung vom
Werk zu Einträgen und Handschriften. Kein Standardbegriff trifft sie genau,
und ein ungenauer wäre schlechter als ein eigener.

---

## Bewusst nicht übernommene Standards

- **MEI**, die Music Encoding Initiative, ist für die Codierung von Notentext
  gedacht, nicht für Katalogmetadaten. Sie wird erst einschlägig, wenn Notentexte
  selbst erfasst werden sollen.
- **CIDOC-CRM, FRBRoo und LRMoo** zielen auf sammlungsübergreifende
  Interoperabilität von Institutionen. Der Modellierungsaufwand steht für ein
  Projekt dieser Größe in keinem Verhältnis. Die zugrunde liegende
  Unterscheidung von Werk und Manifestation wurde gleichwohl übernommen, siehe
  Abschnitt 6, für ausdrücklich gekennzeichnete Fassungen auch die Expression,
  siehe Abschnitt 17, im Vokabular über FRBR Core, siehe Abschnitt 38.
- **Triplestore und SPARQL** wurden aufgeschoben. Der JSON-LD-Kontext hält den
  Weg dorthin offen, ohne ihn jetzt gehen zu müssen.
- **GND und VIAF** sind für Textdichter mittlerweile für 36 von 84 Rohwerten
  manuell verknüpft, siehe Abschnitt 15; die übrigen bleiben offen, teils
  mangels eindeutigem GND-Treffer, teils schlicht noch ungeprüft. Drucke
  verweisen über `rism` auf RISM Online (Abschnitt 31). Das RISM-Sigel der
  Handschriften (`rismSiglum`, Abschnitt 14) wird ungeprüft als Rohtext
  übernommen, nicht gegen eine Normdatei validiert.

---

## Offene Punkte

- In den Repository-Einstellungen von lassoDB muss einmalig manuell GitHub
  Actions als Quelle für GitHub Pages eingestellt werden, das lässt sich nicht
  aus der Anwendung heraus auslösen.
- Die Versionspinnung zwischen Anwendung und Daten soll erst nach Stabilisierung
  des Schemas eingeführt werden.
- Eine Veröffentlichung des Datensatzes über Zenodo mit DOI ist vorgesehen, aber
  noch nicht eingerichtet.
- Einzelne Titel enthalten Zeichen aus der TeX-Vorlage, deren Bedeutung zu klären
  ist, etwa ein nachgestelltes Kreuz und eine auffällige Leerstelle.
- 48 von 85 Textdichter-Rohwerten haben noch keine GND/VIAF-Verknüpfung in
  `raw/personen_normdaten.json` (Abschnitt 15), meist weil sie noch nicht
  geprüft wurden, teils weil kein eindeutiger GND-Treffer vorlag. Zwei davon,
  „Berno von Cluny" und „Pierre Grognet", wurden geprüft und bewusst
  zurückgestellt, siehe Abschnitt 15.
- Das RISM-Sigel der Handschriften ist ungeprüft, siehe Abschnitt 14.
- 280 Katalogzeilen ohne normalisierten Titel, 84 mit stark vom Drucktitel
  abweichendem Titel sowie die Abweichungen bei Stimmenzahl und Erstdruck
  gegenüber MGG warten auf fachliche Prüfung, siehe Abschnitt 21.
- Sechs Drucke des Druckeverzeichnisses fehlen im Blatt *Drucke*, zwei
  Drucke des Blatts im Verzeichnis, siehe Abschnitt 26.
- 311 Handschriften-Zeugnisse und die Zuordnung der 161 LV-Anhang-Werke
  warten auf fachliche Prüfung, siehe Abschnitt 14.

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
