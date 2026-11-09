"""Explicit observable-teacher proposals; no fallback to legacy or executed actions.

These labels can support a separately specified action learner. They do not train
an explicit hybrid controller just by being recorded. Perception losses have
their own capture-time visibility masks and do not consume these action vectors.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class TrainingAuthorization:
    episode_training_eligible:bool=False
    human_review_receipt_verified:bool=False
    teacher_source_receipt_verified:bool=False
    autonomous_visual_review_receipt_verified:bool=False


def teacher_proposal_for_audit(row):
    o=row['observation'];out=row['output'];d=out.get('learner_diagnostics')or{};p=o['px4'];dd=d.get('dagger');reasons=[]
    if dd is not None:
        action=dd.get('expert_bounded_action');source='same_observation_dagger_shadow_expert';intent=d.get('expert_shadow_intent',{})
        if not dd.get('expert_label_valid',False):reasons.append('shadow_teacher_marked_invalid')
        if dd.get('ownership',{}).get('owner')not in ['policy','expert','expert_prefix']:reasons.append('safety_or_fallback_owner')
    elif d.get('expert_source')=='RGB/own telemetry/encoders/declared static priors only'and 'expert_intent'in d:
        action=out.get('learner_action');source='observable_expert_review_harness_proposal';intent=d['expert_intent']
    else:
        action=None;source=None;intent={};reasons.append('no_declared_observable_teacher')
    a=np.asarray(action,dtype=float)if action is not None else np.array([])
    if a.shape!=(6,)or not np.isfinite(a).all():reasons.append('no_finite_teacher_vector')
    if row.get('terminal')or p.get('landed')or not p.get('armed'):reasons.append('terminal_or_not_airborne')
    if not o.get('image_valid')or o.get('image_age_s',99)>.25:reasons.append('image_unavailable_or_stale')
    if not p.get('valid')or p.get('position_age_s',99)>.25 or p.get('attitude_age_s',99)>.25:reasons.append('own_state_unavailable_or_stale')
    if out.get('intervention')is not None or d.get('expert_intervention')is not None:reasons.append('supervision_intervened')
    if d.get('mission_fallback_active'):reasons.append('mission_fallback')
    if d.get('evaluation_fault_active')or d.get('actual_command_owner')=='evaluation_fault':reasons.append('injected_fault')
    if a.shape==(6,)and a[2]>.02 and not intent.get('allow_descent',False):reasons.append('teacher_descent_not_authorized_by_visual_protocol')
    return dict(candidate_teacher_proposal=a.tolist()if a.shape==(6,)and np.isfinite(a).all()else None,
        source=source,candidate_valid=not reasons,exclusion_reasons=reasons,
        executed_action_is_not_a_teacher_label=True,legacy_expert_fields_ignored=True,grants_training_eligibility=False)


def action_training_target(row,authorization):
    review_verified=(authorization.human_review_receipt_verified or authorization.autonomous_visual_review_receipt_verified)
    if not(authorization.episode_training_eligible and review_verified and authorization.teacher_source_receipt_verified):
        raise PermissionError('New eligible episode and verified visual-review/source receipts required; never train review recordings')
    label=teacher_proposal_for_audit(row)
    # None means mask the action loss. Never fabricate zero teacher targets.
    return label['candidate_teacher_proposal']if label['candidate_valid']else None
