install:

- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- `python -m joern_kernel.install`

usage:

- ensure `joern` is in your PATH
- `jupyter console --kernel joern`
