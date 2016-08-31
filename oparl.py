#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
from warnings import warn

import dateutil.parser
import requests
import simplejson
import six


SCHEMA_URI = 'https://schema.oparl.org/1.0'


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
    try:
        return globals()[parts[1]]
    except KeyError:
        raise ValueError('Unknown type "{name}" in type URI "{uri}".'.format(
                         name=parts[1], uri=uri))


def _get_json(url):
    '''
    Download JSON from an URL and parse it.
    '''
    # FIXME: Implement pagination support
    return requests.get(url, verify=False).json()


def from_json(data):
    '''
    Initialize an OParl object from JSON.

    ``data`` is raw OParl JSON data (either as a Python data
    structure or as a string).

    Returns an appropriate subclass of ``Object`` initialized using
    the given data.
    '''
    if isinstance(data, six.string_types):
        data = simplejson.loads(data)
    if not 'id' in data:
        import pdb; pdb.set_trace()
        raise ValueError('JSON data does not have an `id` field.')
    if not 'type' in data:
        raise ValueError('JSON data does not have a `type` field.')
    cls = _class_from_type_uri(data['type'])
    obj = cls(data['id'])
    obj._init_from_json(data)
    return obj


def from_id(id):
    '''
    Initialize an OParl object from its ID (URL).

    The object's data is downloaded and parsed. The resulting object is
    returned.
    '''
    return from_json(_get_json(id))


def lazy(id, type):
    '''
    Create a lazy OParl object.

    The returned object doesn't contain any data (aside from the ID and
    the type). Call its ``load`` method to download the actual data.
    '''
    cls = _class_from_type_uri(type)
    obj = cls(id)
    obj['type'] = type
    return obj


def _ensure_list(value, type, field):
    if (not isinstance(value, collections.Sequence)
            or isinstance(value, six.string_types)):
        warn(('Field "{field}" of type "{type}" must contain a list, but a '
             + 'non-list value was found instead.').format(field=field,
             type=type), SpecificationWarning)
        value = [value]
    return value


def _is_url(value):
    '''
    Check if a value looks like an URL.
    '''
    return isinstance(value, six.string_types) and value.startswith('http')


