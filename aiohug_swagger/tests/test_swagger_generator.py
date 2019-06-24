from pprint import pprint

import pytest
from aiohttp import web
from aiohug import RouteTableDef
from marshmallow import fields, Schema

from aiohug_swagger.swagger import (
    generate_spec,
    DEFAULT_TITLE,
    DEFAULT_VERSION,
    DEFAULT_OPENAPI_VERSION,
    DEFAULT_HOST,
    DEFAULT_SCHEMES,
)


@pytest.fixture
def make_app() -> web.Application:
    app = web.Application()

    def _make_app(routes=None):
        if routes is not None:
            app.add_routes(routes)
        return app

    return _make_app


def _generate_spec(app, **options):
    filled_options = {name: option for name, option in options.items() if option is not None}
    return generate_spec(app, **filled_options)


@pytest.mark.parametrize("title,spec_title", ((None, DEFAULT_TITLE), ("foo", "foo")))
def test_title(make_app, title, spec_title):
    app = make_app()
    spec = _generate_spec(app, title=title)
    assert spec["info"]["title"] == spec_title


@pytest.mark.parametrize("version,spec_version", ((None, DEFAULT_VERSION), ("1.0", "1.0")))
def test_version(make_app, version, spec_version):
    app = make_app()
    spec = _generate_spec(app, version=version)
    assert spec["info"]["version"] == spec_version


@pytest.mark.parametrize(
    "openapi_version,spec_openapi_version", ((None, DEFAULT_OPENAPI_VERSION), ("2.1", "2.1"), ("3.1", "3.1"))
)
def test_openapi_version(make_app, openapi_version, spec_openapi_version):
    app = make_app()
    spec = _generate_spec(app, openapi_version=openapi_version)
    if openapi_version and openapi_version[0] == "2":
        assert spec["swagger"] == spec_openapi_version
    else:
        assert spec["openapi"] == spec_openapi_version


@pytest.mark.parametrize("host,spec_host", ((None, DEFAULT_HOST), ("foo", "foo")))
def test_host(make_app, host, spec_host):
    app = make_app()
    spec = _generate_spec(app, host=host)
    assert spec["host"] == spec_host


@pytest.mark.parametrize("schemes,spec_schemes", ((None, DEFAULT_SCHEMES), (("http", "https"), ("http", "https"))))
def test_schemes(make_app, schemes, spec_schemes):
    app = make_app()
    spec = _generate_spec(app, schemes=schemes)
    assert spec["schemes"] == spec_schemes


def test_with_request_parameter(make_app):
    routes = RouteTableDef()

    @routes.get("/")
    async def with_request_parameter(request):
        return "foo"

    app = make_app(routes)
    spec = generate_spec(app)
    assert "parameters" not in spec["paths"]["/"]["get"]


def test_with_validated_parameter(make_app):
    routes = RouteTableDef()

    @routes.get("/")
    async def with_validated_int_parameter(foo: fields.Integer()):
        return "foo"

    @routes.get("/bar")
    async def with_validated_string_parameter(bar: fields.String()):
        return "bar"

    app = make_app(routes)
    spec = generate_spec(app)

    foo_parameter = spec["paths"]["/"]["get"]["parameters"][0]

    assert foo_parameter["in"] == "query"
    assert foo_parameter["name"] == "foo"
    assert foo_parameter["required"]
    assert foo_parameter["schema"] == {"format": "int32", "type": "integer"}

    bar_parameter = spec["paths"]["/bar"]["get"]["parameters"][0]

    assert bar_parameter["in"] == "query"
    assert bar_parameter["name"] == "bar"
    assert bar_parameter["schema"] == {"type": "string"}


def test_with_default_parameter(make_app):
    routes = RouteTableDef()

    @routes.get("/")
    async def with_default_parameter(foo: fields.Integer() = 5):
        return "foo"

    app = make_app(routes)
    spec = generate_spec(app)
    pprint(spec)

    parameter = spec["paths"]["/"]["get"]["parameters"][0]

    assert parameter["in"] == "query"
    assert parameter["name"] == "foo"
    assert not parameter["required"]
    assert parameter["schema"] == {"format": "int32", "type": "integer"}


def test_with_body_schema(make_app):
    routes = RouteTableDef()

    class BodySchema(Schema):
        a = fields.Integer(required=True)
        b = fields.String(required=True)

    @routes.post("/foo")
    async def with_body_schema_class(body: BodySchema):
        return ""

    @routes.post("/bar")
    async def with_body_schema_instance(body: BodySchema()):
        return ""

    app = make_app(routes)
    spec = generate_spec(app)
    pprint(spec)

    schema_name = f"{with_body_schema_class._original_handler.__module__}.BodySchema"

    foo_parameter = spec["paths"]["/foo"]["post"]["parameters"][0]
    assert foo_parameter["in"] == "body"
    assert foo_parameter["name"] == "body"
    assert foo_parameter["required"]
    assert foo_parameter["schema"] == {"$ref": f"#/definitions/{schema_name}"}

    bar_parameter = spec["paths"]["/bar"]["post"]["parameters"][0]

    assert bar_parameter["in"] == "body"
    assert bar_parameter["name"] == "body"
    assert bar_parameter["required"]
    assert bar_parameter["schema"] == {"$ref": f"#/definitions/{schema_name}"}

    schema = spec["components"]["schemas"][schema_name]

    assert schema == {
        "properties": {"a": {"format": "int32", "type": "integer"}, "b": {"type": "string"}},
        "required": ["a", "b"],
        "type": "object",
    }
