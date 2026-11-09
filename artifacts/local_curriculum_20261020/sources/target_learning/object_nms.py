"""Object-level suppression for duplicate dense-grid boat detections."""
import math

def box(p):
    x,y=p['pixel'];w,h=p['size_px'];return x-w/2,y-h/2,x+w/2,y+h/2

def iou(a,b):
    a=box(a);b=box(b)
    intersection=max(0.,min(a[2],b[2])-max(a[0],b[0]))*max(0.,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0.

def suppress(predictions,threshold=.4):
    output=[]
    for p in sorted(predictions,key=lambda p:p['presence'],reverse=True):
        if not all(math.isfinite(float(v))for v in [*p['pixel'],*p['size_px'],p['presence']]):continue
        if min(p['size_px'])<=0:continue
        if any(q['boat']==p['boat']and iou(p,q)>=threshold for q in output):continue
        output.append(p)
    return output
