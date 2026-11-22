// AERODOCK project site: English and German text.
//
// Every visible string lives here. The markup points at a key with
// data-i18n (text), data-i18n-attr="attribute:key" (aria-label, alt, meta
// content) and switches language with the EN / DE buttons in the navigation.
// The page starts in German for visitors from Austria, Germany and Switzerland,
// in English everywhere else (see the country lookup below).
// app.js and playcheck.js read the same dictionary through AERODOCK_I18N.t().

( () => {

	const KEY = 'aerodock-lang';

	const LANGS = {

		en: {
			'meta.title': 'AERODOCK — a drone that lands itself on a moving boat',
			'meta.description': 'A camera-guided drone finds a moving boat, matches its deck and lands on it. Trained only in simulation, flown by PX4.',

			'nav.how': 'How it works',
			'nav.vehicles': 'Vehicles',
			'nav.simulation': 'Simulation',
			'nav.play': 'Play',
			'nav.results': 'Results',
			'nav.development': 'Development',
			'nav.sections': 'Sections',
			'nav.language': 'Language',

			'hero.f1t': '18 of 20',
			'hero.f1x': 'benchmark missions landed',
			'hero.f2t': 'Camera lands it',
			'hero.f2x': 'the boat\'s radio can help find it, never lands it',
			'hero.f3t': '0 images',
			'hero.f3x': 'of the test world used in training',

			'problem.h2': 'The problem',
			'problem.lead': 'A boat does not wait. It moves, turns, and rises and falls with every wave. The drone has to find it, catch up, and set down at the one moment the deck is safe.',
			'problem.p1t': 'A small, moving target.',
			'problem.p1x': 'The landing pad is 60\u00a0cm wide, on a boat that keeps driving.',
			'problem.p2t': 'Wind and waves.',
			'problem.p2x': 'Crosswind pushes the drone while the deck pitches, rolls and heaves.',
			'problem.p3t': 'Radio to find, vision to land.',
			'problem.p3x': 'The boat\'s radio gets the drone to the target; nothing from the boat steers the landing itself — the camera and the pad geometry do.',

			'how.h2': 'How it works',
			'how.lead': 'Two neural networks look at the camera image and report what they see. Control code and the PX4 autopilot do the flying. An earlier network that flew the drone directly landed in none of its test flights.',
			'how.archAria': 'Signal flow: camera and drone sensors feed learned perception, then geometric localization, then the landing controller, then PX4, which drives the motors and the camera gimbal. The camera sees the result and the loop repeats 25 times per second.',
			'how.loop': 'The drone moves, the camera sees a new image — 25 times per second',
			'how.camera': 'Camera',
			'how.cameraS': '+ drone sensors',
			'how.see': 'See',
			'how.seeS': 'neural network',
			'how.measure': 'Measure',
			'how.measureS': 'pad geometry',
			'how.decide': 'Decide',
			'how.decideS': 'landing controller',
			'how.fly': 'Fly',
			'how.flyS': 'PX4 autopilot',
			'how.ariaCamera': 'Camera and sensors',
			'how.ariaSee': 'Learned perception',
			'how.ariaMeasure': 'Geometric localization',
			'how.ariaDecide': 'Landing controller',
			'how.ariaFly': 'PX4 flight control',
			'how.h3': 'One flight, six steps',
			'how.ph1t': 'Search',
			'how.ph1x': 'Sweep the camera until a boat appears.',
			'how.ph2t': 'Identify',
			'how.ph2x': 'Fly closer and confirm it is the right boat.',
			'how.ph3t': 'Approach',
			'how.ph3x': 'Close the distance and keep the boat in view.',
			'how.ph4t': 'Align',
			'how.ph4x': 'Match the deck\'s speed and heading above the pad.',
			'how.ph5t': 'Descend',
			'how.ph5x': 'Come down only while the pad is measured.',
			'how.ph6t': 'Touch down',
			'how.ph6x': 'Land, disarm and stay on the pad.',

			'veh.h2': 'Two vehicles, designed in CAD',
			'veh.lead': 'Both were modelled part by part in FreeCAD and brought into the physics simulation with their real mass, joints and collision shapes.',
			'veh.drone.h3': 'The drone',
			'veh.drone.p': 'A Holybro X500 V2 quadrotor with a pan-tilt camera, flown by the unmodified PX4 autopilot.',
			'veh.massT': 'Mass',
			'veh.massV': '2.07 kg',
			'veh.camT': 'Camera',
			'veh.camV': '640 × 360, 25 Hz',
			'veh.autoT': 'Autopilot',
			'veh.autoV': 'PX4 1.16',
			'veh.partsT': 'Parts',
			'veh.partsV': 'about €1,760',
			'veh.drone.link': 'Drone simulation',
			'veh.boat.alt1': 'AERODOCK boat, exterior render',
			'veh.boat.alt2': 'AERODOCK boat with the hull hidden: landing bay, lift, batteries and electronics',
			'veh.boat.showInside': 'Show inside',
			'veh.boat.showOutside': 'Show outside',
			'veh.boat.h3': 'The boat — AERODOCK',
			'veh.boat.p': 'A drone-carrying boat. Two lids slide open and a platform lifts the landing pad above the deck.',
			'veh.padT': 'Landing pad',
			'veh.padV': '60 × 60 cm',
			'veh.driveT': 'Drive',
			'veh.driveV': 'two electric motors',
			'veh.physT': 'Physics',
			'veh.physV': 'buoyancy, drag, waves',
			'veh.camsT': 'Cameras',
			'veh.camsV': 'route and landing bay',
			'veh.boat.link': 'Boat simulation',

			'worlds.h2': 'Trained in one world, tested in another',
			'worlds.lead': 'All training happened in MuJoCo, a physics simulator with simple graphics. The realistic simulator is an open-source ocean game we extended. The policy never saw it during training, and lands there anyway.',
			'worlds.trainTag': 'Training',
			'worlds.mujoco.p': 'Accurate physics, plain rendering. Five kinds of coast, random routes, wind, waves and other boats. PX4 runs in step with the physics.',
			'worlds.testTag': 'Test only',
			'worlds.real.h3': 'Realistic simulator',
			'worlds.real.p': 'A realistic ocean rendered in the browser. The same physics, autopilot and policy run locally — no server. You can fly it yourself and hand over to the policy with one key.',
			'worlds.r1b': '1000 Hz',
			'worlds.r1s': 'physics',
			'worlds.r2b': '250 Hz',
			'worlds.r2s': 'autopilot sensors and motors',
			'worlds.r3b': '25 Hz',
			'worlds.r3s': 'camera and policy',

			'play.h2': 'Fly it yourself',
			'play.lead1': 'The realistic simulator runs in your browser. Fly the drone, then press',
			'play.lead2': 'and let the policy find the boat and land. It needs a computer with Chrome or Edge, a capable graphics card and about 150\u00a0MB of download.',
			'play.check': 'Check my computer and play',
			'play.watch': 'Watch the video',
			'play.caption': 'A recorded flight in the realistic simulator: launch, handover, landing.',
			'play.player.play': 'Play',
			'play.player.pause': 'Pause',
			'play.player.seek': 'Seek',
			'play.player.speed': 'Playback speed',
			'play.player.fullscreen': 'Fullscreen',
			'play.player.exitFullscreen': 'Exit fullscreen',

			'res.h2': 'Results',
			'res.lead': 'Every policy flies the same 20 missions on five kinds of coast: boat speeds up to 1.5\u00a0m/s, 4\u00a0m/s crosswind, waves, a search from 100\u00a0m away and other boats in the scene. A landing counts only if the drone ends up disarmed and stable on the pad.',
			'res.chartAria': 'Benchmark scores: teacher 99.2 with 20 of 20 landings; final version 79.9 with 18 of 20; 8 November version with pad finder, camera only, 72.8 with 18 of 20; camera first, before the search head, 47.5 with 11 of 20; radio-dependent 44.4 with 7 of 20.',
			'res.good.h3': 'What the final version does well',
			'res.good.p': 'It landed 18 of 20: every landing, wind and search mission, with boat speeds up to 1.5\u00a0m/s, 4\u00a0m/s crosswind and the search from 100\u00a0m with other boats in the scene. The boat\'s radio only helps it find the boat; the camera lands it.',
			'res.fail.h3': 'Where it still fails',
			'res.fail.p': 'Two missions with waves. The drone reaches the pad, then hovers just above it waiting for a clean measurement of the pad until its time runs out. Everything so far is simulation; there has been no flight with real hardware.',
			'res.note': 'The teacher uses simulator information a real drone would not have. It produces the training examples and marks the upper limit; it is not a deployable policy.',
			'res.noteLink': 'Benchmark data and every flight',

			'story.h2': 'How it got here',
			'story.s1when': 'Step 1',
			'story.s1t': 'Build the world',
			'story.s1p': 'Drone and boat from CAD, water and wind physics, and the real PX4 autopilot in the loop.',
			'story.s2when': 'Step 2',
			'story.s2t': 'Let a network fly',
			'story.s2p': 'A network trained to copy the teacher\'s commands landed in none of its 12 test flights. Every small mistake changed what it saw next.',
			'story.s3when': 'Step 3',
			'story.s3t': 'Split seeing from flying',
			'story.s3p': 'From here on the networks only estimate where the boat and the pad are, and control code flies. The first version leaned on the boat\'s radio: 7 of 20, and none of the six missions without it.',
			'story.s4when': 'Step 4',
			'story.s4t': 'Camera first',
			'story.s4p': 'Trust the camera for position. 11 of 20, but it landed only half of the missions that start with a search.',
			'story.s5when': 'Step 5',
			'story.s5t': 'Add a search head',
			'story.s5p': 'A small network that marks every boat and picks out the target, trained while the main network stayed frozen. 18 of 20, camera only.',
			'story.s6when': 'Step 6',
			'story.s6t': 'One final version',
			'story.s6p': 'The drone flies to the boat\'s radio position first and lets the camera confirm it, and the small pad finder from earlier versions is gone. 18 of 20 again, and the same build flies in the realistic simulator.',

			'end.h2': 'Look inside',
			'end.repo.t': 'Repository',
			'end.repo.s': 'Code, models and data layout',
			'end.train.t': 'Training and architecture',
			'end.train.s': 'Network, teacher and controller in detail',
			'end.sim.t': 'Realistic simulator',
			'end.sim.s': 'Run it locally and fly',
			'end.bench.t': 'Benchmark',
			'end.bench.s': '20 missions, five policies, all evidence',

			'footer.tag': 'AERODOCK — vision-based drone landing',

			'chart.landed': 'landed',
			'chart.badge': 'current',
			'chart.teacher.name': 'Teacher',
			'chart.teacher.note': 'sees simulator truth',
			'chart.teacher.value': '99.2',
			'chart.current.name': 'Final version',
			'chart.current.note': 'two networks, radio if offered',
			'chart.current.value': '79.9',
			'chart.nov.name': '8 November',
			'chart.nov.note': 'with pad finder, no radio',
			'chart.nov.value': '72.8',
			'chart.r15.name': 'Camera first',
			'chart.r15.note': 'before the search head',
			'chart.r15.value': '47.5',
			'chart.radio.name': 'Radio-dependent',
			'chart.radio.note': 'landed only with boat radio',
			'chart.radio.value': '44.4',

			'stage.sense.title': 'Camera and drone sensors',
			'stage.sense.text': 'Everything the policy knows comes from the drone itself: one camera on a pan-tilt mount and the autopilot\'s own estimate of where the drone is and how it moves.',
			'stage.sense.f1k': 'Image',
			'stage.sense.f1v': '640 × 360 colour, 25 frames per second',
			'stage.sense.f2k': 'Own state',
			'stage.sense.f2v': 'position, velocity, attitude, camera angles',
			'stage.sense.f3k': 'Radio',
			'stage.sense.f3v': 'optional: the boat\'s position helps find it, never lands it',
			'stage.see.title': 'See — two networks find the boat and the pad',
			'stage.see.text': 'Both share one image encoder. The search head marks every boat in the frame and says which one is the target. The main network says whether the pad is in view and where it is in the picture, so the camera can stay on it, and estimates where the pad is relative to the drone and how the deck moves, with a short memory of earlier frames.',
			'stage.see.f1k': 'Search head',
			'stage.see.f1v': 'about 45,000 parameters: every boat, and which one is the target',
			'stage.see.f2k': 'Main network',
			'stage.see.f2v': 'about 1.55 million: pad in view, pad position and deck motion, GRU memory',
			'stage.see.f3k': 'Neither flies',
			'stage.see.f3v': 'they report what they see; control code decides the moves',
			'stage.measure.title': 'Measure — geometry locates the pad',
			'stage.measure.text': 'Close to the boat, the known marking on the landing pad is fitted in the image with the calibrated camera. That gives the pad\'s position in metres — a measurement, not a guess. Tracking it over time gives the deck\'s motion.',
			'stage.measure.f1k': 'Input',
			'stage.measure.f1v': 'pad markings and camera calibration',
			'stage.measure.f2k': 'Output',
			'stage.measure.f2v': 'pad position, heading and deck motion',
			'stage.measure.f3k': 'Rule',
			'stage.measure.f3v': 'a confident network alone cannot start the descent',
			'stage.decide.title': 'Decide — an explicit landing controller',
			'stage.decide.text': 'A controller turns the estimates into a flight: search, approach, match the deck, descend, touch down. It limits every command and backs off when the measurement is lost.',
			'stage.decide.f1k': 'Output',
			'stage.decide.f1v': 'three velocities, turn rate, camera pan and tilt',
			'stage.decide.f2k': 'Rate',
			'stage.decide.f2v': '25 commands per second',
			'stage.decide.f3k': 'Safety',
			'stage.decide.f3v': 'bounded commands, descent only on a measured pad, recovery',
			'stage.fly.title': 'Fly — PX4 turns commands into thrust',
			'stage.fly.text': 'The open-source PX4 autopilot — the same software that flies real drones — stabilises the aircraft and drives the four motors. The policy only tells it where to go.',
			'stage.fly.f1k': 'Autopilot',
			'stage.fly.f1v': 'PX4 1.16, unmodified',
			'stage.fly.f2k': 'Loop',
			'stage.fly.f2v': 'sensors and motors at 250 Hz',
			'stage.fly.f3k': 'Commands',
			'stage.fly.f3v': 'velocity setpoints in PX4 offboard mode',

			'pc.checking': 'Checking your computer…',
			'pc.good': 'Your computer looks ready.',
			'pc.note': 'The first start compiles the graphics and can take a minute or two.',
			'pc.slow': 'It will probably run slowly here.',
			'pc.no': 'The simulator cannot run here.',
			'pc.start': 'Start the simulator',
			'pc.watch': 'Watch the video',
			'pc.playAnyway': 'Play anyway',
			'pc.fail': 'The check failed: ',
			'pc.phone': 'Phones and tablets cannot run it yet. Open this page on a computer.',
			'pc.noWebgpu': 'This browser has no WebGPU. Use a current Chrome or Edge.',
			'pc.noAdapter': 'WebGPU is turned off or the graphics driver is blocked.',
			'pc.fallback': 'The browser draws without the graphics card (software rendering).',
			'pc.gpuSlow': 'The {gpu} is too slow for real time (about {n} GFLOP/s in a short test).',
			'pc.gpuOk': 'WebGPU on {gpu}, about {n} GFLOP/s.',
			'pc.memLow': 'About {n} GB of memory; it needs 8 GB or more.',
			'pc.memOk8': '8 GB or more of memory.',
			'pc.memOkN': '{n} GB of memory.',
			'pc.saveData': 'Data saver is on; the simulator downloads about 150 MB.',
			'pc.gpuFallback': 'graphics card',
		},

		de: {
			'meta.title': 'AERODOCK – eine Drohne, die selbst auf einem fahrenden Boot landet',
			'meta.description': 'Eine kameragesteuerte Drohne findet ein fahrendes Boot, gleicht sich an dessen Deck an und landet darauf. Nur in der Simulation trainiert, von PX4 geflogen.',

			'nav.how': 'So funktioniert es',
			'nav.vehicles': 'Fahrzeuge',
			'nav.simulation': 'Simulation',
			'nav.play': 'Spielen',
			'nav.results': 'Ergebnisse',
			'nav.development': 'Entwicklung',
			'nav.sections': 'Bereiche',
			'nav.language': 'Sprache',

			'hero.f1t': '18 von 20',
			'hero.f1x': 'Benchmark-Missionen gelandet',
			'hero.f2t': 'Die Kamera landet',
			'hero.f2x': 'das Funkgerät des Boots hilft beim Finden, landet aber nie',
			'hero.f3t': '0 Bilder',
			'hero.f3x': 'der Testwelt im Training verwendet',

			'problem.h2': 'Das Problem',
			'problem.lead': 'Ein Boot wartet nicht. Es fährt, dreht sich und hebt und senkt sich mit jeder Welle. Die Drohne muss es finden, aufholen und genau in dem Moment aufsetzen, in dem das Deck sicher ist.',
			'problem.p1t': 'Ein kleines, bewegliches Ziel.',
			'problem.p1x': 'Die Landeplattform ist 60\u00a0cm breit – auf einem Boot, das weiterfährt.',
			'problem.p2t': 'Wind und Wellen.',
			'problem.p2x': 'Seitenwind drückt die Drohne, während das Deck nickt, rollt und sich hebt und senkt.',
			'problem.p3t': 'Funk zum Finden, Sicht zum Landen.',
			'problem.p3x': 'Das Funkgerät des Boots bringt die Drohne zum Ziel; nichts vom Boot steuert die Landung selbst – das tun die Kamera und die Geometrie der Plattform.',

			'how.h2': 'So funktioniert es',
			'how.lead': 'Zwei neuronale Netze sehen das Kamerabild und berichten, was sie erkennen. Steuerungscode und der PX4-Autopilot fliegen. Ein früheres Netz, das die Drohne direkt flog, landete in keinem seiner Testflüge.',
			'how.archAria': 'Signalfluss: Kamera und Drohnensensoren speisen die erlernte Wahrnehmung, dann die geometrische Lokalisierung, dann den Landeregler, dann PX4, das die Motoren und die Kameraneigung ansteuert. Die Kamera sieht das Ergebnis, und die Schleife wiederholt sich 25-mal pro Sekunde.',
			'how.loop': 'Die Drohne bewegt sich, die Kamera sieht ein neues Bild – 25-mal pro Sekunde',
			'how.camera': 'Kamera',
			'how.cameraS': '+ Drohnensensoren',
			'how.see': 'Sehen',
			'how.seeS': 'neuronales Netz',
			'how.measure': 'Messen',
			'how.measureS': 'Plattformgeometrie',
			'how.decide': 'Entscheiden',
			'how.decideS': 'Landeregler',
			'how.fly': 'Fliegen',
			'how.flyS': 'PX4-Autopilot',
			'how.ariaCamera': 'Kamera und Sensoren',
			'how.ariaSee': 'Erlernte Wahrnehmung',
			'how.ariaMeasure': 'Geometrische Lokalisierung',
			'how.ariaDecide': 'Landeregler',
			'how.ariaFly': 'PX4-Flugsteuerung',
			'how.h3': 'Ein Flug, sechs Schritte',
			'how.ph1t': 'Suchen',
			'how.ph1x': 'Die Kamera schwenken, bis ein Boot erscheint.',
			'how.ph2t': 'Identifizieren',
			'how.ph2x': 'Näher fliegen und bestätigen, dass es das richtige Boot ist.',
			'how.ph3t': 'Annähern',
			'how.ph3x': 'Den Abstand verringern und das Boot im Blick behalten.',
			'how.ph4t': 'Ausrichten',
			'how.ph4x': 'Geschwindigkeit und Kurs des Decks über der Plattform angleichen.',
			'how.ph5t': 'Sinken',
			'how.ph5x': 'Nur sinken, solange die Plattform gemessen wird.',
			'how.ph6t': 'Aufsetzen',
			'how.ph6x': 'Landen, entwaffnen und auf der Plattform bleiben.',

			'veh.h2': 'Zwei Fahrzeuge, in CAD entworfen',
			'veh.lead': 'Beide wurden in FreeCAD Bauteil für Bauteil modelliert und mit ihrer realen Masse, ihren Gelenken und Kollisionsformen in die Physiksimulation übernommen.',
			'veh.drone.h3': 'Die Drohne',
			'veh.drone.p': 'Ein Holybro X500 V2 Quadrocopter mit Schwenk-Neige-Kamera, geflogen vom unveränderten PX4-Autopiloten.',
			'veh.massT': 'Masse',
			'veh.massV': '2,07 kg',
			'veh.camT': 'Kamera',
			'veh.camV': '640 × 360, 25 Hz',
			'veh.autoT': 'Autopilot',
			'veh.autoV': 'PX4 1.16',
			'veh.partsT': 'Teile',
			'veh.partsV': 'etwa 1.760 €',
			'veh.drone.link': 'Drohnensimulation',
			'veh.boat.alt1': 'AERODOCK-Boot, Außenansicht (Render)',
			'veh.boat.alt2': 'AERODOCK-Boot mit ausgeblendetem Rumpf: Landebucht, Lift, Akkus und Elektronik',
			'veh.boat.showInside': 'Innenansicht zeigen',
			'veh.boat.showOutside': 'Außenansicht zeigen',
			'veh.boat.h3': 'Das Boot – AERODOCK',
			'veh.boat.p': 'Ein Boot, das eine Drohne trägt. Zwei Klappen fahren auf, und eine Plattform hebt die Landeplattform über das Deck.',
			'veh.padT': 'Landeplattform',
			'veh.padV': '60 × 60 cm',
			'veh.driveT': 'Antrieb',
			'veh.driveV': 'zwei Elektromotoren',
			'veh.physT': 'Physik',
			'veh.physV': 'Auftrieb, Luftwiderstand, Wellen',
			'veh.camsT': 'Kameras',
			'veh.camsV': 'Route und Landebucht',
			'veh.boat.link': 'Bootssimulation',

			'worlds.h2': 'In einer Welt trainiert, in einer anderen getestet',
			'worlds.lead': 'Das gesamte Training fand in MuJoCo statt, einem Physiksimulator mit einfacher Grafik. Der realistische Simulator ist ein Open-Source-Ozeanspiel, das wir erweitert haben. Die Steuerung hat ihn im Training nie gesehen und landet trotzdem darin.',
			'worlds.trainTag': 'Training',
			'worlds.mujoco.p': 'Genaue Physik, schlichte Darstellung. Fünf Küstenarten, zufällige Routen, Wind, Wellen und andere Boote. PX4 läuft im Gleichschritt mit der Physik.',
			'worlds.testTag': 'Nur Test',
			'worlds.real.h3': 'Realistischer Simulator',
			'worlds.real.p': 'Ein realistischer Ozean, im Browser gerendert. Dieselbe Physik, derselbe Autopilot und dieselbe Steuerung laufen lokal – ohne Server. Sie können selbst fliegen und mit einer Taste an die Steuerung übergeben.',
			'worlds.r1b': '1000 Hz',
			'worlds.r1s': 'Physik',
			'worlds.r2b': '250 Hz',
			'worlds.r2s': 'Autopilot-Sensoren und Motoren',
			'worlds.r3b': '25 Hz',
			'worlds.r3s': 'Kamera und Steuerung',

			'play.h2': 'Selbst fliegen',
			'play.lead1': 'Der realistische Simulator läuft in Ihrem Browser. Fliegen Sie die Drohne und drücken Sie dann',
			'play.lead2': 'und lassen Sie die Steuerung das Boot finden und landen. Nötig sind ein Computer mit Chrome oder Edge, eine leistungsfähige Grafikkarte und etwa 150\u00a0MB Download.',
			'play.check': 'Computer prüfen und spielen',
			'play.watch': 'Video ansehen',
			'play.caption': 'Ein aufgezeichneter Flug im realistischen Simulator: Start, Übergabe, Landung.',
			'play.player.play': 'Abspielen',
			'play.player.pause': 'Pause',
			'play.player.seek': 'Position',
			'play.player.speed': 'Geschwindigkeit',
			'play.player.fullscreen': 'Vollbild',
			'play.player.exitFullscreen': 'Vollbild verlassen',

			'res.h2': 'Ergebnisse',
			'res.lead': 'Jede Steuerung fliegt dieselben 20 Missionen an fünf Küstenarten: Bootsgeschwindigkeiten bis 1,5\u00a0m/s, 4\u00a0m/s Seitenwind, Wellen, eine Suche aus 100\u00a0m Entfernung und andere Boote in der Szene. Eine Landung zählt nur, wenn die Drohne am Ende entwaffnet und stabil auf der Plattform steht.',
			'res.chartAria': 'Benchmark-Ergebnisse: Lehrer 99,2 mit 20 von 20 Landungen; finale Version 79,9 mit 18 von 20; Version vom 8. November mit Plattformfinder, nur Kamera, 72,8 mit 18 von 20; Kamera zuerst, vor dem Suchkopf, 47,5 mit 11 von 20; funkabhängig 44,4 mit 7 von 20.',
			'res.good.h3': 'Was die finale Version gut kann',
			'res.good.p': 'Sie landete 18 von 20: jede Landungs-, Wind- und Suchmission, mit Bootsgeschwindigkeiten bis 1,5\u00a0m/s, 4\u00a0m/s Seitenwind und der Suche aus 100\u00a0m mit anderen Booten in der Szene. Das Funkgerät des Boots hilft nur beim Finden; die Kamera landet.',
			'res.fail.h3': 'Wo sie noch scheitert',
			'res.fail.p': 'Zwei Missionen mit Wellen. Die Drohne erreicht die Plattform und schwebt dann knapp darüber, bis ihre Zeit abläuft, weil sie auf eine saubere Messung der Plattform wartet. Bisher ist alles Simulation; einen Flug mit echter Hardware gab es nicht.',
			'res.note': 'Der Lehrer nutzt Simulatorinformationen, die eine echte Drohne nicht hätte. Er erzeugt die Trainingsbeispiele und markiert die Obergrenze; er ist keine einsetzbare Steuerung.',
			'res.noteLink': 'Benchmark-Daten und jeder Flug',

			'story.h2': 'Wie es dazu kam',
			'story.s1when': 'Schritt 1',
			'story.s1t': 'Die Welt bauen',
			'story.s1p': 'Drohne und Boot aus CAD, Wasser- und Windphysik und der echte PX4-Autopilot im Regelkreis.',
			'story.s2when': 'Schritt 2',
			'story.s2t': 'Ein Netz fliegen lassen',
			'story.s2p': 'Ein Netz, das die Befehle des Lehrers nachahmen sollte, landete in keinem seiner 12 Testflüge. Jeder kleine Fehler veränderte, was es als Nächstes sah.',
			'story.s3when': 'Schritt 3',
			'story.s3t': 'Sehen und Fliegen trennen',
			'story.s3p': 'Ab hier schätzen die Netze nur noch, wo Boot und Plattform sind, und Steuerungscode fliegt. Die erste Version stützte sich auf das Funkgerät des Boots: 7 von 20, und keine der sechs Missionen ohne Funk.',
			'story.s4when': 'Schritt 4',
			'story.s4t': 'Kamera zuerst',
			'story.s4p': 'Bei der Position der Kamera vertrauen. 11 von 20, aber nur die Hälfte der Missionen mit Suche gelang.',
			'story.s5when': 'Schritt 5',
			'story.s5t': 'Einen Suchkopf ergänzen',
			'story.s5p': 'Ein kleines Netz, das jedes Boot markiert und das Ziel auswählt, trainiert bei eingefrorenem Hauptnetz. 18 von 20, nur mit Kamera.',
			'story.s6when': 'Schritt 6',
			'story.s6t': 'Eine finale Version',
			'story.s6p': 'Die Drohne fliegt zuerst zur Funkposition des Boots und lässt die Kamera sie bestätigen; der kleine Plattformfinder früherer Versionen ist weg. Wieder 18 von 20, und derselbe Build fliegt im realistischen Simulator.',

			'end.h2': 'Einblick',
			'end.repo.t': 'Repository',
			'end.repo.s': 'Code, Modelle und Datenstruktur',
			'end.train.t': 'Training und Architektur',
			'end.train.s': 'Netz, Lehrer und Regler im Detail',
			'end.sim.t': 'Realistischer Simulator',
			'end.sim.s': 'Lokal starten und fliegen',
			'end.bench.t': 'Benchmark',
			'end.bench.s': '20 Missionen, fünf Steuerungen, alle Belege',

			'footer.tag': 'AERODOCK – visionbasierte Drohnenlandung',

			'chart.landed': 'gelandet',
			'chart.badge': 'aktuell',
			'chart.teacher.name': 'Lehrer',
			'chart.teacher.note': 'sieht die Simulator-Wahrheit',
			'chart.teacher.value': '99,2',
			'chart.current.name': 'Finale Version',
			'chart.current.note': 'zwei Netze, Funk falls vorhanden',
			'chart.current.value': '79,9',
			'chart.nov.name': '8. November',
			'chart.nov.note': 'mit Plattformfinder, ohne Funk',
			'chart.nov.value': '72,8',
			'chart.r15.name': 'Kamera zuerst',
			'chart.r15.note': 'vor dem Suchkopf',
			'chart.r15.value': '47,5',
			'chart.radio.name': 'Funkabhängig',
			'chart.radio.note': 'landete nur mit Bootsfunk',
			'chart.radio.value': '44,4',

			'stage.sense.title': 'Kamera und Drohnensensoren',
			'stage.sense.text': 'Alles, was die Steuerung weiß, kommt von der Drohne selbst: eine Kamera auf einem Schwenk-Neige-Sockel und die eigene Schätzung des Autopiloten, wo die Drohne ist und wie sie sich bewegt.',
			'stage.sense.f1k': 'Bild',
			'stage.sense.f1v': '640 × 360 in Farbe, 25 Bilder pro Sekunde',
			'stage.sense.f2k': 'Eigener Zustand',
			'stage.sense.f2v': 'Position, Geschwindigkeit, Lage, Kamerawinkel',
			'stage.sense.f3k': 'Funk',
			'stage.sense.f3v': 'optional: die Position des Boots hilft beim Finden, landet aber nie',
			'stage.see.title': 'Sehen – zwei Netze finden Boot und Plattform',
			'stage.see.text': 'Beide teilen sich einen Bild-Encoder. Der Suchkopf markiert jedes Boot im Bild und sagt, welches das Ziel ist. Das Hauptnetz sagt, ob die Plattform im Blick ist und wo sie im Bild liegt, damit die Kamera auf ihr bleibt, und schätzt, wo die Plattform relativ zur Drohne ist und wie sich das Deck bewegt – mit einem kurzen Gedächtnis früherer Bilder.',
			'stage.see.f1k': 'Suchkopf',
			'stage.see.f1v': 'etwa 45.000 Parameter: jedes Boot und welches das Ziel ist',
			'stage.see.f2k': 'Hauptnetz',
			'stage.see.f2v': 'etwa 1,55 Millionen: Plattform im Blick, Position und Decksbewegung, GRU-Gedächtnis',
			'stage.see.f3k': 'Keines fliegt',
			'stage.see.f3v': 'sie melden, was sie sehen; der Steuerungscode entscheidet über die Manöver',
			'stage.measure.title': 'Messen – Geometrie verortet die Plattform',
			'stage.measure.text': 'Nahe am Boot wird die bekannte Markierung auf der Landeplattform mit der kalibrierten Kamera im Bild eingepasst. Das ergibt die Position der Plattform in Metern – eine Messung, keine Schätzung. Die Verfolgung über die Zeit ergibt die Bewegung des Decks.',
			'stage.measure.f1k': 'Eingang',
			'stage.measure.f1v': 'Plattformmarkierungen und Kamerakalibrierung',
			'stage.measure.f2k': 'Ausgang',
			'stage.measure.f2v': 'Position, Ausrichtung und Decksbewegung der Plattform',
			'stage.measure.f3k': 'Regel',
			'stage.measure.f3v': 'ein sicheres Netz allein darf den Sinkflug nicht starten',
			'stage.decide.title': 'Entscheiden – ein expliziter Landeregler',
			'stage.decide.text': 'Ein Regler macht aus den Schätzungen einen Flug: suchen, annähern, Deck angleichen, sinken, aufsetzen. Er begrenzt jeden Befehl und bricht ab, wenn die Messung verloren geht.',
			'stage.decide.f1k': 'Ausgang',
			'stage.decide.f1v': 'drei Geschwindigkeiten, Drehrate, Kameraschwenk und -neigung',
			'stage.decide.f2k': 'Rate',
			'stage.decide.f2v': '25 Befehle pro Sekunde',
			'stage.decide.f3k': 'Sicherheit',
			'stage.decide.f3v': 'begrenzte Befehle, Sinkflug nur auf gemessene Plattform, Wiederaufnahme',
			'stage.fly.title': 'Fliegen – PX4 macht aus Befehlen Schub',
			'stage.fly.text': 'Der Open-Source-Autopilot PX4 – dieselbe Software, die echte Drohnen fliegt – stabilisiert das Fluggerät und treibt die vier Motoren an. Die Steuerung sagt ihm nur, wohin es fliegen soll.',
			'stage.fly.f1k': 'Autopilot',
			'stage.fly.f1v': 'PX4 1.16, unverändert',
			'stage.fly.f2k': 'Regelkreis',
			'stage.fly.f2v': 'Sensoren und Motoren mit 250 Hz',
			'stage.fly.f3k': 'Befehle',
			'stage.fly.f3v': 'Geschwindigkeits-Sollwerte im PX4-Offboard-Modus',

			'pc.checking': 'Ihr Computer wird geprüft…',
			'pc.good': 'Ihr Computer scheint bereit.',
			'pc.note': 'Der erste Start kompiliert die Grafik und kann ein bis zwei Minuten dauern.',
			'pc.slow': 'Hier läuft es wahrscheinlich langsam.',
			'pc.no': 'Der Simulator kann hier nicht laufen.',
			'pc.start': 'Simulator starten',
			'pc.watch': 'Video ansehen',
			'pc.playAnyway': 'Trotzdem spielen',
			'pc.fail': 'Die Prüfung ist fehlgeschlagen: ',
			'pc.phone': 'Smartphones und Tablets können ihn noch nicht ausführen. Öffnen Sie diese Seite an einem Computer.',
			'pc.noWebgpu': 'Dieser Browser hat kein WebGPU. Verwenden Sie ein aktuelles Chrome oder Edge.',
			'pc.noAdapter': 'WebGPU ist ausgeschaltet oder der Grafiktreiber ist blockiert.',
			'pc.fallback': 'Der Browser zeichnet ohne Grafikkarte (Software-Rendering).',
			'pc.gpuSlow': 'Die {gpu} ist zu langsam für Echtzeit (etwa {n} GFLOP/s in einem kurzen Test).',
			'pc.gpuOk': 'WebGPU auf {gpu}, etwa {n} GFLOP/s.',
			'pc.memLow': '{n} GB Arbeitsspeicher; nötig sind 8 GB oder mehr.',
			'pc.memOk8': '8 GB oder mehr Arbeitsspeicher.',
			'pc.memOkN': '{n} GB Arbeitsspeicher.',
			'pc.saveData': 'Datensparmodus ist an; der Simulator lädt etwa 150 MB herunter.',
			'pc.gpuFallback': 'Grafikkarte',
		},

	};

	const listeners = new Set();
	let current = 'en';
	let explicitChoice = false;

	const requested = new URLSearchParams( location.search ).get( 'lang' );
	let stored = null;
	try { stored = localStorage.getItem( KEY ); } catch ( error ) {}

	// A language from ?lang= or from an earlier visit wins. Otherwise the page opens
	// in German for visitors from Austria, Germany and Switzerland, and in English
	// everywhere else. The browser's own language and clock give the immediate guess,
	// so the page paints in a likely language; the country lookup below settles it.
	if ( requested && LANGS[ requested ] ) { current = requested; explicitChoice = true; }
	else if ( stored && LANGS[ stored ] ) { current = stored; explicitChoice = true; }
	else if ( germanLocale() ) current = 'de';

	const DACH = new Set( [ 'AT', 'DE', 'CH' ] );

	if ( ! explicitChoice ) {

		// Cloudflare Pages answers /cdn-cgi/trace with the visitor's country from the
		// connection, not from the browser settings. Any other host (a local server)
		// answers 404 and the guess above stands.
		const controller = new AbortController();
		const timer = setTimeout( () => controller.abort(), 2000 );
		fetch( '/cdn-cgi/trace', { cache: 'no-store', signal: controller.signal } )
			.then( ( response ) => response.ok ? response.text() : '' )
			.then( ( text ) => {

				const country = /^loc=([A-Z]{2})$/m.exec( text )?.[ 1 ];
				if ( country && DACH.has( country ) && ! explicitChoice ) switchLanguage( 'de' );

			} )
			.catch( () => {} )
			.finally( () => clearTimeout( timer ) );

	}

	const dict = () => LANGS[ current ] || LANGS.en;

	// German browser language (with or without a region) or a clock set in a
	// German-speaking country.
	function germanLocale() {

		const tags = Array.isArray( navigator.languages ) && navigator.languages.length ? navigator.languages : [ navigator.language || '' ];
		if ( tags.some( ( tag ) => /^de([-_](AT|DE|CH))?$/i.test( tag ) ) ) return true;
		const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
		return zone === 'Europe/Vienna' || zone === 'Europe/Berlin' || zone === 'Europe/Zurich';

	}

	function t( key ) {

		const value = dict()[ key ];
		if ( typeof value === 'string' ) return value;
		const fallback = LANGS.en[ key ];
		return typeof fallback === 'string' ? fallback : key;

	}

	function tf( key, vars ) {

		return t( key ).replace( /\{(\w+)\}/g, ( match, name ) => name in vars ? String( vars[ name ] ) : match );

	}

	function apply() {

		document.documentElement.lang = current;
		document.querySelectorAll( '[data-i18n]' ).forEach( ( el ) => { el.textContent = t( el.dataset.i18n ); } );
		document.querySelectorAll( '[data-i18n-attr]' ).forEach( ( el ) => {

			for ( const pair of el.dataset.i18nAttr.split( ';' ) ) {

				const [ attr, key ] = pair.split( ':' ).map( ( part ) => part.trim() );
				if ( attr && key ) el.setAttribute( attr, t( key ) );

			}

		} );
		document.querySelectorAll( '[data-set-lang]' ).forEach( ( button ) => button.setAttribute( 'aria-pressed', String( button.dataset.setLang === current ) ) );
		listeners.forEach( ( fn ) => fn( current ) );

	}

	function switchLanguage( next ) {

		if ( ! LANGS[ next ] || next === current ) return;
		current = next;
		apply();

	}

	// A click is a decision: it is remembered even when it keeps the current
	// language, so the guessed or looked-up country never overrules it later.
	function setLang( next ) {

		if ( ! LANGS[ next ] ) return;
		explicitChoice = true;
		try { localStorage.setItem( KEY, next ); } catch ( error ) {}
		switchLanguage( next );

	}

	document.querySelectorAll( '[data-set-lang]' ).forEach( ( button ) => button.addEventListener( 'click', () => setLang( button.dataset.setLang ) ) );

	window.AERODOCK_I18N = { t, tf, setLang, onChange: ( fn ) => listeners.add( fn ), get lang() { return current; } };
	apply();

} )();
