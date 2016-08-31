#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import json

import dateutil.parser
import six


SCHEMA_URLS = [
    'https://schema.oparl.org/1.0/',  # From standard
    'http://oparl.org/schema/1.0/',   # Used by politik-bei-uns
]


def _class_from_type_uri(uri):
    '''
    Convert a type URI to a class.
    '''
    for schema_url in SCHEMA_URLS:
        if uri.startswith(schema_url):
            name = uri[len(schema_url):]
            break
    else:
        raise ValueError('Invalid type URI "{uri}"'.format(uri=uri))
    try:
        return globals()[name]
    except KeyError:
        raise ValueError('Unknown type "{name}" in type URI "{uri}".'.format(
                         name=name, uri=uri))


def from_json(data):
    if isinstance(data, six.string_types):
        data = json.loads(data)
    if not 'id' in data:
        raise ValueError('JSON data does not have an `id` field.')
    if not 'type' in data:
        raise ValueError('JSON data does not have a `type` field.')
    cls = _class_from_type_uri(data['type'])
    obj = cls()
    for key, value in data.iteritems():
        if key in cls._DATE_FIELDS:
            value = dateutil.parser.parse(value).date()
        if key in cls._DATETIME_FIELDS:
            value = dateutil.parser.parse(value)
        obj[key] = value
    return obj


class Object(dict):
    '''
    Base class for all OParl objects.
    '''

    # Fields that have type 'Date'. Their values are automatically
    # parsed from the string representation.
    _DATE_FIELDS = []

    # Fields that have type 'DateTime'. Their values are automatically
    # parsed from the string representation.
    _DATETIME_FIELDS = ['created', 'modified']

    def __repr__(self):
        id = self['id']
        s = '<oparl:{cls} {id}'.format(cls=self.__class__.__name__, id=id)
        name = self.get('shortname', self.get('name'))
        if name:
            s += ' ({name})'.format(name=name)
        s += '>'
        return s


# OParl types from section 3.3.2
class AgendaItem(Object): pass
class Body(Object): pass
class Consultation(Object): pass
class File(Object): pass
class LegislativeTerm(Object): pass
class Location(Object): pass
class Meeting(Object): pass
class Membership(Object): pass
class Organization(Object): pass
class Paper(Object): pass
class Person(Object): pass
class System(Object): pass
