"""AIR2216II KV920 / T1045II bench-data scenario, not an identified vehicle.

16 V manufacturer points; under-30% behavior, dynamic response, drag and sag
remain explicit calibration assumptions. Current limit applies to the pack.
"""
import numpy as np
G=9.80665
THROTTLE=np.array([0,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100])*0.01
THRUST=np.array([0,210,259,309,373,447,536,628,729,814,906,993,1087,1191,1289,1332])*G/1000
TORQUE=np.array([0,.03,.04,.05,.05,.06,.08,.09,.10,.11,.12,.14,.15,.16,.18,.18])
CURRENT=np.array([0,1.44,1.87,2.29,2.86,3.60,4.53,5.61,6.78,7.92,9.20,10.59,12.11,13.81,15.68,16.37])
RPM=np.array([0,4042,4469,4855,5301,5780,6298,6800,7281,7679,8096,8468,8867,9257,9675,9857])
OMEGA=RPM*2*np.pi/60
_curve_x=THROTTLE[1:]**2-THROTTLE[1:]
THRUST_MODEL_FACTOR=float(np.clip(np.dot(_curve_x,THRUST[1:]/THRUST[-1]-THROTTLE[1:])/np.dot(_curve_x,_curve_x),0,1))
class Propulsion:
    def __init__(self):
        self.charge_Ah=12.;self.voltage=16.8
        self.current=0.;self.limited=False
        # Manufacturer's supplied PM06 wiring is 30 A continuous; pack 36 A.
        self.continuous_current_A=30.
        self.motor_time_constant_s=.080
        self.drive_torque_limit_Nm=float(TORQUE.max()) # conservative bench envelope; stall limit unmeasured
        self.internal_resistance_ohm=.030 # Unmeasured pack scenario.
    def targets(self,commands):
        commands=np.clip(commands,0,1)
        if not self.charge_Ah:
            self.limited=False
            return np.zeros_like(commands)
        ocv=13.2+3.6*np.clip(self.charge_Ah/12,0,1)
        voltage=max(12.,ocv-self.current*self.internal_resistance_ohm)
        # Bound modeled sustained prop load at the maker's 1.2 kgf limit.
        max_omega=np.interp(1.2*G,THRUST,OMEGA)
        targets=np.minimum(np.interp(commands,THROTTLE,OMEGA)*voltage/16,max_omega)
        predicted_current=np.interp(targets,OMEGA,CURRENT).sum()
        self.limited=bool(predicted_current>self.continuous_current_A)
        if self.limited:
            # Monotonic shared electrical budget, not four independent caps.
            lo,hi=0.,1.
            for _ in range(20):
                scale=(lo+hi)/2
                if np.interp(targets*scale,OMEGA,CURRENT).sum()>self.continuous_current_A:hi=scale
                else:lo=scale
            targets*=lo
        return targets
    def update_electrical(self,omega,drive_targets,dt,axial_m_s=None,rotor_radius_m=None,density=1.225):
        """Meter the motors that actually spun during this physics step.

        The manufacturer's 16 V bench current is indexed by measured rotor RPM.
        A motor with its drive disabled draws no propulsion current while it
        coasts or windmills. Auxiliary electronics have no identified power
        figure and are deliberately excluded.
        """
        driven=np.asarray(drive_targets)>0
        speed=np.abs(omega)
        rpm_current=np.interp(speed,OMEGA,CURRENT)
        if axial_m_s is not None:
            if rotor_radius_m is None:raise ValueError('Rotor radius is required for axial-flow power')
            # Ideal actuator-disk power change at a fixed thrust. The bench
            # torque/current ratio gives the motor's observed shaft-to-input
            # efficiency at each RPM; blade profile power remains in the
            # measured baseline. Shallow descent only: vortex-ring behavior
            # cannot be predicted by this ideal-flow equation.
            thrust,bench_torque=self.loads(omega)
            hover_vi=np.sqrt(thrust/(2*density*np.pi*np.asarray(rotor_radius_m)**2))
            axial=np.asarray(axial_m_s)
            disk_flow=axial/2+np.sqrt(hover_vi**2+(axial/2)**2)
            delta_power=thrust*(disk_flow-hover_vi)
            shaft_efficiency=np.divide(bench_torque*speed,16*rpm_current,out=np.ones_like(speed),where=rpm_current>0)
            correction=np.divide(delta_power,self.voltage*shaft_efficiency,out=np.zeros_like(speed),where=(speed>=OMEGA[1])&(shaft_efficiency>0))
            rpm_current=np.maximum(0,rpm_current+correction)
        self.current=float(np.sum(np.where(driven,rpm_current,0.)))
        ocv=13.2+3.6*np.clip(self.charge_Ah/12,0,1)
        self.voltage=float(max(12.,ocv-self.current*self.internal_resistance_ohm))
        self.charge_Ah=max(0.,self.charge_Ah-self.current*dt/3600)
    def loads(self,omega):
        speed=np.abs(omega)
        thrust=np.interp(speed,OMEGA,THRUST);torque=np.interp(speed,OMEGA,TORQUE)
        low=speed<OMEGA[1]
        # A static propeller's air load tends to zero quadratically with RPM.
        # Low-throttle ESC/RPM mapping itself remains unmeasured.
        thrust[low]=THRUST[1]*(speed[low]/OMEGA[1])**2
        torque[low]=TORQUE[1]*(speed[low]/OMEGA[1])**2
        return thrust,torque
