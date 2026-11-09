"""Display the actual policy RGB input beside the actual simulation overview."""
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def install():
    import landing_training.rendering as rendering
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',19)
    title=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',25)
    def compose(self,external,onboard,row):
        canvas=Image.new('RGB',(1280,720),(15,21,30));draw=ImageDraw.Draw(canvas)
        canvas.paste(Image.fromarray(external).resize((640,360)),(0,60));canvas.paste(Image.fromarray(onboard),(640,60))
        draw.text((20,13),'LIVE ML POLICY RUN | NO BOAT RADIO | ACTUAL SIMULATION CAMERAS',font=title,fill='#ffffff')
        draw.rectangle((0,60,640,91),fill='#172332');draw.text((12,64),'OVERVIEW',font=font,fill='#b6dfff')
        draw.rectangle((640,60,1280,91),fill='#172332');draw.text((650,64),'ACTUAL RGB INPUT TO POLICY',font=font,fill='#b6dfff')
        o=row['observation'];d=row['output'].get('learner_diagnostics') or {};a=row['output']['executed_action'];p=row['privileged']
        distance=np.linalg.norm(np.asarray(p['drone_position_enu_m'])[:2]-np.asarray(p['pad_position_enu_m'])[:2])
        lines=[f"Flight {row['task_time_s']:.1f} s | phase: {d.get('control_phase',row['phase'])} | {row['outcome']}",
               f"Armed: {o['px4']['armed']} | accepted visual pose: {d.get('metric_valid',False)} | radio input: ABSENT",
               f"Forward / right / down: {a[0]:+.2f} / {a[1]:+.2f} / {a[2]:+.2f} m/s",
               f"Boat distance: {distance:.2f} m | vertical deck clearance: {p['vertical_clearance_m']:.2f} m (evaluation only)",
               f"Boat speed: {self.env.scenario.boat_speed:.2f} m/s | wind: {self.env.scenario.wind_profile}",
               'Learned perception + geometric visual registration / controller + native PX4',
               'Expert used only for airborne preparation before this recorded policy task.']
        for i,line in enumerate(lines):draw.text((20,449+34*i),line,font=font,fill='#dce5ef')
        return np.asarray(canvas)
    rendering.ReviewRenderer.compose=compose
