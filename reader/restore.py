"""Restore a package that encodes XML fields before optional earlier-page matching."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
from field_lines import convert

if __name__=="__main__":
    data,out=(Path(p).resolve() for p in sys.argv[1:])
    if out.exists(): raise FileExistsError(out)
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        fields=Path(tmp)/"fields"
        subprocess.run([sys.executable,root/"base_restore.py",data,fields],check=True)
        result=Path(tmp)/"result"
        convert(fields,result,False)
        os.replace(result,out)