class ObjectList(list):
    '''
    (Lazy) list of OParl objects.

    OParl collects some objects in lists which are not separate OParl
    objects themselves (for example the value of a Body's
    ``organization`` field). This class is a lazy wrapper around such
    lists.

    Use the ``load`` method to download the actual data.
    '''
    def __init__(self, url):
        self.url = url
        self.loaded = False

    def load(self):
        self[:] = [from_json(v) for v in _get_json(self.url)]
        self.loaded = True

    def __repr__(self):
        s = '<OParl ObjectList'
        if not self.loaded:
            s += '?'
        s += ' {url}>'.format(url=self.url)
        return s


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
    # values are automatically wrapped in ``ObjectList`` instances.
    _REFERENCE_LIST_URL_FIELDS = []

    def __init__(self, id):
        '''
        Private constructor.

        Use ``from_id`` or ``from_json`` instead.
        '''
        self['id'] = id
        self.loaded = False

    def load(self, force=False):
        '''
        Download the object's data.

        Downloads the object's data unless that has already been done.
        Set ``force`` to ``True`` to always download the data.
        '''
        if self.loaded and not force:
            return
        self._init_from_json(_get_json(self['id']))

    def _convert_value(self, field, value):
        '''
        Convert a JSON value to its proper type.

        If the field has a special type (as defined by the class'
        ``_DATE_FIELDS``, ``_DATETIME_FIELDS``, etc.) then the value is
        converted accordingly. Otherwise the value is returned
        unchanged.
        '''
        type = self['type']
        if field in self._DATE_FIELDS:
            return dateutil.parser.parse(value).date()
        if field in self._DATETIME_FIELDS:
            return dateutil.parser.parse(value)
        if field in self._OBJECT_FIELDS:
            if _is_url(value):
                warn(('Field "{field}" of type "{type}" must contain an '
                     + 'object, but a URL ("{url}") was found '
                     + 'instead.').format(field=field, type=type, url=value),
                     SpecificationWarning)
                return from_id(value)
            else:
                return from_json(value)
        if field in self._OBJECT_LIST_FIELDS:
            values = []
            for v in _ensure_list(value, type, field):
                if _is_url(v):
                    warn(('The list in field "{field}" of type "{type}" must '
                         + 'contain objects, but an URL ("{url}") was found '
                         + 'instead.').format(field=field, type=type, url=v),
                         SpecificationWarning)
                    values.append(from_id(v))
                else:
                    values.append(from_json(v))
            return values
        if field in self._REFERENCE_FIELDS:
            if isinstance(value, dict):
                warn(('Field "{field}" of type "{type}" must contain an '
                     + 'object reference (URL), but an object was found '
                     + 'instead.').format(field=field, type=type),
                     SpecificationWarning)
                return from_json(value)
            else:
                return lazy(value, self._REFERENCE_FIELDS[field])
        if field in self._REFERENCE_LIST_FIELDS:
            obj_type = self._REFERENCE_LIST_FIELDS[field]
            values = []
            for v in _ensure_list(value, type, field):
                if isinstance(v, dict):
                    warn(('The list in field "{field}" of type "{type}" must '
                         + 'contain references (URLs), but an object was '
                         + 'found instead.').format(field=field, type=type),
                         SpecificationWarning)
                    values.append(from_json(v))
                else:
                    values.append(lazy(v, obj_type))
            return values
        if field in self._REFERENCE_LIST_URL_FIELDS:
            return ObjectList(value)
        return value

    def _init_from_json(self, data):
        '''
        Init the object from (parsed) JSON data.
        '''
        if not 'id' in data:
            raise ValueError('JSON data does not have an `id` field.')
        if data['id'] != self['id']:
            warn(('Initializing object "{id}" from JSON data which contains a '
                 + 'different ID ("{json_id}").').format(id=self['id'],
                 json_id=data['id']), OParlWarning)
        try:
            type =  data['type']
        except KeyError:
            raise ValueError('JSON data does not have a `type` field.')
        cls = _class_from_type_uri(type)
        if cls != self.__class__:
            raise ValueError(('Type from JSON data ({type}) does not match '
                             + 'instance type.').format(type=type))
        self['type'] = type
        for key, value in data.iteritems():
            self[key] = self._convert_value(key, value)
        self.loaded = True

    def __repr__(self):
        s = '<oparl:{cls}'.format(cls=self.__class__.__name__)
        if not self.loaded:
            s += '?'
        s += ' {id}'.format(id=self['id'])
        name = self.get('shortname', self.get('name'))
        if name:
            s += ' ({name})'.format(name=name)
        s += '>'
        return s


class AgendaItem(Object):
    _DATETIME_FIELDS = ['created', 'modified', 'start', 'end']
    _OBJECT_FIELDS = ['resolutionFile']
    _OBJECT_LIST_FIELDS = ['auxiliaryFile']
    _REFERENCE_FIELDS = {
        'meeting': 'https://schema.oparl.org/1.0/Meeting',
        'consultation': 'https://schema.oparl.org/1.0/Consultation',
    }


class Body(Object):
    _DATETIME_FIELDS = ['created', 'modified', 'licenseValidSince',
                        'oparlSince']
    _OBJECT_FIELDS = ['location']
    _OBJECT_LIST_FIELDS = ['legislativeTerm']
    _REFERENCE_FIELDS = {
        'system': 'https://schema.oparl.org/1.0/System',
    }
    _REFERENCE_LIST_FIELDS = {
        'legislativeTerm': 'https://schema.oparl.org/1.0/LegislativeTerm',
    }
    _REFERENCE_LIST_URL_FIELDS = ['organization', 'person', 'meeting',
                                        'paper']


class Consultation(Object):
    _REFERENCE_FIELDS = {
        'paper': 'https://schema.oparl.org/1.0/Paper',
        'agendaItem': 'https://schema.oparl.org/1.0/AgendaItem',
        'meeting': 'https://schema.oparl.org/1.0/AgendaItem',
    }
    _REFERENCE_LIST_FIELDS = {
        'organization': 'https://schema.oparl.org/1.0/Paper',
    }


