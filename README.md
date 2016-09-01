Python OParl client library
===========================
This package provides tools for easily retrieving information from an
[OParl][oparl] server. OParl is a standard interface for publishing information
about parliaments and their work.

[oparl]: https://oparl.org


Installation
------------
We recommend to install the library in a [virtualenv][virtualenv]:

    virtualenv venv
    source venv/bin/activate

Then:

    pip install -e git+https://github.com/stadt-karlsruhe/python-oparl#egg=oparl


[virtualenv]: https://virtualenv.pypa.io/en/stable/


Usage
-----
The main tool of the library is the `Object` class and its subclasses. They
provide wrappers for the various OParl classes (`Body`, `Person`, ...) and
support lazy loading and automatic conversion of OParl data types (e.g.
`date-time`) to Python types (`datetime.datetime`).

You will typically start by loading a single object from an OParl server
using the `from_id` function:

    import oparl
    system = oparl.from_id('https://politik-bei-uns.de/oparl')

If you've already got OParl JSON data you can also use `from_json`.

Instances of `Object` and its subclasses support a read-only dict-interface:

    for body in system['body']:
        print(body['name'])

This library tries to be as compatible with OParl 1.0 as possible but does not
enforce strict compliance. In some cases non-compliant server behavior that has
been seen "in the wild" is supported. These cases trigger a
`SpecificationWarning`.

By default, HTTPS certificates are verified. You can disable that verification
by setting `VERIFY_HTTPS` to `False`.

The library's logger (`log`) doesn't have a handler attached to it by default,
but may come in handy during development.


License
-------
Copyright (c) 2016, Stadt Karlsruhe (www.karlsruhe.de)

Distributed under the MIT license, see the file `LICENSE` for details.

