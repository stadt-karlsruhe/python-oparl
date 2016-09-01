#!/usr/bin/env python
# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from . import Object


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
    _EXTERNAL_LIST_FIELDS = ['organization', 'person', 'meeting',
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
    _EXTERNAL_LIST_FIELDS = ['meeting']


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
    _EXTERNAL_LIST_FIELDS = ['body']