class File(Object):
    _DATE_FIELDS = ['date']
    _REFERENCE_FIELDS = {
        'masterFile': 'https://schema.oparl.org/1.0/File',
    }
    _REFERENCE_LIST_FIELDS = {
        'derivativeFile': 'https://schema.oparl.org/1.0/File',
        'meeting': 'https://schema.oparl.org/1.0/Meeting',
        'agendaItem': 'https://schema.oparl.org/1.0/AgendaItem',
        'paper': 'https://schema.oparl.org/1.0/Paper',
    }


class LegislativeTerm(Object):
    _DATE_FIELDS = ['startDate', 'endDate']
    _REFERENCE_FIELDS = {
        'body': 'https://schema.oparl.org/1.0/Body',
    }


class Location(Object):
    _REFERENCE_LIST_FIELDS = {
        'bodies': 'https://schema.oparl.org/1.0/Body',
        'organizations': 'https://schema.oparl.org/1.0/Organization',
        'meetings': 'https://schema.oparl.org/1.0/Meeting',
        'papers': 'https://schema.oparl.org/1.0/Paper',
    }


class Meeting(Object):
    _DATETIME_FIELDS = ['created', 'modified', 'start', 'end']
    _OBJECT_FIELDS = ['location', 'invitation', 'resultsProtocol',
                      'verbatimProtocol']
    _OBJECT_LIST_FIELDS = ['auxiliaryFile', 'agendaItem']
    _REFERENCE_LIST_FIELDS = {
        'organization': 'https://schema.oparl.org/1.0/Organization',
        'participant': 'https://schema.oparl.org/1.0/Person',
    }


class Membership(Object):
    _DATE_FIELDS = ['startDate', 'endDate']
    _REFERENCE_FIELDS = {
        'person': 'https://schema.oparl.org/1.0/Person',
        'organization': 'https://schema.oparl.org/1.0/Organization',
        'onBehalfOf': 'https://schema.oparl.org/1.0/Organization',
    }


class Organization(Object):
    _DATE_FIELDS = ['startDate', 'endDate']
    _OBJECT_FIELDS = ['location']
    _REFERENCE_FIELDS = {
        'body': 'https://schema.oparl.org/1.0/Body',
        'externalBody': 'https://schema.oparl.org/1.0/Body',
        'subOrganizationOf': 'https://schema.oparl.org/1.0/Organization',
    }
    _REFERENCE_LIST_FIELDS = {
        'membership': 'https://schema.oparl.org/1.0/Membership',
    }
    _REFERENCE_LIST_URL_FIELDS = ['meeting']


class Paper(Object):
    _DATE_FIELDS = ['date']
    _OBJECT_FIELDS = ['mainFile']
    _OBJECT_LIST_FIELDS = ['auxiliaryFile', 'location', 'consultation']
    _REFERENCE_FIELDS = {
        'body': 'https://schema.oparl.org/1.0/Body',
    }
    _REFERENCE_LIST_FIELDS = {
        'relatedPaper': 'https://schema.oparl.org/1.0/Paper',
        'subordinatedPaper': 'https://schema.oparl.org/1.0/Paper',
        'superordinatedPaper': 'https://schema.oparl.org/1.0/Paper',
        'originatorPerson': 'https://schema.oparl.org/1.0/Person',
        'underDirectionOf': 'https://schema.oparl.org/1.0/Organization',
        'originatorOrganization': 'https://schema.oparl.org/1.0/Organization',
    }


class Person(Object):
    _REFERENCE_FIELDS = {
        'body': 'https://schema.oparl.org/1.0/Body',
        'location': 'https://schema.oparl.org/1.0/Location',
    }
    _REFERENCE_LIST_FIELDS = {
        'membership': 'https://schema.oparl.org/1.0/Membership',
    }


class System(Object):
    _REFERENCE_LIST_FIELDS = {
        'otherOparlVersions': 'https://schema.oparl.org/1.0/System',
    }
    _REFERENCE_LIST_URL_FIELDS = ['body']

