# Poliscoops



## Table of contents

 - [Important links](#important-links)
 - [Bugs and feature requests](#bugs-and-feature-requests)
 - [Install](https://github.com/openstate/poliscoops/blob/master/INSTALL.rst)
 - [Install and usage](#install-and-usage)
 - [Documentation](#documentation)
 - [Contributing](#contributing)
 - [Authors and contributors](#authors-and-contributors)
 - [Copyright and license](#copyright-and-license)

## Important links
 - [Poliscoops homepage](https://poliscoops.eu/)
 - [Official source code repo](https://github.com/openstate/poliscoops/)
 - [Documentation](http://docs.poliscoops.eu/)
 - [Issue tracker](https://github.com/openstate/poliscoops/issues)

## Bugs and feature requests

Have a bug or a feature request? Please first read the [issue guidelines](https://github.com/openstate/poliscoops/blob/master/docs/dev/getting_started.rst) and search for existing and closed issues. If your problem or idea is not addressed yet, [please open a new issue](https://github.com/openstate/poliscoops/issues/new).

## Install and usage

See this guide to [install the Poliscoops API](https://github.com/openstate/poliscoops/blob/master/INSTALL.rst) using Docker. There are also a few usage commands to get you started.

## Removing items

in the `pfl_backend_1 container`: `curl -XDELETE 'http://elasticsearch:9200/pfl_combined_index_fixed/item/60f7e58767aec51e657ae6848ed15c1c36fe8185'`
## Documentation

The documentation of the Poliscoops API can be found at [docs.poliscoops.eu](http://docs.poliscoops.eu/).

We use [Sphinx](http://sphinx-doc.org/) to create the documentation. The source files are included in this repo under the `docs` directory.  

## Contributing

Please read through our [contributing guidelines](https://github.com/openstate/poliscoops/blob/master/docs/dev/getting_started.rst). Included are directions for opening issues, coding standards, and notes on development.

## Authors and contributors

The Poliscoops API is based on the [Open Raadsinformatie API](https://github.com/openstate/open-raadsinformatie/). Authors and contributors of both projects are:

Authors:

* Bart de Goede ([@bartdegoede](https://twitter.com/bartdegoede))
* Justin van Wees ([@justin_v_w](https://twitter.com/justin_v_w))
* Breyten Ernsting ([@breyten](https://twitter.com/breyten))
* Sicco van Sas([@siccovansas](https://twitter.com/siccovansas))

Contributors:

* [DutchCoders](http://dutchcoders.io/)
* [Benno Kruit](https://github.com/bennokr)

## Copyright and license

The Poliscoops API is distributed under the [GNU Lesser General Public License v3](https://www.gnu.org/licenses/lgpl.html). The documentation is released under the [Creative Commons Attribution 4.0 International license](http://creativecommons.org/licenses/by/4.0/).
