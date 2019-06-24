import importlib
import logging
from inspect import signature, Parameter, isclass
from typing import Optional, Tuple

from aiohttp import web
from aiohug.directives import get_available_directives
from apispec import APISpec
from apispec.exceptions import DuplicateComponentNameError
from apispec.ext.marshmallow import MarshmallowPlugin, OpenAPIConverter, resolver
from marshmallow import Schema, fields

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost:8080"
DEFAULT_SCHEMES = ("http",)
DEFAULT_VERSION = None
DEFAULT_OPENAPI_VERSION = "3.0"
DEFAULT_TITLE = "Swagger Application"
DEFAULT_DEFINITIONS_PATH = None
DEFAULT_TESTING_MODE = False
DEFAULT_USE_DEFAULT_RESPONSE = True
DEFAULT_DESCRIPTION = None
DEFAULT_CONTACT_EMAIL = None

PARAMETER_IN_PATH = "path"
PARAMETER_IN_QUERY = "query"


def get_summary(doc):
    if doc is not None:
        return doc.split("\n")[0]


def where_is_parameter(name, url):
    return PARAMETER_IN_PATH if "{%s}" % name in url else PARAMETER_IN_QUERY


def get_parameters(url: str, handler, spec, converter):
    handler_signature = signature(handler._original_handler)

    parameters = []
    for name, handler_parameter in handler_signature.parameters.items():
        parameter_kind = handler_parameter.annotation  # TODO: support `args` argument to route decorator

        if name in get_available_directives() and name != "body" or name == "request":
            continue

        if isinstance(parameter_kind, fields.Field):
            parameter_place = where_is_parameter(name, url)
            parameter_kind.metadata = {"location": parameter_place}

            has_default = handler_parameter.default != Parameter.empty
            parameter_kind.required = not has_default

            parameter = converter.field2parameter(parameter_kind, name=name, default_in=parameter_place)

            if has_default:
                parameter["default"] = handler_parameter.default

            parameters.append(parameter)
        elif name == "body":
            is_schema_class = isclass(parameter_kind) and issubclass(parameter_kind, Schema)
            if not isinstance(parameter_kind, Schema) and not is_schema_class:
                continue

            schema = parameter_kind() if is_schema_class else parameter_kind
            schema_name = f"{schema.__module__}.{schema.__class__.__name__}"

            try:
                spec.components.schema(schema_name, schema=schema)
            except DuplicateComponentNameError:  # schemas can be reused, no big deal
                pass

            ref_definition = "#/definitions/{}".format(schema_name)
            ref_schema = {"$ref": ref_definition}

            parameters.append(
                {"in": "body", "name": "body", "required": True, "schema": ref_schema}
            )

    return parameters


def generate_spec(
    app: web.Application,
    title: str = DEFAULT_TITLE,
    version: Optional[str] = DEFAULT_VERSION,
    openapi_version: str = DEFAULT_OPENAPI_VERSION,
    host: str = DEFAULT_HOST,
    schemes: Tuple[str, ...] = DEFAULT_SCHEMES,
    definitions_path: Optional[str] = DEFAULT_DEFINITIONS_PATH,
    **options
):
    options["host"] = host
    options["schemes"] = schemes

    marshmallow_plugin = MarshmallowPlugin()

    spec = APISpec(
        title=title, version=version, openapi_version=openapi_version, plugins=(marshmallow_plugin,), **options
    )
    converter = OpenAPIConverter(openapi_version=openapi_version, schema_name_resolver=resolver, spec=spec)

    if definitions_path is not None:
        definitions = importlib.import_module(definitions_path)

        for name, schema in definitions.__dict__.items():
            if issubclass(schema, Schema):
                schema_name = resolver(schema)
                spec.components.schema(schema_name, schema=schema)

    resources = app.router._resources
    for resource in resources:
        url = resource.canonical
        name = resource.name
        for route in resource._routes:
            method = route.method
            if method == "HEAD":
                continue

            handler = route._handler

            try:
                handler_spec = handler.swagger_spec
            except AttributeError:
                handler_spec = {}

            if "excluded" in handler_spec:  # TODO: why?
                continue

            handler_spec["summary"] = get_summary(handler.__doc__)
            handler_spec["description"] = handler.__doc__

            parameters = get_parameters(url, handler, spec, converter)
            if parameters:
                handler_spec["parameters"] = parameters

            handler_spec["operationId"] = name

            spec.path(url, operations={method.lower(): handler_spec})

    return spec.to_dict()
