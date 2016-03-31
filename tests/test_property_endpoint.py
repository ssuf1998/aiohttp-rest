import json
from asyncio import coroutine

import pytest
from fluentmock import create_mock

from aiohttp_rest.resource import PropertyEndpoint, RestResource
from .fixtures import resource, Model, model_1, model_2, models


@pytest.fixture
def endpoint(resource: RestResource):
    return PropertyEndpoint(resource)


@pytest.mark.asyncio
async def test_get_should_return_correct_property(endpoint: PropertyEndpoint, model_1: Model):
    response = await endpoint.get(model_1.id, 'name')

    assert json.loads(response.body.decode('utf-8')) == {'name': model_1.name}
    assert response.status == 200
    assert response.content_type == 'application/json'


@pytest.mark.asyncio
async def test_get_should_raise_404_when_instance_is_not_found(endpoint: PropertyEndpoint):
    response = await endpoint.get('does_not_exit', 'name')

    assert response.status == 404


@pytest.mark.asyncio
async def test_get_should_raise_404_when_property_does_not_exist(endpoint: PropertyEndpoint, model_1: Model):
    response = await endpoint.get(model_1.id, 'does_not_exist')

    assert response.status == 404


@pytest.mark.asyncio
async def test_put_should_overwrite_property(endpoint: PropertyEndpoint, model_1: Model):
    request = create_mock(method='PUT', json=coroutine(lambda: {'name': 'vertical'}))

    response = await endpoint.put(request, model_1.id, 'name')

    assert model_1.name == 'vertical'
    assert json.loads(response.body.decode('utf-8')) == {'name': 'vertical'}
    assert response.status == 200
    assert response.content_type == 'application/json'


@pytest.mark.asyncio
async def test_put_should_return_404_when_instance_does_not_exist(endpoint: PropertyEndpoint, model_1: Model):
    request = create_mock(method='PUT', json=coroutine(lambda: {'name': 'vertical'}))

    response = await endpoint.put(request, 'does_not_exist', 'name')

    assert response.status == 404


@pytest.mark.asyncio
async def test_put_should_return_404_when_property_does_not_exist(endpoint: PropertyEndpoint, model_1: Model):
    request = create_mock(method='PUT', json=coroutine(lambda: {'does_not_exist': 'vertical'}))

    response = await endpoint.put(request, model_1.id, 'does_not_exist')

    assert response.status == 404
