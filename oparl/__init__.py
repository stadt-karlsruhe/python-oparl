#!/usr/bin/env python
# encoding: utf-8

# Copyright (c) 2016, Stadt Karlsruhe (www.karlsruhe.de)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
OParl client library.

This package provides tools for easily retrieving information from an
OParl_ server. OParl is a standard interface for publishing information
about parliaments and their work.

.. _OParl: https://oparl.org

The main tool of the library is the ``Object`` class and its subclasses.
They provide wrappers for the various OParl classes (``Body``,
``Person``, ...) and support lazy loading and automatic conversion of
OParl data types (e.g. ``date-time``) to Python types
(``datetime.datetime``).

You will typically start by loading a single object from an OParl server
using the ``from_id`` function::

    import oparl
    system = oparl.from_id('https://politik-bei-uns.de/oparl')

If you've already got OParl JSON data you can also use ``from_json``.

Instances of ``Object`` and its subclasses support a read-only dict-
interface::

    for body in system['body']:
        print(body['name'])

This library tries to be as compatible with OParl 1.0 as possible but
does not enforce strict compliance. In some cases non-compliant server
behavior that has been seen "in the wild" is supported. These cases
trigger a ``SpecificationWarning``. If invalid values are encountered
during auto-conversion (e.g. illegal date strings) then a
``ContentWarning`` is issued and conversion is skipped.

By default, HTTPS certificates are verified. You can disable that
verification by setting ``VERIFY_HTTPS`` to ``False``.

The libraries logger (``log``) doesn't have a handler attached to it by
default, but may come in handy during development.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import json
import logging
import sys
from warnings import warn

import dateutil.parser
import requests
import six
from unidecode import unidecode


log = logging.getLogger(__name__)


__version__ = '0.1.1'


# Official OParl 1.0 schema URI
SCHEMA_URI = 'https://schema.oparl.org/1.0'

# Should HTTPS certificates be verified?
VERIFY_HTTPS = True


class Warning(UserWarning):
    '''
    Base class for OParl warnings.
    '''
    pass


class SpecificationWarning(Warning):
    '''
    Warning that something did not comply with the OParl specification.
    '''
    pass


class ContentWarning(Warning):
    '''
    Warning that some content was malformed.

    This occurs, for example, if a date string does not contain a valid
    date.
    '''
    pass


def _class_from_type_uri(uri):
    '''
    Convert a type URI to a class.
    '''
    parts = uri.rsplit('/', 1)
    if len(parts) != 2:
        raise ValueError('Invalid type URI "{uri}".'.format(uri=uri))
    if parts[0] != SCHEMA_URI:
        warn(('Invalid schema URI "{schema_uri}" in type URI "{type_uri}" '
             + '(should be "{oparl_uri}").').format(schema_uri=parts[0],
             type_uri=uri, oparl_uri=SCHEMA_URI), SpecificationWarning)
    import oparl.objects
    try:
        return getattr(sys.modules['oparl.objects'], parts[1])
    except AttributeError:
        raise ValueError('Unknown type "{name}" in type URI "{uri}".'.format(
                         name=parts[1], uri=uri))


def _get_json(url):
    '''
    Download JSON from an URL and parse it.
    '''
    log.debug('Downloading {url}'.format(url=url))
    r = requests.get(url, verify=VERIFY_HTTPS)
    r.raise_for_status()
    return r.json()


def from_json(data):
    '''
    Initialize an OParl object from JSON.

    ``data`` is raw OParl JSON data (either as a Python data
    structure or as a string).

    Returns an appropriate subclass of ``Object`` initialized using
    the given data.
    '''
    if isinstance(data, six.string_types):
        data = json.loads(data)
    if not 'id' in data:
        raise ValueError('JSON data does not have an `id` field.')
    if not 'type' in data:
        raise ValueError('JSON data does not have a `type` field.')
    cls = _class_from_type_uri(data['type'])
    obj = cls(data['id'], data['type'])
    obj._init_from_json(data)
    return obj


def from_id(id):
    '''
    Initialize an OParl object from its ID (URL).

    The object's data is downloaded and parsed. The resulting object is
    returned.
    '''
    return from_json(_get_json(id))


def _lazy(id, type):
    '''
    Create a lazy OParl object.

    The returned object doesn't contain any data (aside from the ID and
    the type). The data is downloaded once it is required
    '''
    cls = _class_from_type_uri(type)
    return cls(id, type)


def _is_url(value):
    '''
    Check if a value looks like an URL.
    '''
    return isinstance(value, six.string_types) and value.startswith('http')


