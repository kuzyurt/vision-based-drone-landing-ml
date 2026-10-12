"""Export pinned NumPy 2.2.6 Ziggurat constants and RNG validation vectors."""
from pathlib import Path
import json,re,hashlib,urllib.request
import numpy as np

root=Path(__file__).resolve().parent
url='https://raw.githubusercontent.com/numpy/numpy/v2.2.6/numpy/random/src/distributions/ziggurat_constants.h'
data=urllib.request.urlopen(url).read();text=data.decode()
arrays={}
for name in ['ki_double','wi_double','fi_double']:
    body=re.search(r'\b'+name+r'\s*\[\s*\]\s*=\s*\{(.*?)\}',text,re.S).group(1)
    tokens=[token.strip() for token in body.split(',') if token.strip()]
    arrays[name]=[int(re.sub(r'[uUlL]+$','',token),0) if name=='ki_double' else float(token) for token in tokens]
for name in ['ziggurat_nor_r','ziggurat_nor_inv_r']:
    arrays[name]=float(re.search(r'\b'+name+r'\s*=\s*([^;]+)',text).group(1))
out=root.parent/'app/src/landing/NoiseTables.js'
out.write_text('// NumPy 2.2.6 Ziggurat constants; BSD-3-Clause. See wasm/NOTICE.md.\n'
    '// Source SHA256: '+hashlib.sha256(data).hexdigest()+'\nexport default '+json.dumps(arrays,separators=(',',':'))+';\n')
state=np.random.PCG64(714).state['state']
vectors={'state':str(state['state']),'increment':str(state['inc']),
    'uint64':[str(value) for value in np.random.PCG64(714).random_raw(100)],
    'normal':np.random.default_rng(714).standard_normal(20000).tolist()}
(root/'tests/noise-vectors.json').write_text(json.dumps(vectors,separators=(',',':')))
print(out)
