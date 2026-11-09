# Ausführungsanleitung zum unveränderten Plan

Diese Datei konkretisiert `PLAN.md`. Sie ändert weder Ziel, Episodenzahl,
Aufgabenumfang noch Zeitbudget. Der ursprüngliche Plan bleibt unverändert.

**Zustand bei Erstellung: Detailplan wartet auf menschliche Freigabe.**
Die acht bereits laufenden Zweck-Prüfflüge dürfen schließen. Lesen ihrer Ergebnisse,
Sicherung und sichere Bereinigung sind erlaubt. Vor Freigabe dieser Anleitung keine
weitere Sammlung, kein Training und keine neuen Benchmarks starten.

Nach Freigabe arbeitet der ausführende Agent selbständig. Der Nutzer ist anschließend
16 Stunden nicht erreichbar. Nicht auf erneute Sichtung, neue Fragen oder neue
Genehmigung für bereits hier erlaubte Schritte warten. Bei Unklarheit ein Artefakt
als ungeprüft ausschließen, vorhandene zulässige Arbeit fortsetzen und den Grund
dokumentieren. Keine Zustimmung, Messung oder erfolgreich absolvierte Phase erfinden.

## 0. Einstieg für einen neuen Agenten

1. Diese Datei vollständig lesen.
2. `PLAN.md`, `STATUS.md`, `EXECUTION_STATE.json` und `EXECUTION_CHECKLIST.json` lesen.
3. Prüfen, ob `PLAN_APPROVAL.json` existiert und eine tatsächliche spätere menschliche
   Planfreigabe samt Plan-/Runbook-Hash dokumentiert. Ein Timer-Impuls, alter
   Demo-Approval oder selbst geschriebenes `approved=true` ist keine Planfreigabe.
4. Bei fehlender Freigabe nur die oben erlaubten bestehenden Flüge/Sicherungen betreuen.
5. Bei vorhandener Freigabe aktuelle Uhrzeit, Prozesse, Dateien und Zustände lesen.
   Historische PIDs und alte Erfolgsmeldungen niemals als aktuellen Zustand übernehmen.
6. Den ersten noch nicht nachweislich abgeschlossenen Schritt der Checkliste bearbeiten.
   Bereits abgeschlossene Flüge, Caches und Trainingsläufe nicht aus Bequemlichkeit neu starten.
7. Nach jedem abgeschlossenen oder fehlgeschlagenen Schritt Zustand atomar speichern.
8. Alle 30 Minuten über den bestehenden Timer erneut einsteigen. Während eines aktiven
   Arbeitsschritts relevante neue Erkenntnisse kurz mitteilen; unveränderte Timer-
   Kontrollen bleiben still. Ein gestarteter Prozess ist kein fertiges Arbeitsergebnis.

### 0.1 Feste Orte und Werkzeuge

| Bezeichnung | Exakter Ort |
|---|---|
| Lokales Repository | `D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing` |
| Lokaler Arbeitsordner dieser Iteration | `D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/approved_curriculum_20261020` |
| VM-Login | `hxhshsh7gyg@34.87.180.165` |
| Erwarteter VM-Benutzer | `hxhshsh7gyg` |
| Erwarteter Hostname | `drone-test2-20261015-183521` |
| VM-Repository | `/home/hxhshsh7gyg/vision-based-drone-landing-ml` |
| VM-Python | `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/.venv/bin/python` |
| Alter Experimentordner, nur Referenz | `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z` |
| Neuer VM-Arbeitsordner | `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020` |
| Originaldaten-Manifest | `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/datasets/expert/manifest.json` |
| Geprüfte V31-Quellen | Alter Experimentordner + `/expert_fix_review_20261019/v31/sources` |
| Geprüfte lokale Videolieferung | Repository + `/artifacts/expert_fix_review_20261019/delivery_v31` |
| Lokale Sicherungsnachweise | Neuer lokaler Ordner + `/policy_backups/LATEST_VERIFIED.json` |
| 30-Minuten-Timer-ID | `finish-approved-mujoco-curriculum-and-local-policy-backup` |

SSH immer mit `BatchMode=yes`, `StrictHostKeyChecking=yes`, `IdentitiesOnly=yes`
und Schlüsselpfad `C:/Users/gamee/.ssh/id_ed25519` verwenden. Schlüsseldateien nie
öffnen oder ausgeben. Hostkey-Prüfung bei einem Fehler nicht abschalten.

Die lokale PowerShell arbeitet im Repository. Der vorhandene Transport kapselt
Argument-Quoting und die VM-Adresse. Beispiel für ein bereits existierendes kurzes
VM-Skript, das innerhalb von 240 Sekunden endet:

```powershell
Set-Location 'D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing'
python -c "import sys; sys.path.insert(0,'artifacts/approved_curriculum_20261020'); import transport; print(transport.run('inventory_data.py'))"
```

Dieses Beispiel ist eine Erklärung, **keine Aufforderung, den fertigen Inventarlauf
zu wiederholen**. Lange Arbeit wird über ein versioniertes Launcher-Skript im
Hintergrund auf der VM gestartet; der Launcher gibt PID und Receipt sofort zurück.
Nie eine stundenlang blockierende SSH-Sitzung als einzigen Supervisor verwenden.
SCP-Abschluss abwarten, bevor eine abhängige Datei benutzt wird.

### 0.2 Was bereits existiert und was noch implementiert werden muss

**Vorhanden und geprüft:** `transport.py`, `snapshot_policy.py`,
`backup_watcher.py`, `inventory_data.py`, `prepare_semantic_producer.py`,
`run_semantic_collection_v32.py`, `semantic_contract.py`,
`queue_semantic_pilots.py`, `launch_semantic_pilots.py`.

**Noch keine fertige ausführbare Gesamtpipeline:** vollständiger Pilot-Auditor,
passende Welt-/Szenencaches für die breite Sammlung, Originaldaten-Maskenproduzent
und dessen echter Trainingsconsumer, neue zugelassene Daten-/ROI-Caches,
Sammlungsorchestrator, neuer Trainer, eingefrorener Paarvergleich und Abschluss-
export müssen in den unten beschriebenen Phasen erstellt oder aus nachweislich
passendem bestehenden Code abgeleitet werden. Ihre im Folgenden angegebenen Namen
sind Ziel-Artefakte, **keine bereits vorhandenen Startbefehle**.

Ein Agent darf ein fehlendes Skript nicht durch das gleichnamige alte Skript aus
einer früheren Iteration ersetzen. Zuerst Implementierung, Eingaben, Tests und
Source-Hash prüfen. Alte Collector-/Trainer-Prozesse nicht wiederbeleben.

## 1. Unverhandelbare Grenzen

1. Alle Trainingsbilder entstehen ausschließlich in MuJoCo. Tidewater ist später
   externer Transfer-Test, kein Training und keine Auswahl von Modell oder Parametern.
2. Der Controller erhält nur RGB, eigene Telemetrie, eigene Encoder, Kalibrierung
   und ausdrücklich deklarierte statische Priors. Keine dynamische Bootposition,
   Simulator-Objekt-ID, Segmentierung, Orakelaktion oder Boot-Radio als Task-Eingabe.
3. Simulator-Wahrheit darf der isolierte Annotator/Prüfer für Labels und Auswertung
   nutzen. Annotationsergebnisse werden nicht an den Controller zurückgegeben.
4. Ein Suchziel ist physisch und optisch normal in der Welt vorhanden. Nur die
   anfängliche Kamerablickrichtung liegt daneben. Nicht `--target-absent`, Rendergruppen,
   Alpha, Masken, Blackout, Blind-Zeit oder Entfernen des Bootes verwenden.
5. E12 ohne Ziel mit Heimkehr entfällt. Keine neue `return_home`-/`land_home`-Episode
   rendern oder trainieren. Historische E12-Dateien bleiben unverändert erhalten.
