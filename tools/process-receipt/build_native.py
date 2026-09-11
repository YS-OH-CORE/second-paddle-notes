"""Build in a disposable environment, then verify a fresh offline installation."""
from pathlib import Path
import os
import subprocess
import sys
import venv


def main():
    root = Path(os.environ['RUNNER_TEMP'])/'process-native-build'
    root.mkdir(exist_ok=False)
    env = root/'builder'
    venv.EnvBuilder(with_pip=True).create(env)
    py = env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    package = Path(__file__).resolve().parent
    subprocess.run([str(py),'-m','pip','--disable-pip-version-check','install','setuptools==82.0.1'],
                   check=True,timeout=120)
    dist = root/'dist'
    subprocess.run([str(py),'-m','pip','--disable-pip-version-check','wheel','--no-index',
        '--no-deps','--no-build-isolation','--wheel-dir',str(dist),str(package)],check=True,timeout=90)
    wheels = list(dist.glob('*.whl'))
    if len(wheels)!=1:
        raise RuntimeError('Expected exactly one built wheel')
    subprocess.run([sys.executable,str(package/'verify_portable_install.py'),'--wheel',str(wheels[0]),
                    '--out',str(root/'installation')],check=True,timeout=160)


if __name__=='__main__':
    main()