class ExternalObjectList(collections.Sequence):
    '''
    (Lazy) list of OParl objects.

    OParl has "external object lists". These lists contain OParl objects
    and are accessible via URL but are not true OParl objects themselves
    (they don't have their own fields, IDs, etc.). They exist to allow
    a pagination of large lists.

    This class lazily wraps such a list. Pages are retrieved only once
    further items are requested by indexing (``my_list[34]``) or by
    iterating over the list.

    To prevent storing large lists completely in memory only the
    currently requested page is stored. Random access to the list may
    therefore lead to repeated downloads of the same page. To download
    the complete list use ``my_list = list(my_list)``.

    Using ``len`` on an instance of this class returns the currently
    known number of items in the list. This number may increase once
    more items are requested. In OParl, the only portable way to get the
    total number of available items is to download the complete list.
    This can be done by using ``my_list = list(my_list)``.

    Due to its dynamic nature, instances of this class only support non-
    negative integer indices. In particular, slicing and negative
    indices are not supported
    '''
    # The only mandatory link between sub-pages of a paginated list in
    # OParl is ``next``. While OParl offers several other such links
    # (e.g. ``last``) these are optional. Similarly, OParl doesn't
    # require the server to mention the total number of items.

    def __init__(self, url):
        self.url = url
        self._data = []
        self._current_page_index = None
        self._page_urls = [(0, url)]
        self._offset = 0
        self._len = 0

    def __len__(self):
        return self._len

    def _load_page_for_index(self, i):
        '''
        Loads the sub-page which contains an index.

        The page which contains the index ``i`` is loaded. If ``i`` is
        larger than the number of items in the list then an
        ``IndexError`` is raised.
        '''
        j = 0
        while True:
            if j == len(self._page_urls) - 1:
                if self._page_urls[j][1] is None:
                    raise IndexError()
                self._load_page(j)
            if self._page_urls[j + 1][0] > i:
                self._load_page(j)
                return
            j += 1

    def _load_page(self, page_index):
        '''
        Load a sub-page.

        Sub-pages must be loaded incrementally, i.e. page ``i`` must be
        loaded before page ``i + 1``.
        '''
        if page_index == self._current_page_index:
            return
        log.debug('Getting page {index} for list {url}'.format(
                  index=page_index, url=self.url))
        self._offset, url = self._page_urls[page_index]
        if url is None:
            raise IndexError()
        data = _get_json(url)
        self._data = [from_json(obj) for obj in data['data']]
        next_offset = self._offset + len(self._data)
        self._len = max(self._len, next_offset)
        if page_index == len(self._page_urls) - 1:
            next_url = data['links'].get('next')
            self._page_urls.append((next_offset, next_url))
        self._current_page_index = page_index

    def __getitem__(self, i):
        if not isinstance(i, int) or i < 0:
            raise IndexError('Only non-negative integer indices are '
                             + 'supported.')
        self._load_page_for_index(i)
        return self._data[i - self._offset]

    def __repr__(self):
        return unidecode('<OParl ExternalObjectList {url}>'.format(
                         url=self.url))


