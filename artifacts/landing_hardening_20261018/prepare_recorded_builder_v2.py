from pathlib import Path
r=Path(__file__).resolve().parent
s=(r/'continue_combined_r14.py').read_text()
s=s.replace("STATE=ROOT/'combined_r14_builder_state.json'","STATE=ROOT/'combined_r14_builder_v2_state.json'")
s=s.replace("(ROOT/'r14_pipeline_receipt.json')","(ROOT/'r14_pipeline_v2_receipt.json')")
a="    template=template.replace(a,b)"
b=a+"\n    flag=\"'--full-budget','--mission-safety','--qualification'\"\n    assert flag in template\n    template=template.replace(flag,\"'--full-budget','--mission-safety','--qualification','--record-all-rgb'\")"
assert s.count(a)==1;s=s.replace(a,b)
(r/'continue_combined_r14_v2.py').write_text(s)