6. Die echte native Physik, Kollisionsauswertung, physische Aufsetzbedingungen und
   PX4-Disarm-Bedingungen bleiben gleich. Keine Erfolgsbedingungen lockern.
7. Das System bleibt hybrid: gelernte Wahrnehmung, geometrische Registrierung,
   explizite Steuerung und PX4. Den alten `landing_training/train.py`-Aktions-GRU
   nicht als Ersatz trainieren. Explizite Steuerung lernt keine Manöver aus Aktionsvektoren.
8. Originale 1.200 Episoden, ihre Freigaben/Splits, V31-Quellen, alte Fehlversuche,
   alte Quarantäne und evaluierte Quellen nie überschreiben. Neue abgeleitete
   Daten, Quellen und Modelle erhalten neue Pfade und explizite Herkunft.
9. Die Freigabe der V31-Demos hebt die alte Quarantäne von 59 buggy Aufnahmen und
   ihren abgeleiteten Trainingsdaten/Checkpoints nicht auf. Insbesondere keine
   V23-/V24-Fehlerdaten, alten Caches oder verworfenen Gewichte still wiederverwenden.
10. Der geprüfte V31-Recognizer als initialer, separat zugelassener Modellzustand
    hat SHA256 `c87dca7541d361b183ce45da5f7756bdc5a358aaf544fb2bc5c3fc08bad1e0e3`.
    Das erlaubt nicht automatisch das Wiederverwenden seines alten Trainingsdatensatzes.
    Sein alter 80%-Cold-Static-Test bleibt als **nicht bestanden** dokumentiert.
11. Rohaufnahmen aus dem neuen Producer bleiben `training_eligible=False`. Nicht
    Attribute umschreiben. Nur ein separater, geprüfter Derivativ-Manifest-Consumer
    darf die ausdrücklich zugelassenen neuen Labels nutzen.
12. Kein alter globaler Quarantäne-Guard wird entfernt, deaktiviert oder mit einem
    gefälschten Review umgangen. Neuer Trainingscode prüft seinen neuen, engen
    Vertrag und muss alte gesperrte Daten im Negativtest weiterhin ablehnen.
13. Störung, Safety-Override, tatsächliche Aktion, Schatten-Expertenvorschlag und
    tatsächlicher Experte sind verschiedene Quellen. Niemals umetikettieren.
14. Acht Worker, wenn ausreichend Ressourcen vorhanden sind. Mindestens 4 GiB
    RAM und 1 GiB VRAM frei halten; Startwachstum bereits gestarteter Worker
    berücksichtigen. Keine erneute 4/8/12-Worker-Suche und kein erzwungenes OOM.
15. Keine VM-Verlängerung, kein Kauf, keine neue VM. Keine unqualifizierte Policy
    in die Windows-/Tidewater-Produktion kopieren. Experimentelle lokale Sicherung
    bedeutet nicht Deployment oder Qualifikation.

## 2. Uhrzeit, Budget und Abbruchzeitpunkte

Ursprung ist die Nutzerangabe vom 20.10.2026 gegen 00:33 Europe/Berlin:
17 Stunden verbleibende VM-Zeit. Das ist keine vom Provider verifizierte Abschaltung.
Alle folgenden Grenzen werden vorsorglich davon abgeleitet; sie wandern nicht
mit jeder Fortsetzung nach hinten.

| Zeitpunkt am 20.10.2026 | UTC | Europe/Berlin | Bedeutung |
|---|---|---|---|
| Normales Ende Zweck-/Masken-Vorbereitung | 00:33 | 02:33 | Höchstens 2h ab ursprünglichem Beginn |
| Normales Ende neuer Sammlung | 05:33 | 07:33 | Maximal 5h tatsächliche Sammlung |
| Normales Ende Training/Modellauswahl | 07:33 | 09:33 | 1–2h Cache/Training/Validierung |
| Normales Ende Benchmarks | 11:33 | 13:33 | 3–4h native Paarvergleiche + begrenzter Transfer |
| Ziel für vollständige lokale Lieferung | 13:33 | 15:33 | Einschließlich Export-/Reparaturreserve |
| Letzter geplanter kompletter Notexport | 15:15 | 17:15 | Nicht auf VM-Abschaltung warten |
| Keine weiteren VM-Arbeiten außer laufendem Export | 15:20 | 17:20 | Eigene lange Prozesse sicher beenden |
| Abschlussbericht spätestens | 15:25 | 17:25 | Tatsächlichen Stand und Lücken nennen |
| Backup-Watcher endet | 15:30 | 17:30 | Letzte Chance ist kein primäres Sicherungskonzept |
| Nutzerseitig angenommene VM-Grenze | 15:33 | 17:33 | Harte Planungsobergrenze |

Die normale obere Summe ist 15h; die äußeren 17h enthalten weitere 2h Reserve.
Masken-/Metadatenarbeit darf CPU-/I/O-schonend während der Sammlung laufen.
GPU-Training nicht unkontrolliert zusätzlich zu acht Renderworkern starten.

An jedem Phasenwechsel:

1. Aktuelle UTC ermitteln, mit obiger Tabelle vergleichen.
2. Verbleibende Zeit für noch notwendige Phasen einschließlich Sicherung reservieren.
3. Bei Verzug zuerst weitere Datensammlung reduzieren. Keine Tests, Hash-Prüfung
   oder Sicherung streichen, um eine runde Episodenzahl zu erreichen.
4. Bei nicht bestandenem technischen Gate nicht aus Zeitdruck trotzdem trainieren.
5. Bei früherer VM-Abschaltung vorhandene lokale Pakete und letzten gültigen Stand
   liefern. Keine Wiederherstellung auf einer kostenpflichtigen neuen VM veranlassen.

Durchsatzbasis: Der letzte komplette Lauf lieferte 20.027 Kamerazeilen in
2.310,12 Wandsekunden = 8,669 Zeilen/s insgesamt für die parallel laufende
Pipeline. Nicht nochmals mit acht multiplizieren. 47fps ist für diese vollständige
Pipeline nicht gemessen. Grobe Rechnung:64 Episoden ×80 Task-Sekunden ×25Hz
=128.000 Kamerazeilen; bei 8,669/s etwa4,1h. Längere Such-/Recovery-Flüge und
abgelehnte Aufnahmen reduzieren die innerhalb der 5h lieferbare Menge.

## 3. Protokoll, Freigaben und Zustandsmaschine

`EXECUTION_STATE.json` ist der lokale Wiedereinstiegspunkt. Jede abgeschlossene
Phase verweist auf einen eigenen Receipt mit Eingangs-/Ausgangs-Hashes, Uhrzeiten,
konkreten Ergebnissen und Fehlern. JSON atomar schreiben: temporäre Datei schreiben,
dann umbenennen. Keine halbfertige Datei als abgeschlossenen Receipt verwenden.

Zulässige Reihenfolge:

```text
AWAITING_PLAN_APPROVAL
  -> PREFLIGHT
  -> PILOT_AUDIT
  -> WORLD_AND_DATA_CONTRACTS
  -> COLLECTION_AND_MASKS
  -> DATA_ADMISSION
  -> TRAINING_AND_VALIDATION
  -> CANDIDATE_FREEZE
  -> NATIVE_PAIRED_EVALUATION
  -> EXTERNAL_TRANSFER
  -> VERIFIED_EXPORT
  -> REPORTED
```

Seiteneinstiege sind nur BACKUP/READ_ONLY_DIAGNOSIS/SAFE_CLEANUP. Sie geben die
nächste Phase nicht frei. Eine fehlgeschlagene Phase bekommt `failed` mit Ursache;
`passed` wird nur aus tatsächlich vorhandenen, geprüften Nachweisen gesetzt.