class Object(collections.Mapping):
    '''
    Base class for all OParl objects.

    The subclasses of this class (e.g. ``Person``) represent the various
    OParl objects. The classes are dict-like read-only wrappers around
    the objects' JSON data.

    An object can be initialized using the ``from_id`` and ``from_json``
    functions. The classes' constructors are not intended for public use.

    Non-trivial fields defined by the OParl standard (e.g. fields of
    type ``date-time``) are automatically converted to an appropriate
    Python object. Nested objects referenced via an URL are loaded
    lazily, i.e. their full data is only downloaded once it is required.
    You can check whether that has happened using the ``loaded``
    attribute and force it via the ``load`` method.
    '''
    # Fields that have type 'Date'. Their values are automatically
    # parsed from the string representation.
    _DATE_FIELDS = []

    # Fields that have type 'DateTime'. Their values are automatically
    # parsed from the string representation.
    _DATETIME_FIELDS = ['created', 'modified']

    # Fields that contain another OParl objects. The object is
    # automatically parsed from its JSON representation.
    _OBJECT_FIELDS = []

    # Fields that contain a list of other OParl objects. The objects are
    # automatically parsed from their JSON representation.
    _OBJECT_LIST_FIELDS = []

    # Fields that contain a reference (URL) to another OParl object.
    # Their value is automatically replaced by a corresponding lazy
    # OParl object. This dict maps field names to the OParl type URIs of
    # the referenced object.
    _REFERENCE_FIELDS = {}

    # Fields that contain a list of references (URLs) to other OParl
    # objects. The values in the lists are automatically replaced by
    # corresponding lazy OParl objects. This dict maps field names to
    # the OParl type URIs of the referenced objects.
    _REFERENCE_LIST_FIELDS = {}

    # Fields that contain an URL to a a list of OParl objects. Their
    # values are automatically wrapped in ``ExternalObjectList``
    # instances.
    _EXTERNAL_LIST_FIELDS = []

    def __init__(self, id, type):
        '''
        Private constructor.

        Use ``from_id`` or ``from_json`` instead.
        '''
        self._data = {'id': id, 'type': type}
        self.loaded = False

    def load(self, force=False):
        '''
        Load the object's data if it hasn't been loaded, yet.

        If ``force`` is true then the data is always downloaded.
        '''
        if self.loaded and not force:
            return
        self._init_from_json(_get_json(self._data['id']))

    def __getitem__(self, key):
        try:
            return self._data[key]
        except KeyError:
            if not self.loaded:
                self.load()
                return self._data[key]
            raise

    def __iter__(self):
        self.load()
        return self._data.__iter__()

    def __len__(self):
        self.load()
        return len(self._data)

    def _convert_value(self, field, value):
        '''
        Convert a JSON value to its proper type.

        If the field has a special type (as defined by the class'
        ``_DATE_FIELDS``, ``_DATETIME_FIELDS``, etc.) then the value is
        converted accordingly. Otherwise the value is returned
        unchanged.
        '''
        if field in self._DATE_FIELDS:
            return self._parse_date(value, field)
        if field in self._DATETIME_FIELDS:
            return self._parse_datetime(value, field)
        if field in self._OBJECT_FIELDS:
            return self._parse_object(value, field)
        if field in self._OBJECT_LIST_FIELDS:
            return self._parse_object_list(value, field)
        if field in self._REFERENCE_FIELDS:
            return self._parse_reference(value, field)
        if field in self._REFERENCE_LIST_FIELDS:
            return self._parse_reference_list(value, field)
        if field in self._EXTERNAL_LIST_FIELDS:
            return ExternalObjectList(value)
        return value

    def _ensure_list(self, value, field):
        if (not isinstance(value, collections.Sequence)
                or isinstance(value, six.string_types)):
            warn(('In object "{id}": Field "{field}" of type "{type}" must '
                 + 'contain a list, but a non-list value was found '
                 + 'instead.').format(id=self._data['id'], field=field,
                 type=self._data['type']), SpecificationWarning)
            value = [value]
        return value

    def _parse_date(self, value, field):
        try:
            return dateutil.parser.parse(value).date()
        except ValueError as e:
            warn(('In object "{id}": Field "{field}" contains an invalid '
                 + 'date string ("{value}"): {error}').format(
                 id=self._data['id'], field=field, value=value, error=e),
                 ContentWarning)
            return value

    def _parse_datetime(self, value, field):
        try:
            return dateutil.parser.parse(value)
        except ValueError as e:
            warn(('In object "{id}": Field "{field}" contains an invalid '
                 + 'date-time string ("{value}"): {error}').format(
                 id=self._data['id'], field=field, value=value, error=e),
                 ContentWarning)
            return value

    def _parse_object(self, value, field):
        if _is_url(value):
            warn(('In object "{id}": Field "{field}" of type "{type}" '
                 + 'must contain an object, but a URL ("{url}") was found '
                 + 'instead.').format(id=self._data['id'], field=field,
                 type=self._data['type'], url=value), SpecificationWarning)
            return from_id(value)
        else:
            return from_json(value)

    def _parse_object_list(self, value, field):
        values = []
        for v in self._ensure_list(value, field):
            if _is_url(v):
                warn(('In object "{id}": The list in field "{field}" of '
                     + 'type "{type}" must contain objects, but an URL '
                     + '("{url}") was found instead.').format(
                     id=self._data['id'], field=field, type=self._data['type'],
                     url=v), SpecificationWarning)
                values.append(from_id(v))
            else:
                values.append(from_json(v))
        return values

    def _parse_reference(self, value, field):
        if isinstance(value, dict):
            warn(('In object "{id}": Field "{field}" of type "{type}" '
                 + 'must contain an object reference (URL), but an object '
                 + 'was found instead.').format(id=self._data['id'],
                 field=field, type=self._data['type']), SpecificationWarning)
            return from_json(value)
        else:
            return _lazy(value, self._REFERENCE_FIELDS[field])

    def _parse_reference_list(self, value, field):
        obj_type = self._REFERENCE_LIST_FIELDS[field]
        values = []
        for v in self._ensure_list(value, field):
            if isinstance(v, dict):
                warn(('In object "{id}": The list in field "{field}" of '
                     + 'type "{type}" must contain references (URLs), but '
                     + 'an object was found instead.').format(
                     id=self._data['id'], field=field,
                     type=self._data['type']), SpecificationWarning)
                values.append(from_json(v))
            else:
                values.append(_lazy(v, obj_type))
        return values

    def _init_from_json(self, data):
        '''
        Init the object from (parsed) JSON data.
        '''
        if not 'id' in data:
            raise ValueError('JSON data does not have an `id` field.')
        if data['id'] != self._data['id']:
            warn(('Initializing object "{id}" from JSON data which contains a '
                 + 'different ID ("{json_id}").').format(id=self._data['id'],
                 json_id=data['id']), ContentWarning)
        try:
            type =  data['type']
        except KeyError:
            raise ValueError('JSON data does not have a `type` field.')
        cls = _class_from_type_uri(type)
        if cls != self.__class__:
            raise ValueError(('Type from JSON data ({type}) does not match '
                             + 'instance type.').format(type=type))
        for key, value in six.iteritems(data):
            self._data[key] = self._convert_value(key, value)
        self.loaded = True

    def __repr__(self):
        s = '<oparl:{cls}'.format(cls=self.__class__.__name__)
        if not self.loaded:
            s += '?'
        s += ' {id}'.format(id=self._data['id'])
        name = self._data.get('shortname', self._data.get('name'))
        if name:
            s += ' ({name})'.format(name=name)
        s += '>'
        return unidecode(s)

