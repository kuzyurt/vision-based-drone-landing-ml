from pathlib import Path
p=Path(__file__).parent;s=(p/'render_static_repair_v44.py').read_text().replace('static_repair_v44','static_repair_v44b')
s=s.replace('math.atan2(point[1]-xy[1],point[0]-xy[0])-math.atan2(ray[1],ray[0])','math.atan2(point[1]-xy[1],point[0]-xy[0])+(math.pi if name==\'background\'else 0.)-math.atan2(ray[1],ray[0])')
(p/'render_static_repair_v44b.py').write_text(s)
for n in ['queue','launch']:(p/(n+'_static_repair_v44b.py')).write_text((p/(n+'_static_repair_v44.py')).read_text().replace('static_repair_v44','static_repair_v44b'))
for n in ['render_static_repair_v44b.py','queue_static_repair_v44b.py','launch_static_repair_v44b.py']:compile((p/n).read_text(),n,'exec')