**Ausnahmeausgang statt Sackgasse:** Bei nicht rechtzeitig reparierbarem Gate-Fehler,
Budgetende oder VM-Ausfall darf jede Phase direkt zu VERIFIED_EXPORT/REPORTED
wechseln. Das ist eine Sicherung/Teillieferung, kein Bestehen der ausgelassenen
Phasen. Ihre Zustände bleiben `failed`, `not_run` oder `skipped_with_reason`.
Fehlendes Training benötigt keinen erfundenen neuen Checkpoint:die letzte wirklich
existierende Basis/Resume-Datei sichern. Ein fehlender nativer Test darf nicht die
Sicherung bis zur VM-Abschaltung blockieren. Ein entfallener Tidewater-Test erhält
einen `not_run`-Bericht mit Ursache, niemals einen erfundenen Erfolg.

Eine Korrektur erhält einen neuen Quellenpfad/eine neue Revision. Bereits laufende
oder evaluierte Quellen nicht ändern. Die neue Revision muss die betroffenen Gates
erneut bestehen; unveränderte bereits bewiesene Voraussetzungen nicht teuer wiederholen.

### 3.1 Verbindliches Receipt-Schema

Jeder Gate-Receipt enthält mindestens:

```json
{
  "schema": "approved.curriculum.gate.v1",
  "gate_id": "eindeutige Kennung",
  "status": "passed oder failed",
  "started_utc": "ISO-8601",
  "finished_utc": "ISO-8601",
  "input_files": {"relativer/Pfad": "sha256"},
  "output_files": {"relativer/Pfad": "sha256"},
  "checks": [{"name": "konkrete Prüfung", "passed": true, "evidence": "Datei plus Zeilen-/Framebezug"}],
  "known_limits": [],
  "training_eligibility_granted": false
}
```

Das Schema ist eine Vorlage, keine vorab erteilte Freigabe. Werte nie aus diesem
Beispiel übernehmen. Datenzulassung wird ausschließlich im dafür vorgesehenen
Datenmanifest explizit und komponentenspezifisch gewährt.

## 4. Phase A — Startkontrolle und unabhängige Sicherung

**Eingang:** tatsächliche Planfreigabe, aktueller Zustand, bestehende Backup-Dateien.

1. `whoami` und `hostname` über strenges SSH abfragen. Bei Abweichung keine
   schreibenden Aktionen auf dem fremden System durchführen.
2. Eigene aktuelle Prozesse mit vollständiger Kommandozeile und Startzeit lesen.
   Letzte Dateien/Logs von `semantic_pilots` lesen. Kein zweites Pilot-Launch starten.
3. Unter Windows die PID aus `backup_watcher.pid` mit existierendem Prozess,
   Kommandozeile und Startzeit abgleichen. Eine zufällig wiedervergebene PID ist
   kein Beleg. `backup_watcher_state.json`, `.log`, `.err` und letzten Receipt lesen.
4. `status=watching` und frische Check-Zeit prüfen. Bei unverändertem Modell darf
   die Snapshot-Erstellzeit älter sein; die letzte Prüfuhrzeit muss aktuell bleiben.
5. Mindestens ein lokales ZIP plus `.verified.json` und `LATEST_VERIFIED.json`
   müssen existieren. ZIP öffnen und alle Member-Hashes anhand
   `BACKUP_MANIFEST.json` kontrollieren. Das bloße Existieren eines ZIP genügt nicht.
6. Bei tatsächlich abgestorbenem Watcher genau einen Nachfolger mit
   `Start-Process -WindowStyle Hidden` starten. Den vorhandenen lebenden Watcher
   nicht duplizieren. Seine Deadline bleibt `2026-10-20T15:30:00+00:00`.
7. Bei einem Backup-Fehler zunächst die konkrete Fehlermeldung reparieren. Ein
   funktionierender unabhängiger lokaler Backup-Pfad ist vor neuem Training Pflicht.
8. Freien lokalen Speicher prüfen. Keine Rohdaten von hunderten GB herunterladen.
   Bei knappem Platz neue Snapshot-Größe begrenzen; vorhandene einzige gültige
   Sicherung nie löschen. Alte Rohaufnahmen auf der VM nicht für Platzgewinn löschen.

Vorhandener lokaler Einmallauf, nur wenn der Watcher nicht gleichzeitig in einem
Snapshot/Download steckt:

```powershell
python artifacts/approved_curriculum_20261020/backup_watcher.py --once
```

Der periodische Watcher prüft alle fünf Minuten. Im geplanten Training best/latest
mit atomarer Dateiersetzung speichern, nicht direkt in eine veröffentlichte Datei
schreiben. Gleichzeitige Snapshot-Erzeuger/Downloads müssen vor häufiger Nutzung
von Einmalläufen durch einen gemeinsamen Prozess-/Dateilock serialisiert werden;
bis dahin keine konkurrierenden Einmalläufe starten. Dieses fehlende Lock ist ein
expliziter kleiner Implementierungspunkt, kein bereits bewiesenes Backup-Merkmal.

**Ausgang A:** `preflight_receipt.json` mit Identität, freien Ressourcen,
aktiven eigenen Prozessen und lokal verifizierter Sicherung. Kein Training starten,
wenn die letzte neue Policy nicht zuverlässig zum Laptop gelangen kann.

## 5. Phase B — Acht bestehende Zweck-Prüfflüge schließen und auswerten

**Existierende VM-Pfade:** `semantic_pilots/state.json`, `plan.json`,
`<Name>.log`, `<Name>/initial_view_receipt.json`, `semantic_camera_trace.jsonl`,
`capture_annotations.jsonl`, `steps.jsonl`, `observations.h5`, `summary.json`,
`preview_result.json`, `source_receipt.json`, `native_hook_bindings.json`.

Die erste Aufgabe ist Lesen, nicht Neustart. Der aktuelle Coordinator wurde unter
PID612154 gestartet; diese PID ist nur Historie und muss aktuell geprüft werden.
Die acht Namen sind `visible_start`, `search_near`, `search_mid`, `search_far`,
`search_distractors`, `yaw_resync`, `tilt_loss`, `learner_struggle`.

### 5.1 Erstbild-Gate

1. Rohaufnahme schließen lassen. Unvollständiges H5 nicht als fertiges Training lesen.
2. Den ersten **gültigen gelieferten** RGB-Frame anhand von Capture-Zeit und SHA
   exakt zu seiner Annotation verbinden. Keine Nächstzeitpunkt-Ersetzung.
3. `initial_view_receipt` mit diesem gelieferten Frame abgleichen. Die aktuelle
   Producer-Prüfung läuft beim ersten Capture; der separate Abgleich zur ersten
   Lieferung ist zusätzlich erforderlich, insbesondere bei Bildverzögerung.
4. Suchfälle:0 Zielboot-Pixel im ersten gelieferten Bild; Zielgeometrie vorhanden,
   normale Rendergruppen/Alpha; keine Blind-Zeit oder Bildmaskierung.
5. Sichtbarer Start:mehr als0 Zielboot-Pixel, korrektes physisches Ziel, nicht bloß
   ein fremdes Boot mit kopiertem Kreuz.
6. Eigene Kameramatrix/Encoder/Attitude und RGB müssen zusammenpassen. Keine
   Objekt-Labelinformation an Controller oder Aufgabenentscheidung weiterreichen.
7. Tatsächliche horizontale Startdistanz aus dem isolierten Beobachter muss im
   deklarierten Band liegen. `scenario.distance=52` allein ist kein Beweis für52m.

Die ersten Capture-Nachweise existierten beim Schreiben bereits für Suchstarts
um8,20,28 und52m mit0 Zielpixeln. Dies ist **kein** Nachweis einer erfolgreichen
Suche, Entdeckung oder Landung.

### 5.2 Zweck-Gate pro Aufgabenklasse

