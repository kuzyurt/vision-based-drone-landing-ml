from pathlib import Path
R=Path(__file__).parent;p=R/'test_survey_v51.py';s=p.read_text().replace('35.if keep else0.','35. if keep else 0.');compile(s,str(p),'exec');p.write_text(s)
