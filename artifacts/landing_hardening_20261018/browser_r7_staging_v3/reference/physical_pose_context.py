"""Reject visual fits contradicting an already declared coarse deck datum.

This is a broad plausibility veto, never a measurement of dynamic boat height.
The mission uncertainty is deliberately multiplied by3; it is not treated as a
certified statistical interval. Pixel/paint/conditioning and touchdown gates
remain mandatory after this additional check.
"""
import math
import numpy as np
from .persistent_target import own_state

def fit_height_context(fit,capture):
 if fit is None:return dict(available=False,compatible=True,reason='no_fit')
 mission=capture.get('mission',{});keys=['water_datum_enu_m','nominal_deck_height_above_water_m','coarse_height_uncertainty_m']
 if not all(key in mission for key in keys):return dict(available=False,compatible=True,reason='declared_prior_unavailable')
 try:water,deck,uncertainty=[float(mission[key]) for key in keys]
 except (TypeError,ValueError):return dict(available=False,compatible=False,reason='invalid_declared_prior')
 if not all(math.isfinite(x) for x in [water,deck,uncertainty]) or uncertainty<=0:return dict(available=False,compatible=False,reason='invalid_declared_prior')
 own=own_state(capture);r=np.asarray(fit['relative_position'],dtype=float)
 if own is None or r.shape!=(3,) or not np.isfinite(r).all():return dict(available=False,compatible=False,reason='own_estimate_or_visual_fit_invalid')
 inferred=float(own[0][2]-r[2]);nominal=water+deck;bound=3.*uncertainty;residual=inferred-nominal
 return dict(available=True,compatible=abs(residual)<=bound,reason='declared_deck_height_compatible' if abs(residual)<=bound else 'inconsistent_declared_deck_height',
  inferred_height_enu_m=inferred,declared_nominal_height_enu_m=nominal,residual_m=residual,permitted_deviation_m=bound,
  source='RGB registration +own altitude compared with declared sea datum/static deck-height prior; no dynamic boat state')
