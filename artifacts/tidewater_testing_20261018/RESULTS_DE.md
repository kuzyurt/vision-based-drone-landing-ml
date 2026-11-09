# Tidewater: zusätzliche Flug- und Geschwindigkeitstests

18. Oktober 2026. Getestet wurde die unveränderte aktuelle R15-Policy in der
Tidewater-Spielszene, mit deren Grafik, Boot, Küstenroute und MuJoCo/PX4-Physik.
Es gab **kein Training und keine Änderungen an der Policy oder den Landekriterien**.
Die Ausführung erfolgte automatisiert auf der VM mit dem produktiven
ONNX-WebGPU/WASM/Pyodide-Stack, ohne Bedienung der Browseroberfläche.

## Ergebnis auf einen Blick

**26 neue Flüge: 5 bestätigte Bootslandungen, 21 erfolglose Bootsmissionen,
keine registrierte Kollision.** Die gezielt ausgewählten schwierigen Fälle sind
keine repräsentative Stichprobe für eine allgemeine Erfolgsquote.

- Die erste Serie mit schwierigen Startansichten: **0/18 Landungen**.
- Die acht ergänzenden Flüge mit anfangs sichtbarem Boot: **5/8 Landungen**.
- Mit Positionsfunk wurden **rund 1,00 m/s zweimal erfolgreich bestätigt**.
  Bei rund 1,35 m/s gelang keine Landung.
- Ohne Positionsfunk gelang eine Landung bei **rund 0,35 m/s**. Der zweite
  Versuch mit etwas größerem Abstand scheiterte bei derselben Geschwindigkeit.
  Eine zuverlässige Geschwindigkeitsgrenze ohne Funk ist damit nicht belegt.

## Anfangs sichtbares Boot: Bewegung getrennt von anfänglicher Suche

Die Ausgangsposition lag ungefähr 9 m hinter dem Boot, bei rund 4,5 m tatsächlicher
Körperhöhe und 20° Kameraneigung. Die Startaufnahme wurde geprüft: Das Boot war
sichtbar. Die Bestätigungsläufe begannen bei ungefähr 10,9 m Abstand und 5 m Höhe.
Das Boot wurde über seine normalen Motoren entlang der Küste bewegt; seine
Position wurde nicht direkt vorgeschrieben.

Geschwindigkeiten sind gemessen, nicht nur eingestellte Sollwerte. Bei Landungen
steht der Mittelwert der letzten etwa zwei Sekunden; bei Fehlschlägen der Wert
am Ende des Versuchs. Zeiten beginnen bei der Übernahme durch die Policy.

| Situation | Positionsfunk | Gemessene Bootsgeschwindigkeit | Ergebnis |
|---|---|---:|---|
| Boot ohne Motorantrieb | Aus | 0,005 m/s | Gelandet; 37,1 s |
| Langsame Fahrt | Aus | 0,349 m/s | Gelandet; 35,9 s |
| Langsame Fahrt, veränderter Start | Aus | 0,349 m/s | Keine Landung; 175,1 s |
| Fahrt, Boot anfangs sichtbar | Aus | 0,644 m/s | Keine Landung; 175,1 s |
| Fahrt, Boot anfangs sichtbar | An | 0,643 m/s | Gelandet; 41,1 s |
| Schnellere Fahrt | An | 1,003 m/s | Gelandet; 43,3 s |
| Schnellere Fahrt, veränderter Start | An | 1,004 m/s | Gelandet; 51,6 s |
| Höherer Geschwindigkeitsversuch | An | 1,350 m/s | Keine Landung; 175,1 s |

Das sind die höchsten in diesen Zusatztests nachgewiesenen Landegeschwindigkeiten,
keine universellen physikalischen Maxima. Oberhalb des ersten Fehlschlags wurden
die sichtbaren Startfälle nicht unnötig weiter nach oben wiederholt.

Die frühere einfache Tidewater-Prüfung ohne Funk bleibt gültig: Aus einer näheren
Startposition gelang eine Landung in 47,7 s, bei über den Flug gemittelten
0,63 m/s Bootsgeschwindigkeit. Die neuen Fehlschläge widersprechen diesem einzelnen
Erfolg nicht; sie zeigen, wie stark die Leistung von Abstand und Startansicht
abhängt. Insbesondere wäre „ohne Funk maximal 0,35 m/s“ eine falsche Verallgemeinerung.

## Die 18 schwierigeren Fälle

Die niedrigen Geschwindigkeitsfälle starteten ungefähr 9 m hinter dem Boot bei
rund 2 m Körperhöhe und 35° Kameraneigung. Die tatsächliche erste Aufnahme zeigte
nur Wasser. Diese Serie prüft deshalb wesentlich auch die selbständige Suche.
Zusätzliche Fälle kombinierten ungünstige Kamerarichtung, Wind, Bewölkung,
größeren Abstand beziehungsweise spätere Tageszeit. Die Wellenkonfiguration
blieb bei der bestehenden Begrenzung von 5 cm.