| Fall | Muss als tatsächlicher Ablauf nachweisbar sein | Nicht ausreichend |
|---|---|---|
| E01 ruhig/nominal | Tatsächlicher Anflug, gültige geometrische Ausrichtung, physischer Touchdown/Disarm | Nur schöner Einzel-Frame |
| E02 Ablenkungen | Fremde Objekte/Glare tatsächlich im Kameraverlauf; richtige Zielauswahl; kein fremdes metrisches Ziel/keine fremde Landung | Dekoy irgendwo unsichtbar in der Welt |
| E03 Pan-Störung | Tatsächlich ausgeführte Pan-Befehle mit Störungsbesitz, Encoder-/RGB-Reaktion, anschließende Synchronisierung | Nur Fault-Konfiguration; behaupteter Verlust ohne Verlust |
| E04 + E04a | Tatsächlicher Marker-/Geometrieverlust, angehaltener Sinkflug, zulässige Recovery, Reakquisition, Landung; E04a gleiche Aufzeichnung | Bloße Kameradrehung ohne Sichtverlust |
| E05 sichtbares Ziel | Ziel im ersten Bild, reale Sichtung wird behalten/untersucht statt grundlos übersprungen | Ein Suchfall, der erst später zufällig das Boot sieht |
| E06 Suche nah | Erstbild ohne Ziel; tatsächliche Blickänderung; spätere Sichtung, Untersuchung, Ziel-Landung;5–20m Start | Boot schon im Erstbild oder direkt am Bildrand beim ersten Minischritt |
| E07 Suche mittel | Gleiche Kriterien; tatsächlicher Start20–40m | Nur andere Episodenbezeichnung bei8m |
| E08 Suche fern | Gleiche Kriterien; tatsächlicher Start40–60m; zunehmende erkennbare Bildinformation beim Annähern | Annehmen, das Boot sei auf60m stets erkennbar |
| E09 Terminal | Unterstütztes Aufsetzen/Disarm; keine unnötige neue Expertenübernahme nach Kontakt | Falsche Rettung nach bereits sicherem Touchdown |
| E10/E11 Rettung | Tatsächlicher learner-besessener schwieriger Zustand; danach gelatchte Expertenkontrolle; tatsächliche Korrektur/Recovery; aktive und abgelaufene Memory-Pfade getrennt prüfen | Präventive Übernahme nach winzigem Startfehler, selbständig fortschreitende Learner-Recovery, Lehrer-only-Demo oder Teleport |
| E12 alt | Explizit ausgeschlossen, keine neue Aufnahme | Home-Landung als Bootserfolg zählen |

Suchentdeckung zusätzlich:mindestens20° nützliche Änderung des tatsächlichen
Kamerabearings zwischen erster Ansicht und erster Zielsichtung, horizontaler
Blickstrahlanteil mindestens0,2. Das ist das bereits implementierte
Szenario-Zweck-Gate, kein neues Steuerungsziel. Original-E06 mit6.131 Zielpixeln
im Erstbild muss der Regressionstest ablehnen. Keine künstliche Wartezeit vor
bereits klar erkannter Zielaufnahme einführen, um den Prüfer zufriedenzustellen.

Für Fault- und Rescue-Labels müssen die Messwerte im **Prüfer aus echten Zeilen**
berechnet werden, inklusive Frame-/Capture-IDs. Die derzeitige Funktion
`semantic_contract.purpose` akzeptiert entsprechende Messfelder; das allein
beweist noch keinen Ablauf. Niemand darf `measured_metric_loss_frames` oder
`measured_struggle_before_takeover` von Hand in einen Vertrag eintragen, um einen
Test zu bestehen. Der neue vollständige Auditor muss diese Lücke schließen.

### 5.3 Physik-, Ownership- und Bild-Gate

1. Source-Hashes gegen eingefrorenes Producer-/Actor-Paket prüfen.
2. Native tatsächliche Globals prüfen:beabsichtigter Renderer, NoRadio,
   Supervisor, PX4-Wrapper und Capture-Hook nach Effekten vor Verzögerungsqueue.
3. Für jede gültige Lieferung RGB-SHA und Capture-Zeit exakt verbinden.
   Wiederholte verzögerte Frames sind dieselbe Aufnahme und keine neue Stimme.
4. `executed_action[t]` und `previous_executed_action[t+1]` prüfen.
5. Tatsächlichen Besitzer jeder Aktion aus ausgeführtem Pfad prüfen.
6. Fehlende frische Geometrie darf kein unzulässiges Sinken erzeugen. Native
   Terminal-Commit-Regeln unverändert interpretieren, nicht pauschal deaktivieren.
7. Falsches Boot, Wasser, Kollision, Label-/Source-/History-Bruch sind Fehler,
   keine Datenpunkte, die man bloß als normale erfolgreiche Demonstration behält.
8. Konfigurierter Fault ohne ausgeführte Zeilen = fehlende Abdeckung.
9. Bei Mission-Fallback muss Collection vor Home-Rückkehr mit Null-Hold abbrechen.
   Stop-Zeile und alles Home-/Return-bezogene ausschließen. Abbruch ist kein Erfolg.
10. Tatsächliche RGB-Sequenz um Erstbild, Entdeckung, Störung, Verlust,
    Reakquisition und Terminal prüfen. Keine kosmetische Stabilisierung oder
    Rekonstruktion verwenden. Für interne Sichtung keine langen Videos rendern.

**Ausgang B:** je Pilot `purpose_audit.json` und gemeinsamer
`pilot_gate_receipt.json`. Validierte Piloten dürfen nur dann zur späteren
Menge zählen, wenn zusätzlich Rollen/Splits und Datenzulassung passen. Sie sind
bekannte Entwicklungswelten, niemals unabhängige Benchmarkfälle.

## 6. Phase C — Welten, Quellen, Splits und Datensatzvertrag einfrieren

Diese Phase benötigt Implementierung. Keine breite Sammlung starten, bevor sie
einen bestandenen Gate-Receipt hat.

### 6.1 Quellen und Szenencaches

1. Reviewed V31-Actor und Basisgewichte zunächst unverändert übernehmen. Jede
   erforderliche tatsächliche Korrektur in neuer Revision isolieren und nur die
   betroffenen Funktions-/RGB-/Fluggates erneut absolvieren.
2. Alle geladenen Module mit absoluten `__file__`-Pfaden und Hashes protokollieren.
   Python-Importreihenfolge prüfen; `landing_training.paths` vor `usv`-Importen.
3. V31 lädt feste basic/hard-Szenencaches. Diese sind nur bekannte Entwicklungs-
   Szenen. Das Setzen von `Scenario.kind='rock'` darf nicht als tatsächliches
   physisches Rock-Terrain ausgegeben werden, wenn ein Beach-Modell geladen ist.
4. Passende Szenencaches für die vorgesehenen Welt-/Map-Seeds erzeugen oder
   nachweislich passende vorhandene Caches verwenden. Echte Weltgeometrie,
   statische Küstenabfragen, Kollisionsgeometrie und Navigationswelt müssen dieselbe
   Karte/Rotation/Seed beschreiben. Nicht nur eine Textur oder Metadaten ändern.
5. Je Cache Modell-/XML-/Welt-/Routen-Hashes speichern. Target- und Drohnen-CAD,
   Massen, Trägheiten, Antriebe, Kollisionskomponenten und Solver-/Physikoptionen
   gegen die Basis vergleichen. Die alte981-Komponenten-Prüfung deckte nur ihre
   zwei damaligen Modelle ab; sie ist keine universelle neue Freigabe.
6. Sichere Spawn-/Korridorprüfung mit statischen Priors durchführen. Gegenstände
   dürfen nicht überlappen oder in Zielroute/Startbereich spawnen. Die spätere
   Steuerung erhält keine dieser dynamischen Objektkoordinaten.
7. Falls ein Terrain-Korridor nicht zertifiziert werden kann:Fall als nicht
   ausführbar ausweisen. Wasser-/Geländeschutz nicht blind entfernen. Keine neue
   Overland-Fähigkeit behaupten, die im beschränkten Budget nicht nachgewiesen ist.
8. Erstbild-/Distanz-/Zweck-Prüfer bleibt für jede zufällige Episode aktiv.

### 6.2 Rollen und Seeds

