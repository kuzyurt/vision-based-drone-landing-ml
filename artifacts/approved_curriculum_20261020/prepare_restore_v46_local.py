from pathlib import Path
R=Path(__file__).parent;s=(R/'restore_windows_v39.py').read_text().replace('experimental_v39','experimental_v46').replace('BUILD_RECEIPT.json','BUILD_RECEIPT_V46.json').replace('LOCAL_WINDOWS_RESTORE_VERIFIED.json','LOCAL_WINDOWS_RESTORE_VERIFIED_V46.json');(R/'restore_windows_v46.py').write_text(s)
