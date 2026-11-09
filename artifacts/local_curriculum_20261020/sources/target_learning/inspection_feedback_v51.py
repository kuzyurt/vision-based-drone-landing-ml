"""Honor the existing full-survey transition after rejected stale-ray inspection."""
from .inspection_feedback_v25 import InspectionFeedback as Previous
class InspectionFeedback(Previous):
    def observe(self,protocol,state,candidates,**kwargs):
        info=super().observe(protocol,state,candidates,**kwargs)
        if info.get('retired')and not info.get('completed_scan_retained')and getattr(protocol,'scan_completed',False):
            previous=protocol.scan_band
            protocol._new_survey('completed_survey_inspection_finished_new_elevation')
            info.update(actual_completed_survey_transition=True,previous_band=previous,next_band=protocol.scan_band)
        return info