1. Alle Original- und bisherigen Plan-/Szenario-Seeds inventarisieren. Alte
   zurückgezogene Tests bleiben Test-/Diagnosegeschichte und werden keine Trainingsdaten.
2. Trainings-, Validierungs- und spätere unabhängige Evaluationswelten vor der
   Generierung fest zuordnen. `world_seed` darf nie rollenübergreifend vorkommen.
   Auch pfad-/familien-/trajectory-bezogene Ableitungen dürfen keine verdeckte Leckage bilden.
3. Exponierte Pilotwelten höchstens als Trainings-/Entwicklungsquelle verwenden,
   niemals später als frisch/unbekannt ausgeben.
4. Beide Datenrollen sollen alle fünf vorgesehenen Map-Familien enthalten.
   Die Szenencaches müssen die tatsächliche Karte belegen. Keine fünf-Map-
   Abdeckung aus zwei Karten behaupten.
5. Exakte Szenario-/Welt-/Rollenliste in `collection/plan.json` speichern und hashen.
   Jede Episode verweist auf diesen Hash. Änderungen erzeugen eine neue Planrevision,
   keine stille Mutation des laufenden Plans.

### 6.3 Detaillierung der bestehenden64-Episoden-Zielmenge

Die folgende Arbeitsaufteilung konkretisiert die bereits vorgesehenen Aufgaben,
ohne die Gesamtmenge oder48/16-Aufteilung zu verändern:

| Aufgabenfamilie | Training | Validierung | Zusammen |
|---|---:|---:|---:|
| E01 nominal/ruhig | 6 | 2 | 8 |
| E02 Ablenkungen/Glare/andere Boote | 6 | 2 | 8 |
| E03 Pan-Synchronisierung | 3 | 1 | 4 |
| E04 echter Nahbereichsverlust | 3 | 1 | 4 |
| E05 sichtbares Erstbild | 3 | 1 | 4 |
| E06 Suche5–20m | 6 | 2 | 8 |
| E07 Suche20–40m | 6 | 2 | 8 |
| E08 Suche40–60m | 6 | 2 | 8 |
| E09 unterstütztes Terminal | 3 | 1 | 4 |
| E10 tatsächliche Learner-/Expertenrettung | 3 | 1 | 4 |
| E11 Rettung/Memory-Pfad | 3 | 1 | 4 |
| **Gesamt** | **48** | **16** | **64** |

Dies sind Zielmengen gültiger Episoden, keine Behauptung, dass solche Daten bereits
existieren. Wenn eine Familie innerhalb des Budgets nicht qualifiziert werden kann,
ihre Lücke ausweisen. Nicht vier weitere Nominalflüge als vier Rettungen umbenennen.
Keine Rückkehr-/Heimlandungsdaten zum Auffüllen verwenden.

Parameterstreuung bleibt im geprüften Rahmen:Boote normal vorhanden, variable
Startblickrichtung/Entfernung, fünf Map-Familien, ursprüngliche korrekt artikulierte
Zielgeometrie, fremde Boote/Objekte, physikalisch kohärenter Glare, erlaubtes Licht,
Wetter, Bewegung und Wellen. Keine neue unvalidierte Extremphysik einführen.

**Ausgang C:** `collection/plan.json`, `collection/source_snapshot/`,
`collection/world_role_index.json`, `collection/environment_receipts/`,
`collection/data_contract.json`, `world_and_data_gate.json`.

## 7. Phase D — Alte Daten ableiten und neue Daten sammeln

### 7.1 Originaldaten:Versionierte Masken statt Neurendern

1. Originalmanifest und dessen Review-Verbindung prüfen. Verifizierter Bestand:
   960 Training,120 Validierung,120 Test. Alte Test-RGB nicht für Maskenschwellen,
   Training oder Hyperparameter lesen. Split-Mitgliedschaft bleibt erhalten.
2. Die vorhandene12-Episoden-Probe ist nur Metadaten-/Kostenprobe. Nicht daraus
   einen globalen gültigen Anteil oder eine Qualitätsfreigabe ableiten.
3. Neue Masken unter `original_masks/<revision>/` erzeugen. Dateien enthalten
   Originalpfad, deklarierte und tatsächlich verifizierte Quellhashes, Frame-Index,
   Schema, Gründe und komponentenspezifische boolesche Loss-Masken.
4. Original-H5 nie ändern, Frames nie physisch entfernen. Reihenfolge und
   tatsächliche Aktion-/Störungshistorie bleiben für Sequenzen erhalten.
5. Pro Episode in einem Durchgang Metadaten lesen und nötige Quellhashprüfung
   durchführen. Große Originaldateien nicht wiederholt für jeden Kopf hashen.
   I/O-Parallelität begrenzen, damit acht laufende Simulatoren nicht ausgebremst werden.
6. Keine Bild-Neurenderung, keine Kamera allein nachträglich drehen und dann die
   alten Aktionen als passende Labels ausgeben. Ein korrigierter physischer Verlauf
   wäre eine neue Simulation, keine Bildbearbeitung.

Maskenregeln:

| Label/Kopf | Behalten nur wenn | Ausschließen wenn |
|---|---|---|
| Irgendein Trainingsziel | Quelle, Rolle, Capture und Label gültig | Home/Return-Segment, Stop-Hold, verbotene Quelle, inkonsistenter Verlauf |
| Expertenaktion, falls später ein tatsächlich eingesetzter Consumer existiert | Echter beobachtbarer Expertenvorschlag, zulässige Korrektur, richtiger Besitzer | Fault/Safety/Learner ausgeführt, Null-Platzhalter, problemverursachende Kameraaktion, nicht aus RGB/eigenem Zustand ableitbare Orakelaktion |
| Boot-Design | Verifizierte sichtbare Struktur/kontextgerechte Identität | Kalter reiner Marker-Crop, unklare Identität, unvalidierte reduzierte Klon-Geometrie |
| Marker/Pixelpose | Tatsächlich sichtbare, korrekt capture-gebundene Markerinformation | Marker nicht sichtbar, Projektion/Timing inkonsistent oder uneindeutige Symmetrie |
| Perzeptionsbild unter Störung | Label bleibt im tatsächlichen Bild korrekt und beobachtbar | Nicht allein aufgrund eines schlechten Kommandos verwerfen oder allein aufgrund von Simulator-Wahrheit akzeptieren |

Das Originalboot ohne sichtbaren Marker bleibt dasselbe Design. Ein anderes Boot
mit kopiertem Kreuz bleibt ein anderes Design. Symmetrische Cross-Ansichten dürfen
keine eindeutige unbeobachtbare180°-Yaw-Zielvorgabe erhalten.

Die alte Aufzeichnung enthält möglicherweise nur Pad-Labels und keine valide
Whole-Boat-Bounding-Box. Keine Whole-Boat-Identität durch frei erfundene Crop-/Box-
Labels erzeugen. Für diesen Kopf nur belegte Quellen nutzen; bei fehlendem Nachweis
Kopf maskieren und die Zahl fehlender Labels berichten. Bestehende Pose-Labels dürfen
separat nutzbar sein. Diese Auswahl muss der tatsächliche Consumer berücksichtigen.

Kamerasynchronisierung anhand tatsächlicher Kamera-/Encoder-/Pose-Verläufe prüfen.
Keine beliebige kosmetische Winkelgrenze erfinden, um möglichst viele Frames zu
behalten. Vor Verwendung eine feste, begründete Spezifikation und Regressionen
gegen bekannte Fehl- und Korrekturabschnitte schreiben. Wenn das im Budget nicht
belegbar ist, fragliche Aktionslabels nicht verwenden. Aktionsimitation ist ohnehin
nicht der neue aktuelle Hybrid-Trainingsauftrag.

### 7.2 Neue Sammlung mit acht Workern

