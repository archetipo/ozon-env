# ozon-env

<h2 align="center">The Uncompromising Code Formatter</h2>

<p align="center">
<a href="hhttps://github.com/archetipo/ozon-env/actions"><img alt="Actions Status" src="https://github.com/psf/black/workflows/Test/badge.svg"></a>
<a href="https://github.com/archetipo/ozon-env?branch=main"><img alt="Coverage Status" src="https://coveralls.io/repos/github/psf/black/badge.svg?branch=main"></a>
<a href="https://github.com/archetipo/ozon-env/blob/main/LICENSE"><img alt="License: MIT" src="https://black.readthedocs.io/en/stable/_static/license.svg"></a>
<a href="https://github.com/archetipo/ozon-env"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

ozon-env lib is a api system to interact with Service App project

For information about the Service App project,
see https://github.com/INRIM/service-app

## Installation

The source code is currently hosted on GitHub at:
https://github.com/archetipo/ozon-env

### PyPI - Python Package Index

Binary installers for the latest released version are available at the [Python
Package Index](https://pypi.python.org/pypi/ozon-env)

```sh
pip(3) install ozon-env
```

```sh
poetry install --without dev
```

or

### Source Install with Poetry (recommended)

Convenient for developers. Also useful for running the (unit)tests.

```sh
git clone https://github.com/archetipo/ozon-env.git
```

add virtualenv **env** Pytnon >=3.10

```
pip install poetry
poetry install
```

### Source Install with pip

Optional dependencies need to be installed separately.

```sh
pip(3) install git+https://github.com/archetipo/ozon-env
```

### Tests Coverage and Code style

```
./run_test.sh
```

## License

[MIT](LICENSE)

## Contributing

All contributions, bug reports, bug fixes, documentation improvements,
enhancements and ideas are welcome.