import pytest
from aiohttp import web
from aiohug import RouteTableDef

from aiohug_swagger.handlers import routes as swagger_handlers


@pytest.fixture
def app() -> web.Application:
    routes = RouteTableDef()

    @routes.get("/")
    async def ping():
        return "pong"

    app = web.Application()
    app.add_routes(routes)
    app.add_routes(swagger_handlers)
    return app


async def test_swagger_json(app, aiohttp_client):
    client = await aiohttp_client(app)
    resp = await client.get("/swagger.json")
    assert resp.status == 200
    await resp.json()
    assert resp.content_type == "application/json"


async def test_swagger_yaml(app, aiohttp_client):
    client = await aiohttp_client(app)
    resp = await client.get("/swagger.yaml")
    assert resp.status == 200
    assert resp.content_type == "text/yaml"
    await resp.text()


async def test_swagger_html(app, aiohttp_client):
    client = await aiohttp_client(app)
    resp = await client.get("/swagger.html")
    assert resp.status == 200
    assert resp.content_type == "text/html"
    await resp.text()


async def test_swagger(app, aiohttp_client):
    client = await aiohttp_client(app)
    resp = await client.get("/redoc.html")
    assert resp.status == 200
    assert resp.content_type == "text/html"
