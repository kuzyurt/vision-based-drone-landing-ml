from pathlib import Path
R=Path(__file__).parent
s=(R/'download_restore_v39.py').read_text().replace('experimental_v39','experimental_v46');(R/'download_restore_v46.py').write_text(s)
