import pytest
from marshmallow import Schema, fields

from aiohug_swagger.decorators import _ensure_swagger_attr, response, spec


class ExampleTestSchema(Schema):
    field = fields.Integer()


def test_ensure_swagger_attr():
    def handler():
        pass

    with pytest.raises(AttributeError):
        handler.swagger_spec

    _ensure_swagger_attr(handler)
    handler.swagger_spec == {"responses": {}}


def test_response():
    code = 201
    schema = ExampleTestSchema
    description = "test"

    @response(code, schema=schema, description=description)
    def handler():
        pass

    assert code in handler.swagger_spec["responses"]
    assert handler.swagger_spec["responses"][code]["schema"] == schema
    assert handler.swagger_spec["responses"][code]["description"] == description


def test_response_code():
    code = 201

    @response(code)
    def handler():
        pass

    assert code in handler.swagger_spec["responses"]
    assert handler.swagger_spec["responses"][code] == {}


def test_spec():
    attrs = {"private": True, "exclude": True, "deprecated": True, "tags": ["test"]}

    @spec(**attrs)
    def handler():
        pass

    for attr, value in attrs.items():
        assert handler.swagger_spec[attr] == value


def test_spec_response_codes():
    codes = [200, 409]

    @spec(response_codes=codes)
    def handler():
        pass

    assert list(handler.swagger_spec["responses"].keys()) == codes