Alle folgenden Versuche endeten ohne Bootslandung. Die angegebenen Zeiten sind
Zeiten bis zur Übergabe an manuelle Haltefunktion, nicht erfolgreiche Landezeiten.

| Situation / eingestellte Geschwindigkeit | Ohne Positionsfunk | Mit Positionsfunk |
|---|---:|---:|
| Niedriger Start, Soll 0,6 m/s | 135,5 s | 175,1 s |
| Niedriger Start, Soll 1,0 m/s | 81,8 s | 125,0 s |
| Niedriger Start, Soll 1,4 m/s | 173,4 s | 101,1 s |
| Niedriger Start, Soll 1,8 m/s | 175,0 s | 151,9 s |
| Niedriger Start, Soll 2,2 m/s | 120,1 s | 153,4 s |
| Niedriger Start, Soll 2,8 m/s | 39,5 s | 38,7 s |
| Naher Start, stark versetzte Kamera und Wind | 85,6 s | 40,4 s |
| Rund 21 m Abstand, Bewölkung, Wind, Kamera abgewandt | 175,1 s | 175,1 s |
| Rund 41 m Abstand, spätere Tageszeit, Wind, Kamera abgewandt | 175,1 s | 175,0 s |

Beim höchsten Sollwert von 2,8 m/s fuhr das Boot am Abbruch tatsächlich etwa
2,64–2,65 m/s. Weder mit noch ohne Funk gelang eine Landung. Da diese Fälle
bereits an der Erfassung scheiterten, bestimmen sie keine reine Grenze des
Flug- oder Geschwindigkeitsreglers.

## Was die Aufzeichnungen erklären

In **17 der 18 schwierigen Flüge gab es keine einzige akzeptierte geometrische
Pad-Pose**. Im verbleibenden Flug gab es nur eine einzelne akzeptierte Messung,
keine bestätigte Messfolge. Auch die drei fehlgeschlagenen Zusatzflüge hatten
keine akzeptierte geometrische Pose. Dagegen hatten die fünf erfolgreichen
Zusatzflüge jeweils 690–943 akzeptierte Messbilder.

Das ist somit vor allem ein Problem der zuverlässigen Zielerfassung und
geometrischen Bestätigung unter diesen Tidewater-Ansichten. Es ist kein Beleg
dafür, dass die Drohne das bewegte Boot schon stabil vermessen hatte und sich
lediglich nicht zum Sinkflug „traute“. Der vorhandene Zielzustand mit Gedächtnis
hilft erst, wenn zuvor brauchbare Messungen etabliert wurden. Welcher einzelne
Schritt der Erfassung zuerst verbessert werden sollte, wurde hier nicht durch
Änderungen oder Training untersucht.

Bei den Fehlschlägen blieb die aufgezeichnete wahre Körperhöhe mindestens rund
1,67 m. Der unveränderte Spiel-Kollisionsprüfer registrierte in keinem der
26 Versuche eine Kollision. Das ist eine konkrete Beobachtung dieser Flüge,
keine allgemeine Zusicherung einer sicheren Rückkehr oder Kollisionsfreiheit.

## Einordnung und Nachweise

„Mit Funk“ bedeutet den simulierten Spielkanal: Positionsrauschen mit 0,25 m
Standardabweichung pro Koordinate, Aktualisierung mit 1 Hz, einschließlich der
normalen Verbindungslogik. Es wurde keine physische SX1262-Hardware geprüft.
Die tatsächliche Verfügbarkeit wurde pro Messbild protokolliert; ohne Funk
erhielt die Policy in keinem Bild gültige Bootspositionsdaten.

Die zuvor gemessenen **58/60** gehören zur ursprünglichen nativen Umgebung.
Sie sind keine Tidewater-Erfolgsquote. Die beiden früheren einfachen
Tidewater-Erfolge reichen angesichts dieser zusätzlichen Ergebnisse nicht als
Nachweis einer robusten Übertragung auf anspruchsvolle Spielsituationen.

Bei der nachträglichen Auswertung fiel außerdem auf: Die nominelle horizontale
2-m/s-Begrenzung ist nach der vorhandenen achsweisen Befehlsglättung keine
strikte Vektornormgrenze; aufgezeichnet wurden kurzzeitig bis 2,044 m/s.
Dies wurde dokumentiert, nicht während der Tests verändert. Die ursprünglichen
physischen Auflage-, Stabilitäts- und Motorabschaltungskriterien blieben unverändert.

Alle Originalaufzeichnungen, Modelle und fehlgeschlagenen Versuche bleiben
erhalten. Es gab keine neue Datensammlung für Training und keinen neuen Build.
Der kompakte lokale Nachweis wurde über SSH geladen und anhand seiner Prüfsummen
verifiziert. Vollständige Bildfolgen und Traces verbleiben auf der VM.

[Detaillierte Messwerte und Phasenzähler](verified/audited_results.json)
enthalten alle 26 Fälle und die Zuordnung zur unveränderten R15-Policy.
