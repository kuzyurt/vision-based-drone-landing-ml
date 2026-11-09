import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {velocityPacket,estimatorObservation} from '../src/landing/PolicyTelemetry.js';
const fixture=JSON.parse(await fs.readFile(new URL('../../simulation/runtime/ml-fixtures/transport.json',import.meta.url)));
for(const f of fixture)assert.deepEqual(Array.from(velocityPacket(f.action,f.yaw,f.time,f.sequence)),f.packet);
const o=new Float64Array(20);o.set([1,2,3,-4,5,6,-7,Math.cos(.6),0,0,Math.sin(.6),1,0,2000000,2004000,14,.1,.2,.3,2004000]);
const state=estimatorObservation({observation:()=>o,originENU:[10,20,30],lastSensor:2008000,armed:true,landed:false});
assert.deepEqual(state.position_enu_m,[13,22,34]);assert.deepEqual(state.velocity_enu_m_s,[6,5,7]);assert(Math.abs(state.attitude_ned_rad[2]-1.2)<1e-12);assert.deepEqual(state.angular_rate_frd_rad_s,[.1,.2,.3]);assert.equal(state.position_age_s,.008);assert.equal(state.attitude_age_s,.004);
console.log('Velocity commands match pymavlink packets byte for byte; estimator ENU, NED attitude and angular-rate contract verified.');
