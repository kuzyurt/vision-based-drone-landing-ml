"""Compact figures from saved traces; render on the VM only."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent


def main():
    audit=json.loads((ROOT/'audit.json').read_text())
    failed=[c for c in audit['cases'] if c['outcome']!='landed']
    fig,axes=plt.subplots(5,2,figsize=(15,18),layout='constrained')
    for row,case in enumerate(failed):
        data=json.loads((ROOT/(case['name']+'_series.json')).read_text())
        t=np.array([d['t'] for d in data]);drone=np.array([d['drone_xy'] for d in data]);boat=np.array([d['boat_xy'] for d in data])
        origin=drone[0];ax=axes[row,0]
        ax.plot(*(drone-origin).T,color='#bc7b12',label='Drone, recorded truth')
        ax.plot(*(boat-origin).T,color='#087f8c',label='Boat, recorded truth')
        ax.scatter(*(drone[0]-origin),color='#bc7b12',marker='o');ax.scatter(*(boat[0]-origin),color='#087f8c',marker='o')
        ax.scatter(*(drone[-1]-origin),color='#bc7b12',marker='x');ax.scatter(*(boat[-1]-origin),color='#087f8c',marker='x')
        ax.set(title=case['name'],xlabel='East from initial drone position (m)',ylabel='North (m)',aspect='equal');ax.grid(alpha=.2)
        if row==0:ax.legend(fontsize=9)
        ax=axes[row,1]
        ax.plot(t,[d['dist'] for d in data],color='#283c65',label='True horizontal boat distance')
        estimated=[np.linalg.norm(d['est_rel'][:2]) if d['est_rel'] is not None else np.nan for d in data]
        ax.plot(t,estimated,color='#cc5d2d',label='Controller estimated horizontal distance')
        accepted=np.array([d['metric'] for d in data])
        if accepted.any():ax.scatter(t[accepted],np.array([d['dist'] for d in data])[accepted],s=4,color='#199258',label='Accepted metric pose')
        first=case['first_metric_s']
        if first is not None:ax.axvline(first,color='#199258',ls='--',alpha=.6)
        ax.set(xlabel='Task time (s)',ylabel='Horizontal distance (m)',xlim=(0,180));ax.grid(alpha=.2)
        if row==0:ax.legend(fontsize=8)
    fig.suptitle('Five original failures: 3D acquisition and tracking audit\nExisting traces only; truth is used for diagnosis, never policy input',fontsize=16)
    fig.savefig(ROOT/'failure_paths_and_tracking.png',dpi=140);plt.close(fig)


if __name__=='__main__':main()
