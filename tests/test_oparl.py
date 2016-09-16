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

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import warnings

import mock
import pytest
import six

import oparl
import oparl.objects



# Objects provided by the mocked ``_get_json``, keys are the URLs
OBJECTS = {
    'a-legislativeterm': {
        'id': 'a-legislativeterm',
        'type': 'https://schema.oparl.org/1.0/LegislativeTerm',
    },
    'object-with-id-that-differs-from-its-url': {
        'id': 'this is not my url',
        'type': 'https://schema.oparl.org/1.0/System',
    },
    'a-location': {
        'id': 'a-location',
        'type': 'https://schema.oparl.org/1.0/Location',
    },
}


@pytest.fixture(scope='module', autouse=True)
def mock_oparl():
    '''
    Mock parts of the ``oparl`` module.

    ``oparl._get_json`` is mocked so that it loads JSON data from
    ``OBJECTS``.

    ``oparl._is_url`` is mocked so that every string looks like an URL.
    '''
    def is_url(value):
        return isinstance(value, six.string_types)
    with mock.patch('oparl._get_json', new=OBJECTS.__getitem__):
        with mock.patch('oparl._is_url', new=is_url):
            yield


def test_invalid_date_string_triggers_contentwarning():
    with pytest.warns(oparl.ContentWarning) as record:
        oparl.from_json('''{
            "id": "object-with-invalid-date",
            "type": "https://schema.oparl.org/1.0/Organization",
            "startDate": "this is not a date"
        }''')
    assert len(record) == 1
    assert 'invalid date string' in record[0].message.args[0]


def test_invalid_datetime_string_triggers_contentwarning():
    with pytest.warns(oparl.ContentWarning) as record:
        oparl.from_json('''{
            "id": "object-with-invalid-datetime",
            "type": "https://schema.oparl.org/1.0/Organization",
            "created": "this is not a date-time"
        }''')
    assert len(record) == 1
    assert 'invalid date-time string' in record[0].message.args[0]


def test_scalar_instead_of_list_triggers_specificationwarning():
    with pytest.warns(oparl.SpecificationWarning) as record:
        obj = oparl.from_json('''{
            "id": "object-with-scalar-instead-of-list",
            "type": "https://schema.oparl.org/1.0/Person",
            "membership": {
                "id": "does-not-exist",
                "type": "https://schema.oparl.org/1.0/Membership"
            }
        }''')
    assert len(record) == 1
    assert 'non-list value' in record[0].message.args[0]
    membership = obj['membership']
    assert isinstance(membership, list)
    assert len(membership) == 1
    assert membership[0]['id'] == 'does-not-exist'


def test_reference_instead_of_object_triggers_specificationwarning():
    with pytest.warns(oparl.SpecificationWarning) as record:
        obj = oparl.from_json('''{
            "id": "object-with-reference-instead-of-object",
            "type": "https://schema.oparl.org/1.0/Body",
            "location": "a-location"
        }''')
    assert len(record) == 1
    assert 'must contain an object' in record[0].message.args[0]
    location = obj['location']
    assert isinstance(location, oparl.objects.Location)
    assert location['id'] == 'a-location'


def test_reference_instead_of_object_in_list_triggers_specificationwarning():
    with pytest.warns(oparl.SpecificationWarning) as record:
        obj = oparl.from_json('''{
            "id": "object-with-reference-instead-of-object-in-list",
            "type": "https://schema.oparl.org/1.0/Body",
            "legislativeTerm": ["a-legislativeterm"]
        }''')
    assert len(record) == 1
    assert 'must contain objects' in record[0].message.args[0]
    terms = obj['legislativeTerm']
    assert isinstance(terms, list)
    assert len(terms) == 1
    assert isinstance(terms[0], oparl.objects.LegislativeTerm)
    assert terms[0]['id'] == 'a-legislativeterm'


def test_object_instead_of_reference_triggers_specificationwarning():
    with pytest.warns(oparl.SpecificationWarning) as record:
        obj = oparl.from_json('''{
            "id": "object-with-object-instead-of-reference",
            "type": "https://schema.oparl.org/1.0/Body",
            "system": {
                "id": "does-not-exist",
                "type": "https://schema.oparl.org/1.0/System"
            }
        }''')
    assert len(record) == 1
    assert 'must contain an object reference' in record[0].message.args[0]
    system = obj['system']
    assert isinstance(system, oparl.objects.System)
    assert system['id'] == 'does-not-exist'


def test_object_instead_of_reference_in_list_triggers_specificationwarning():
    with pytest.warns(oparl.SpecificationWarning) as record:
        obj = oparl.from_json('''{
            "id": "object-with-object-instead-of-reference-in-list",
            "type": "https://schema.oparl.org/1.0/System",
            "otherOparlVersions": [{
                "id": "does-not-exist",
                "type": "https://schema.oparl.org/1.0/System"
            }]
        }''')
    assert len(record) == 1
    assert 'must contain references' in record[0].message.args[0]
    others = obj['otherOparlVersions']
    assert isinstance(others, list)
    assert len(others) == 1
    assert isinstance(others[0], oparl.objects.System)
    assert others[0]['id'] == 'does-not-exist'


def test_id_that_differs_from_url_triggers_contentwarning():
    obj = oparl._lazy('object-with-id-that-differs-from-its-url',
                      'https://schema.oparl.org/1.0/System')
    with pytest.warns(oparl.ContentWarning) as record:
        obj.load()
    assert len(record) == 1
    assert 'a different ID' in record[0].message.args[0]
    assert obj['id'] == 'this is not my url'


def test_invalid_schema_uri_triggers_specificationwarning():
    with pytest.warns(oparl.SpecificationWarning) as record:
        obj = oparl.from_json('''{
            "id": "object-with-invalid-schema-uri",
            "type": "this-is-not-the-correct-schema-uri/System"
        }''')
    assert len(record) == 2
    assert 'Invalid schema URI' in record[0].message.args[0]
    assert record[0].message[0] == record[1].message[0]
    assert obj['type'] == 'this-is-not-the-correct-schema-uri/System'


def test_missing_id_raises_valueerror():
    with pytest.raises(ValueError) as e:
        oparl.from_json('''{
            "type": "https://schema.oparl.org/1.0/System"
        }''')
    assert 'does not have an `id` field' in e.value.message


def test_missing_type_raises_valueerror():
    with pytest.raises(ValueError) as e:
        oparl.from_json('''{
            "id": "does-not-exist"
        }''')
    assert 'does not have a `type` field' in e.value.message


def test_type_mismatch_raises_valueerror():
    obj = oparl._lazy('a-location',
                      'https://schema.oparl.org/1.0/System')
    with pytest.raises(ValueError) as e:
        obj.load()
    assert 'does not match instance type' in e.value.message


def test_invalid_type_uri_raises_valuerror():
    with pytest.raises(ValueError) as e:
        oparl.from_json('''{
            "id": "does-not-exist",
            "type": "invalid"
        }''')
    assert 'Invalid type URI' in e.value.message


def test_unknown_type_raises_valueerror():
    with pytest.raises(ValueError) as e:
        oparl.from_json('''{
            "id": "does-not-exist",
            "type": "not/known"
        }''')
    assert 'Unknown type' in e.value.message

