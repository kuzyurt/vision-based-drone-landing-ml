import assert from 'node:assert/strict';
import {FlightOperations} from '../src/game/FlightOperations.js';
import {SimulationBridge} from '../src/landing/SimulationBridge.js';
import * as E from '../src/engine/index.js';

const sent=[];
const op={mode:'boat',boatCamera:'boat_nav',autopilot:false,manualMotors:[70,30],
 _refreshUI(){},_toast(){},suppressedKeys:new Set(),app:{input:{keys:new Set()}},
 bridge:{send:p=>sent.push(p),selectCamera(){sent.push('camera switched')}}};
FlightOperations.prototype._receive.call(op,{mode:'drone',boat_camera:'boat_dock',boat_autopilot:true,boat:{port_power:0,starboard_power:0}});
assert.equal(op.mode,'boat');assert.equal(op.boatCamera,'boat_nav');
assert.equal(op.autopilot,false);assert.deepEqual(op.manualMotors,[70,30]);
FlightOperations.prototype.switchVehicle.call(op);
assert.equal(op.mode,'drone');assert.equal(sent[1],'camera switched');
const bridge=Object.create(SimulationBridge.prototype);
bridge.groups=new Map();bridge.meshes=new Map();bridge.app={scene:new E.Scene(),flightOps:op,camera:new E.PerspectiveCamera(),engine:{canvas:{width:1920,height:1080}}};
bridge.cameraTarget={position:new E.Vector3(),quaternion:new E.Quaternion(),scale:new E.Vector3()};
const mesh=new E.Mesh(new E.BoxGeometry(),{});mesh.matrixAutoUpdate=false;bridge.meshes.set('original CAD part',mesh);bridge.app.scene.add(mesh);
bridge._applyTransforms([['original CAD part',new E.Matrix4().makeTranslation(2,0,0).elements.map((_,i,a)=>a[(i%4)*4+Math.floor(i/4)]),'boat']]);
bridge.state={};bridge._applyBodies([['boat',[1,0,0,10,0,1,0,20,0,0,1,30,0,0,0,1]]]);
bridge.app.scene.updateMatrixWorld(true);
assert.deepEqual(mesh.matrixWorld.elements.slice(12,15),[12,20,30]);
op.mode='boat';op.boatCamera='boat_nav';
bridge._applyCamera({mode:'drone',views:{boat_nav:{matrix:[1,0,0,10,0,1,0,20,0,0,1,30,0,0,0,1],fovy:60}}},true);
assert.equal(bridge.cameraView,'boat_nav');assert.deepEqual(bridge.app.camera.position.toArray(),[10,20,30]);
console.log('Delayed telemetry, instant camera choice, independent throttle commands and CAD body poses passed');
