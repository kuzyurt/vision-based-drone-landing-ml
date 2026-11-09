from pathlib import Path
R=Path(__file__).parent
s=(R/'test_takeover_v46.py').read_text().replace('search_v46','search_v48').replace('takeover_v46','takeover_v48').replace('unverified_descent_v43','unverified_descent_v48').replace('dagger_v46','dagger_v48').replace('collection_v46','collection_v48')
s=s.replace("{'metric_confirmed':False},obs", "{'metric_confirmed':confirmed,'expert_intent':{'allow_descent':confirmed}},obs")
s=s.replace("confirmed=kind=='confirmed'", "confirmed=kind in ['confirmed','identity_without_landing_permission']")
s=s.replace("'allow_descent':confirmed", "'allow_descent':kind=='confirmed'")
s=s.replace("['descent','confirmed','hover','ascending','repeat']", "['descent','confirmed','identity_without_landing_permission','hover','ascending','repeat']")
s=s.replace("assert results['descent']and results['descent'][0]>=5.3", "assert results['descent']and results['descent'][0]>=5.3\nassert results['identity_without_landing_permission']and results['identity_without_landing_permission'][0]>=5.3")
(R/'test_takeover_v48.py').write_text(s)