1. Producer und Plan vor Launch hashen; Ausgabeverzeichnis muss neu sein.
2. Vor jedem Start RAM/VRAM inklusive Startwachstum laufender Worker prüfen.
3. Acht Slots füllen; frei gewordene Slots zeitnah aus der festen Warteschlange
   nachfüllen. Nicht auf den langsamsten Worker warten, um eine ganze Runde neu zu starten.
4. Für Sammlung `--omit-overview` benutzen. Tatsächliche640×360-Onboard-RGB,
   Capture-Annotationen, Schritte und Physik/Ownership bleiben erhalten.
5. Bei Mission-Fallback Diagnoseabbruch vor Home-Kommandos. Ein Fehler darf nicht
   erst einen vollständigen nutzlosen Heimflug rendern.
6. Zweck- und Datenprüfer bearbeiten nur geschlossene Dateien. Dateischluss und
   Abschluss-Receipt müssen tatsächliche Schließung belegen.
7. Erfolg zählt erst nach Zweck-, Source-, Ownership-, Capture- und Physik-Gate.
8. Bei Kollision/Wasser/falschem Boot/Source-Leak/Labelbruch neue Starts sofort
   stoppen, laufende betroffene Jobs sicher bereinigen und Ursache analysieren.
   Bei einem einzelnen logischen Zweckfehler weitere Sammlung dieser Klasse stoppen;
   andere bereits gestartete unabhängige Diagnosefälle dürfen ihre Beweise schließen.
9. Für jede Ablehnung Ursache und Kosten speichern. Nicht still löschen und
   nicht als erfolgreichen Trainingsfall zählen.
10. Tatsächlichen Gesamtdurchsatz der laufenden Pipeline protokollieren. Nicht
    Worker-Wandzeiten aufsummieren und gleichzeitig mit Gesamtdurchsatz rechnen.
11. Nach erstem abgeschlossenen Batch verbleibende Menge/Zeit anhand gemessener
    Dauer prognostizieren. Kein neuer Worker-Count-Benchmark.
12. Nach5h Sammlung oder dem absoluten Cutoff keine weitere Sammlung starten.
    Vor langer letzter Episode Export-/Trainingsreserve prüfen. Tatsächlich
    erreichte gültige Menge nennen, auch wenn sie unter64 liegt.

**Ausgang D:** geschlossene neue Rohaufnahmen plus geprüfte Zweck-Receipts,
Maskenmanifest mit Behalten-/Ablehnen-Zahlen nach Phase/Map/Kopf und tatsächlichen
Kosten. Roh-Eligibility bleibt unverändert false.

## 8. Phase E — Datenzulassung und tatsächlichen Trainingsconsumer prüfen

1. Neuen Consumer ausdrücklich auf neuen Derivativ-Manifest-Schema-Namen begrenzen.
   Er darf nicht einfach alle H5-Dateien unter `outputs/` einsammeln.
2. Pro Frame Quelle, Rolle, Welt, Capture-UID/SHA, Labelmaske und Labelprovenienz
   prüfen. Veraltete/reduplizierte Captures nicht mehrfach als unabhängige Evidenz werten.
3. Alte verworfene Review-/V23-/V24-/Retired-/Test-Quellen im Negativtest einspeisen;
   der Consumer muss sie ablehnen. Alte Quarantänedatei bleibt existent/unverändert.
4. Einen absichtlich falschen Source-Hash, falsche Rolle, falsche Capture-Zeit,
   Home-Zeile und Null-Platzhalter-Aktionsquelle einspeisen:alle müssen abgelehnt
   oder beim exakt richtigen Kopf mit belegtem Grund maskiert werden.
5. Echte Trainings-Mini-Batches laden. Nachweisen, dass Masken den Loss tatsächlich
   steuern. Maskierte Targets verändern den Loss/Gradienten nicht; gültige
   Korrektur-/Wahrnehmungslabels verändern ihn. Kein bloßer Dateierstellungs-Test.
6. Vortrainierte unveränderte Encoder/Detektoren nur aus den zugelassenen
   Modellquellen initialisieren. Nicht alte gesperrte Daten-Caches importieren,
   nur weil ihr Dateiname `original` oder `validation` enthält.
7. Für Whole-Boat-Design und Marker den tatsächlich eingesetzten RGB-Crop-/Input-
   Pfad verwenden. Exaktes640×360-Eingangsbild; aktuelle Crop-Geometrie/96×96-
   Verifier-Auflösung nicht versehentlich durch privilegierte perfekte Val-Crops ersetzen.
8. Training darf nachvollziehbare Augmentationen/Train-Box-Jitter verwenden;
   Validierung misst deployed Vorschläge, keine GT-Rettung der Vorschläge.
9. Identität, Marker-Sichtbarkeit, metrische Geometrie und Landebereitschaft bleiben
   getrennte Aufgaben. Kein fehlendes Pad als falsche Bootidentität labeln.
10. Datencache-/Feature-Hashes und Split-Zuordnung einfrieren. Mit altem,
    zugelassenem Modell auf genau dieser Validierung vor jedem Fine-Tuning messen.

**Ausgang E:** `admission/manifest.json`, `admission/rejections.json`,
`admission/source_index.json`, `consumer_validation_receipt.json`,
`model_training/baseline_validation.json`. Keine Freigabe ohne echte Consumer-Prüfung.

## 9. Phase F — Anwendbare Wahrnehmung trainieren und separat speichern

1. Vor Start erneut Backup und Zeitreserve prüfen. Nicht auf einem Dataset starten,
   dessen Gate nur deshalb grün ist, weil Assertions deaktiviert wurden.
2. Detaillierte Modellkonfiguration einfrieren:Architektur, Vortrainingshashes,
   trainierbare Köpfe, Loss-Gewichte, Rollen, Maskenschemata, Seed, Optimizer,
   Batchgrößen, Validierungsintervall und Early-Stopping-Regel.
3. Warmstart und exakte Optimizer-Fortsetzung unterscheiden. Keine exakte Fortsetzung
   behaupten, wenn AdamW neu gestartet wird. Diese Metadaten in den Checkpoint schreiben.
4. Bestehenden pose-/spatial-/Physikzustand beibehalten, sofern kein konkret
   nachgewiesener, zugelassener Anpassungsbedarf besteht. Nicht automatisch alle
   Gewichte trainierbar schalten, um länger zu trainieren.
5. Der aktive Hybrid muss die neuen Wahrnehmungsgewichte tatsächlich laden.
   Einen unveränderten R15-Learner mit neuem Dateinamen nicht als neue Policy evaluieren.
6. Alte und neue zulässige Trainingsquellen mischen; neue Recovery-Frames dürfen
   ruhige Nominalausrichtung nicht verdrängen. Mengen/Gewichte ausdrücklich speichern.
7. Nach kurzer echter Cache-/Trainingsprobe Zeit für verbleibende Epochen messen.
   1–2h ist Budget für Cache, Fine-Tuning und Validierung, nicht die Aufforderung,
   die GPU künstlich2h laufen zu lassen. Wenn das kleine Modell früher fertig ist,
   sofort sinnvoll weitergehen.
8. Keine blinden Epochenverlängerungen. Bei Stagnation nach vorab festgelegter
   Patience stoppen. Nicht auf Testdaten nachjustieren.
9. `latest.pt` und `best.pt` atomar speichern. Mindestens Modellzustand,
   Optimizerzustand, Epoche/Schritt, Zufallszustände, Normalisierung/Kalibrierung,
   Training-/Source-/Manifest-Hashes, Validierung und erforderliche Konfiguration
   für eine ehrliche Fortsetzung beilegen.
10. Nach neuem best/latest unabhängige lokale Sicherung kontrollieren. Im ZIP
     muss genau der neue Checkpoint-Hash vorhanden sein. Ein aktualisierter Receipt
     mit weiterhin nur der alten Basis ist keine Sicherung des trainierten Modells.
11. Auswahl ausschließlich aus vorab erklärter Validierungsregel:mehr echte
     Zielerkennung, keine neue falsche Boot-/Glare-/Background-Akzeptanz am festen
     Betriebspunkt, keine Pose-/Markerregression. Konflikte offen melden.
