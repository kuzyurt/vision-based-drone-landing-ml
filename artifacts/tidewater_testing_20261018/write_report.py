from pathlib import Path
import datetime,hashlib,json,shutil
r=Path(__file__).resolve().parent;repo=r.parents[1]
data=json.loads((r/'verified/audited_results.json').read_text())
by={x['id']:x for x in data['results']}
def de(v,n=1):return f'{v:.{n}f}'.replace('.',',')
def outcome(x):return ('Gelandet'if x['landed']else'Keine Landung')+'; '+de(x['flight_seconds'])+' s'
text='''# Tidewater: zusätzliche Flug- und Geschwindigkeitstests

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
'''
labels=[('visible_unpowered_visual','Boot ohne Motorantrieb'),('visible_slow_visual','Langsame Fahrt'),
 ('confirm_visual','Langsame Fahrt, veränderter Start'),('visible_0p6_visual','Fahrt, Boot anfangs sichtbar'),
 ('visible_0p6_radio','Fahrt, Boot anfangs sichtbar'),('midpoint_radio','Schnellere Fahrt'),
 ('confirm_radio','Schnellere Fahrt, veränderter Start'),('visible_1p4_radio','Höherer Geschwindigkeitsversuch')]
for key,label in labels:
    x=by[key];text+='| '+label+' | '+('An'if x['radio']else'Aus')+' | '+de(x['final_2s_speed_m_s']['mean'],3)+' m/s | '+outcome(x)+' |\n'
text+='''
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
'''
for stem,label in [('speed_0p6','Niedriger Start, Soll 0,6 m/s'),('speed_1p0','Niedriger Start, Soll 1,0 m/s'),
 ('speed_1p4','Niedriger Start, Soll 1,4 m/s'),('speed_1p8','Niedriger Start, Soll 1,8 m/s'),
 ('speed_2p2','Niedriger Start, Soll 2,2 m/s'),('speed_2p8','Niedriger Start, Soll 2,8 m/s'),
 ('close_oblique','Naher Start, stark versetzte Kamera und Wind'),('far20_cloudy','Rund 21 m Abstand, Bewölkung, Wind, Kamera abgewandt'),
 ('far40_late','Rund 41 m Abstand, spätere Tageszeit, Wind, Kamera abgewandt')]:
    text+='| '+label+' | '+de(by[stem+'_visual']['flight_seconds'])+' s | '+de(by[stem+'_radio']['flight_seconds'])+' s |\n'
text+='''
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
physischen Auflage-, Stabilitäts- und Entschärfungskriterien blieben unverändert.

Alle Originalaufzeichnungen, Modelle und fehlgeschlagenen Versuche bleiben
erhalten. Es gab keine neue Datensammlung für Training und keinen neuen Build.
Der kompakte lokale Nachweis wurde über SSH geladen und anhand seiner Prüfsummen
verifiziert. Vollständige Bildfolgen und Traces verbleiben auf der VM.

[Detaillierte Messwerte und Phasenzähler](../../../artifacts/tidewater_testing_20261018/verified/audited_results.json)
enthalten alle 26 Fälle und die Zuordnung zur unveränderten R15-Policy.
'''
target=repo/'landing_training/docs/reports/TIDEWATER_TEST_RESULTS_2026-10-18.md'
assert not target.exists();target.write_text(text,encoding='utf-8')
(r/'RESULTS_DE.md').write_text(text,encoding='utf-8')
backup=r/'docs_before_test_report';backup.mkdir()
for rel in ['landing_training/docs/CURRENT_POLICY.md','landing_training/README.md','tidewater-game/README.md']:
    p=repo/rel;q=backup/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
current=repo/'landing_training/docs/CURRENT_POLICY.md';s=current.read_text(encoding='utf-8')
anchor='## Deployment boundaries'
addition='''## Additional Tidewater stress tests — 18 October

The unchanged R15 subsequently completed26additional Tidewater flights:5boat
landings and21failedboatmissions,zero registeredgamecollisions. The18challenging
search/start cases all failed. Of8initially-visible diagnostic/speed cases,5landed.
Radio-enabled landings at a measured~1.00m/s passed twice;~1.35m/s failed.
Without radio,~.35m/s landed once and failed from a changed start;~.64m/s failed.
The earlier closer-start no-radio success at~.63m/s remains separate evidence,
so no reliable universal no-radio speed limit is established.

Failures overwhelmingly had no accepted geometric pad pose:17/18challenging
cases had zero,one had only1;all3failedvisible-start cases had zero. This exposes
acquisition/registration weakness,not a demonstrated pure flight-speed ceiling.
See the [full new test report](reports/TIDEWATER_TEST_RESULTS_2026-10-18.md).
No policy/training/physics changes were made for these tests.

'''
assert s.count(anchor)==1;s=s.replace(anchor,addition+anchor)
s=s.replace("horizontal command cap is 2 m/s, so stop or slow the boat", "nominal horizontal command limit is 2 m/s before per-axis slew (recorded\nvector norms reached 2.044 m/s), so stop or slow the boat")
current.write_text(s,encoding='utf-8')
for rel,anchor,addition in [
 ('landing_training/README.md','The root `policy.py` and `train.py` remain the original baseline implementation.',
  'Additional Tidewater stress tests exposed significant acquisition limits:0/18\nchallenging starts landed;5/8separate visible-start diagnostics landed. These\nresults do not change the native58/60measurement. See the\n[new Tidewater test report](docs/reports/TIDEWATER_TEST_RESULTS_2026-10-18.md).\n\n'),
 ('tidewater-game/README.md','A boat landing requires physical foot support and two seconds of stable,',
  '**Additional Tidewater stress tests:** the unchanged policy subsequently landed\nin0/18challenging search/start cases and5/8initially-visible diagnostic cases.\nWith radio,~1.00m/s landed twice;~1.35m/s failed. Without radio,even~.35m/s was\nstart-dependent. See the [new complete results](../landing_training/docs/reports/TIDEWATER_TEST_RESULTS_2026-10-18.md).\nThe earlier two simple successes are not evidence of general Tidewater reliability.\n\n')]:
    p=repo/rel;s=p.read_text(encoding='utf-8');assert s.count(anchor)==1;p.write_text(s.replace(anchor,addition+anchor),encoding='utf-8')
receipt=dict(status='completed_tidewater_tests_reported_no_policy_changes',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    tests=26,landings=5,registered_collisions=0,source_candidate_sha256=data['candidate_sha256'],
    archive_sha256=hashlib.sha256((r/'compact_results.tar.gz').read_bytes()).hexdigest(),
    report=str(target),report_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    no_training=True,no_policy_changes=True,no_new_build=True)
(r/'completion_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2))
