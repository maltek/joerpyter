import argparse
import json
import os
import sys
import shutil

from jupyter_client.kernelspec import KernelSpecManager
from tempfile import TemporaryDirectory

def kernel_json(name, binary):
    return {
        "argv": [sys.executable, "-m", "joern_kernel", "-f", "{connection_file}"],
        "display_name": name,
        "language": "scala",
        "env": {
            "JOERPYTER_NAME": name,
            "JOERPYTER_BINARY": binary,
        },
    }


def install_my_kernel_spec(user=True, prefix=None):
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755) # Starts off as 700, not user readable
        # requires logo files in kernel root directory
        cur_path = os.path.dirname(os.path.realpath(__file__))
        for logo in ["logo-32x32.png", "logo-64x64.png"]:
            try:
                shutil.copy(os.path.join(cur_path, logo), td)
            except FileNotFoundError:
                print("Custom logo files not found. Default logos will be used.")
        
        for name, binary in (('Joern', "joern"), ('Ocular', 'ocular.sh')):
            print(f'Installing Jupyter kernel spec for {name}')
            with open(os.path.join(td, 'kernel.json'), 'w') as f:
                json.dump(kernel_json(name, binary), f, sort_keys=True)
            KernelSpecManager().install_kernel_spec(td, name, user=user, prefix=prefix)


def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False # assume not an admin on non-Unix platforms

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', action='store_true',
        help="Install to the per-user kernels registry. Default if not root.")
    ap.add_argument('--sys-prefix', action='store_true',
        help="Install to sys.prefix (e.g. a virtualenv or conda env)")
    ap.add_argument('--prefix',
        help="Install to the given prefix. "
             "Kernelspec will be installed in {PREFIX}/share/jupyter/kernels/")
    args = ap.parse_args(argv)

    if args.sys_prefix:
        args.prefix = sys.prefix
    if not args.prefix and not _is_root():
        args.user = True

    install_my_kernel_spec(user=args.user, prefix=args.prefix)

if __name__ == '__main__':
    main()