12. Falls keine neue Variante die Validierung verbessert:Basis beibehalten,
     neue Modelle experimentell archivieren, keine Verbesserung behaupten.
13. Alter fehlgeschlagener Cold-Static-Test bleibt gespeichert. Ein neuer
     Val-/Task-Messwert überschreibt nicht die alte Gate-Datei und erteilt keine
     automatische Produktionsfreigabe.

**Ausgang F:** best/latest/History/Optimizer-/Resume-Metadaten, Training-Provenienz,
Vergleich zur vorher gemessenen Validierungsbasis, lokal verifizierter Snapshot.

## 10. Phase G — Kandidatenpaket einfrieren und eigenständig laden

1. Gewählten experimentellen Kandidaten unter
   `candidate_exports/frozen_candidate_<revision>/` exportieren. Code, alle geladenen
   Gewichte, Kalibrierung, statische Priors, Normalisierung, Grenzwerte und Manifest
   gehören zusammen. Kein übersehener Import aus einem veränderlichen VM-Ordner.
2. Transitive Import-/Dateiabhängigkeiten inventarisieren, notwendige Quellen
   paketieren und Bibliotheks-/Python-/Torch-/ONNX-/CUDA-Versionen speichern.
3. Paketmanifest mit Hash für jede Datei erstellen. Ab jetzt Modell-/Steuerungs-
   Quellen dieses Kandidaten nicht mehr bearbeiten.
4. In frischem Prozess ausschließlich aus dem eingefrorenen Paket laden und einen
   bekannten zulässigen RGB-/Telemetry-Probeinput durch den echten Runtime-Pfad
   ausführen. Genau die gewählten Gewichte müssen geladen sein; Input/Output endlich.
5. Gleicher Frame im nativen späteren Runtimepfad, konsistente Historie und
   unveränderte Source-/Physik-/Landebedingungen prüfen. Ein Unit-Test eines
   ungebundenen Helpers ersetzt nicht den tatsächlichen Runtime-Hook.
6. Die lokale ZIP-Sicherung muss das komplette eingefrorene Paket enthalten,
   einschließlich aller neuen Checkpoints und notwendiger Hilfsquellen. Member-
   Hashes gegen Freeze-Manifest vergleichen; CPU-Load/Architekturprüfung soweit
   lokal möglich. Fehlende VM-/GPU-Abhängigkeiten ehrlich im Resume-README nennen.

**Ausgang G:** `candidate_binding.json`, vollständiges Freeze-Paket,
`candidate_runtime_probe.json`, Hash-identisches lokal geprüftes Backup.

## 11. Phase H — Unabhängiger nativer Paarvergleich

Ziel bleibt18 Szenarien ×Basis/Kandidat =36 Testflüge. Testbilder werden nie Training.

1.18 unabhängige, bislang nicht exponierte Testwelten/Szenarien festlegen und
   hashen, bevor irgendein Kandidat dort Bilder sieht. Fünf Map-Familien abdecken;
   initial sichtbare und echte Suchfälle, Nah-/Fernsuche, Ablenkungen und die
   beabsichtigten Störungen aus den bestehenden Aufgaben berücksichtigen.
2. Für jedes Paar identische Szenario-/Umwelt-/Störungs-/Physikdefinition, eigene
   getrennte Aufzeichnungen, tatsächliche unabhängige Bootbewegung und NoRadio.
   Nicht bit-identische Bilder nach unterschiedlichen Aktionen erwarten.
3. Baseline = eingefrorener originaler R15-Laufzeitstand aus eigenem Paket.
   Kandidat = eingefrorenes neues Hybridpaket. Baseline darf nicht heimlich den
   neuen Recognizer oder neue Aufgabensteuerung konsumieren.
4. Beide sind Policy allein, ohne Expertenpräfix/Rescue. Eine Expertenübernahme
   würde eine andere Messung darstellen und darf nicht als Policy-Erfolg zählen.
5. Erst kleine Harness-Setup-/Bindingsprüfung auf bekannten Entwicklungsdaten;
   dadurch keinen unabhängigen Testfall bereits zur Modellauswahl exponieren.
6. Sichere acht Slots verwenden. Sammlung ist beendet; keine konkurrierende
   GPU-Trainingsschleife. Start-/Memory-Reserven weiterhin prüfen.
7. Home-Fallback zählt als fehlgeschlagene Bootmission und wird vor Rückkehr
   abgebrochen; keine Home-Videos und keine Home-Trainingsdaten erzeugen.
8. Pro Fall native physische Landung/Disarm, Kollisionen, falsche Objektkontakte,
   Wasser, Zeit bis Landung, Entdeckung/Identität/Geometrie, Störungsabdeckung,
   actual-command-Historie und Source-/Input-Provenienz prüfen.
9. Nur geschlossene abgeschlossene Fälle in den Nenner aufnehmen. Unterbrochene,
   ungestartete und Setup-fehlgeschlagene Fälle gesondert ausweisen.
10. Technische/physische Verletzung:Starts stoppen, Beweise behalten. Policy-
    Fehler:keine Parameter/Modelle während der Suite anpassen. Suite zuerst als
    zurückgezogen markieren, bevor eine spätere neue Revision auf unabhängigen
    Welten beurteilt werden könnte. Zeit erlaubt nicht automatisch einen zweiten Test.
11. Bei Zeitmangel nur vollständig gepaarte abgeschlossene Fälle vergleichen;
    fehlende Menge/Abdeckung berichten. Nicht einen einzelnen erfolgreichen
    Kandidatenfall gegen einen anderen Baseline-Fall stellen.
12. Ergebnis ist Vergleich des gesamten Hybridstandes. Controller und Wahrnehmung
    können beide unterschiedlich sein; daraus keinen isolierten neuronalen
    Kausaleffekt oder allgemeine Zuverlässigkeitsgarantie ableiten.

**Ausgang H:** eingefrorener Szenarioplan, pro Fall Hashes/Rohresultat/Physik-Audit,
`native_comparison_report.json` mit vollständigen Paaren, tatsächlichen Raten und Lücken.

## 12. Phase I — Begrenzter Tidewater-Transfer

1. Nur mit vor diesem Test eingefrorenem Modell-/Steuerungspaket. Kein Lernen,
   keine Threshold-Auswahl und kein Bildtraining aus Tidewater.
2. Nur vorhandene VM-Testumgebung benutzen, mit unveränderter Spielphysik und
   unabhängiger Bootsteuerung. Kein Boot-Radio/Truth-Bypass für die Drohne.
3. Gematchte Basis-/Kandidatenstarts aus den vorhandenen relevanten Testarten
   benutzen:anfangs sichtbar, anfangs außerhalb des Blicks, entferntere Suche und
   bewegtes Boot, soweit im verbliebenen Budget ausführbar. Vorher festlegen,
   welche kurzen Fälle in das4h-Gesamtbenchmarkbudget passen.
4. Tatsächlichen Spiele-/Browser-Runtimepfad und die geladenen Weight-/Source-
   Hashes prüfen. Nicht lediglich einen nativen Mock als Spieltest ausgeben.
5. Keine neue Stundenproduktion von Videos. Bei relevantem Fehler nur kurze
   echte Kamerasequenz mit richtigen Zeit-/Ownership-Labels auf VM exportieren.
6. Fehler bewahren und berichten. Keine Anpassung anhand des Spiels und danach
   denselben Spieldurchlauf als unabhängigen Test darstellen.
7. Windows-Imports und VM-relative Imports sind verschieden. Keine VM-Dateien
   blind in die Windows-Spielproduktion kopieren. Der Auftrag verlangt eine lokale
   sichere Experimentlieferung; ein unqualifizierter Kandidat wird nicht installiert.

