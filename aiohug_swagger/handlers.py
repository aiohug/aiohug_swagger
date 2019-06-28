import os

import yaml
from aiohttp import web
from aiohug import RouteTableDef

from aiohug_swagger import generate_spec, spec

routes = RouteTableDef()


@spec(exclude=True)
@routes.get("/swagger.json")
async def swagger_json(request):
    return generate_spec(request.app)


@spec(exclude=True)
@routes.get("/swagger.yaml")
async def swagger_yaml(request):
    return web.Response(
        text=yaml.dump(generate_spec(request.app)), content_type="text/yaml"
    )


async def _render_template(template):
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates", template
    )
    with open(template_path) as template:
        return template.read().replace("{{ swagger_url }}", "/swagger.json")


@spec(exclude=True)
@routes.get("/swagger.html")
async def swagger_html():
    return web.Response(
        text=await _render_template("swaggerui.html"), content_type="text/html"
    )


@spec(exclude=True)
@routes.get("/redoc.html")
async def redoc_html():
    return web.Response(
        text=await _render_template("redoc.html"), content_type="text/html"
    )
