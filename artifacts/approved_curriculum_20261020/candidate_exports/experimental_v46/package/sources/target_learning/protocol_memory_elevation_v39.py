"""Remember an inspected view across track aliases, without changing identity votes."""
import math
from .protocol_elevation_v39 import SearchProtocol as Previous

class SearchProtocol(Previous):
    def __init__(self,**kw):
        super().__init__(**kw);self.visual_context={};self.own_viewpoint=None
        self.inspected_views={};self.visit_events=[]
    def observe_visual_context(self,own_position,tracks):
        self.own_viewpoint=tuple(map(float,own_position));self.visual_context=tracks
    def _remember(self,now):
        for key in self.rejected:
            if key in self.inspected_views:continue
            context=self.visual_context.get(key,{})
            interval=context.get('range_interval')
            self.inspected_views[key]=dict(point=context.get('point'),appearance=context.get('appearance'),
                own=self.own_viewpoint,reason=self.cooldown_reasons.get(key,'unresolved_inspection'),
                first_rejected_s=now,radius=min(1.5,max(.75,(interval[1]-interval[0])*.5))if interval else .75)
        if len(self.inspected_views)>256:self.search_exhausted=True
    def _same_view(self,record,context):
        if record['point']is None or context.get('point')is None or record['appearance']is None or context.get('appearance')is None:return False
        if math.dist(record['point'][:2],context['point'][:2])>record['radius']:return False
        first,second=record['appearance'],context['appearance']
        if len(first)!=len(second):return False
        distance=math.sqrt(sum(((float(x)-float(y))/31)**2 for x,y in zip(first,second))/max(1,len(first)))
        if distance>.12:return False
        wrong='wrong_design'in record['reason']
        if not wrong and record['own']is not None and self.own_viewpoint is not None and math.dist(record['own'],self.own_viewpoint)>2:return False
        return True
    def step(self,s,candidates):
        self._remember(s.time_s)
        filtered=[]
        for candidate in candidates:
            context=self.visual_context.get(candidate.track_id,{})
            positive=(candidate.age_s<=.25 and candidate.identity_observable and candidate.target_probability>=.98 and candidate.distinct_confirmations>=3)
            record=self.inspected_views.get(candidate.track_id)
            match=next((r for r in self.inspected_views.values()if self._same_view(r,context)),None)
            evidence_record=record or match
            if positive and(evidence_record is None or evidence_record['reason']!='recognizable_design_without_qualified_pad'or candidate.marker_probability>=.8):
                self.rejected.pop(candidate.track_id,None)
                self.inspected_views.pop(candidate.track_id,None)
                for old in list(self.inspected_views):
                    if self._same_view(self.inspected_views[old],context):self.inspected_views.pop(old)
                filtered.append(candidate);continue
            if record is not None and 'wrong_design'not in record['reason'] and record['own']is not None and self.own_viewpoint is not None and math.dist(record['own'],self.own_viewpoint)>2:
                self.inspected_views.pop(candidate.track_id,None);self.rejected.pop(candidate.track_id,None);record=None
            sticky=record is not None and(record['own']is None or self.own_viewpoint is None or
                'wrong_design'in record['reason']or math.dist(record['own'],self.own_viewpoint)<=2)
            suppress=bool(sticky or match is not None)
            if suppress and not(self.overflight is not None and self.selected==candidate.track_id):
                self.rejected[candidate.track_id]=s.time_s
                self.cooldown_reasons[candidate.track_id]='unchanged_inspected_view_no_new_evidence'
                if candidate.track_id not in self.inspected_views:
                    self.visit_events.append(dict(time_s=s.time_s,track_id=candidate.track_id,event='new_visual_track_same_inspected_view',identity_votes_changed=False))
                continue
            filtered.append(candidate)
        intent=super().step(s,filtered);self._remember(s.time_s)
        return intent