**Ausgang I:** tatsächliche externe Vergleichsergebnisse und Quellen-/Stacknachweise
oder explizite Begründung, dass aufgrund vorgelagerter Fehler/Zeit kein Test erfolgte.

## 13. Phase J — Endexport, Wiederherstellung und Abschlussbericht

Diese Phase läuft nicht ausschließlich am Ende:Nach jedem wichtigen Checkpoint
und Freeze muss bereits ein verifizierter lokaler Snapshot bestehen.

Endlieferung:

- Gewählte beste Variante und letzter tatsächlich fortsetzbarer Checkpoint.
- Falls keine neue Variante qualifiziert:den experimentellen Zustand ausdrücklich
  unqualifiziert markieren und den ursprünglichen Basiszustand ebenfalls erhalten.
- Vollständige Quellen-/Konfigurations-/Kalibrierungs-/Modellmanifeste mit Hashes.
- Optimizer/RNG/Schritt/Epoche und genaue Resume-Anweisung; fehlende Resume-
  Bestandteile nicht verschweigen oder eine exakte Fortsetzung behaupten.
- Originalmasken-Manifeste, neue Zulassungs-/Ablehnungs-/Split-/Weltlisten und
  aussagekräftige Consumer-/Zweck-Audits; Rohbilder im Budget nicht alle herunterladen.
- Trainingsvergleich, native Paare, externe Ergebnisse, bekannte Fehler und
  nicht ausgeführte Abdeckung.
- Kurzes `RESTORE_AND_RUN.md` mit exakten vorhandenen Dateien/Commands,
  Paketversionen und Unterscheidung Training fortsetzen / Inferenz / Experiment.

Prüfreihenfolge:

1. VM-Artefakte stabil/geschlossen, Hash-/Größenmanifest erstellen.
2. Kompaktes Paket atomar veröffentlichen; kein ZIP lesen, während es noch wächst.
3. Lokalen Download vollständig abwarten, SHA256 und Bytes prüfen.
4. ZIP-Pfade gegen Traversal prüfen und alle Member-Hashes prüfen.
5. Besonders `best.pt`, `latest.pt` und eingefrorenes Kandidatenmanifest mit den
   tatsächlich letzten gewählten VM-Hashes vergleichen.
6. Neues ZIP plus Receipt liegt physisch auf Laptop. Erst jetzt Export als fertig markieren.
7. Wiederherstellungs-/Load-Test aus lokaler Lieferung, soweit Plattform vorhanden;
   verbleibende GPU-/Linux-Anforderungen dokumentieren.
8. Eigene abgeschlossene Prozesse sauber beenden, keine fremden Prozesse anfassen.
9. Ehrlichen Abschlussbericht vor Deadline schreiben:geplante/tatsächliche
   Episoden, zurückgewiesene Fälle, behaltene Maskenanteile, Lernkomponente,
   Validierungsänderung, vollständige Testpaare, experimentell/qualifiziert,
   genaue lokale Pfade und Grenzen. Keine crash-proof-/Hardware-Garantie.
10. Nach finalem Bericht bestehenden30-Minuten-Heartbeat über Automation-Tool
    löschen. Den laufenden Backup-Watcher nicht vor Prüfung der letzten lokalen
    Lieferung stoppen; er darf bis seiner konservativen Deadline weiterlaufen.

## 14. Fehler- und Wiederanlauf-Tabelle

| Beobachtung | Sofortige Aktion | Zulässiger nächster Schritt | Verbotene Abkürzung |
|---|---|---|---|
| SSH einmal kurz weg | Eigene lokalen Prozesse/letzte Receipts lesen; begrenzt erneut verbinden | Identität erneut prüfen und aktuellen Zustand lesen | Neue Jobs blind duplizieren; Hostkeyprüfung deaktivieren |
| Launcher liefert PID, kein neuer State | Prozess/Startzeit/Log prüfen | Nur nach nachgewiesenem Exit spezifischen Startfehler in neuer Revision reparieren | Alte PIDs für lebendig halten |
| State-Zeit alt, Schritte wachsen | Weiterlaufen lassen; State schreibt eventuell nur bei abgeschlossenen Jobs | Nächsten echten Ereignisabschluss abwarten | Gesunden Worker als stalled töten |
| Keine Frames/CPU, unveränderte Datei | Child/Logs/I/O/Ressourcen prüfen | Nachweisbarer technischer Fehler gezielt beheben | Zeitlimit pauschal verlängern |
| Suchboot im Erstbild | Episode als Zweckfehler zurückweisen | Statische Startblickrichtung neu erstellen und tatsächliches Erstbild prüfen | Boot verstecken, Alpha/Masken/Blackout nutzen |
| Far-Fall ist tatsächlich nah | Tatsächliche Distanz aus separatem Observer lesen | Startgeometrie/-Vorbereitung korrigieren | Metadatenband zum gemessenen8m-Fall umbenennen |
| Fault nicht ausgeführt | Fehlende Abdeckung markieren | Trigger/Pfad aus tatsächlich öffentlicher Geometrie reparieren und neu prüfen | `fault_frames` oder Coverage von Hand setzen |
| Learner rettet sich selbst | Keine Expertenrettung behaupten | Als selbständige Recovery getrennt berichten; Rescue-Familie weiter offen | Übernahme künstlich früher auslösen, nur damit ein Lehrervideo entsteht |
| Fehler nach schon unterstütztem Touchdown | Terminalregel und echte Kontakte prüfen | Unnötige Übernahme/Kameraänderung reparieren | Als erfolgreiche Rettung labeln |
| Falsches Objekt/Wasser/Kollision | Collection-/Eval-Neustarts stoppen, Quelle einfrieren | Gezielte Ursache aus RGB/Command/Contact analysieren | Fehler aus Bericht entfernen oder Scorer lockern |
| Bilder/Labels nicht exakt verbunden | Frame/Derivativ verweigern | Capture-Pipeline-/Delay-Verbindung korrigieren | Nächste Zeit oder Segmentierung eines anderen Bildes benutzen |
| Weltcache passt nicht zur Map | Breite Sammlung dieser Welt stoppen | Passenden Cache herstellen und physisch prüfen | Nur `Scenario.kind` ändern |
| Masken-Datei erstellt, Consumer ignoriert sie | Kein Training | Loss-/Gradientenprobe im echten Consumer reparieren | Behaupten, die Daten seien nun bereinigt |
| NaN/OOM im Training | Checkpoint/Logs bewahren, betroffenen Lauf beenden | Nach konkreter Ressourcen-/Numerikdiagnose kleinere sichere Einstellung in neuer Revision | Unbesehen Epochenschleife wiederholen |
| Neue Variante schlechter | Basis erhalten, neue Variante experimentell sichern | Fehler und Limits berichten | Testdaten zur Modellwahl verwenden |
| Backup lokal unverifiziert | Kein neues Langtraining starten | Snapshot/Download/Hash/Member-Prüfung reparieren | Remote `saved` als lokalen Sicherungsbeweis behandeln |
| VM stirbt früher | Lokale geprüfte Pakete inventarisieren | Tatsächlichen Stand/Resume-Lücken liefern | Verlängerung kaufen oder nicht vorhandene Ergebnisse erfinden |
| Budget wird knapp | Neue Sammlung zuerst reduzieren, früh sichern | Kleinere gültige Lieferung mit ehrlichen Nennern | Prüfungen abschalten oder bis zur letzten Minute rendern |

## 15. Abschlussbedingung dieser Anleitung

Der Plan gilt nicht als ausgeführt, weil alle Checkboxen manuell angehakt sind.
Für jeden erledigten Schritt müssen die referenzierten echten Receipts und
Artefakte vorhanden sein. Die Arbeit ist nur dann fertig, wenn der letzte relevante
Modell-/Resume-Stand lokal verifiziert vorliegt und der Bericht tatsächliche
Ergebnisse, offene Aufgaben und Grenzen wiedergibt. Das darf auch ein ehrliches
experimentelles oder nicht verbessertes Resultat sein.
