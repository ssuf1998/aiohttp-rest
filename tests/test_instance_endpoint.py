import json
import uuid
from asyncio import coroutine

import pytest
from fluentmock import create_mock

from aiohttp_rest import InstanceEndpoint, RestResource

from .fixtures import Model, model_1, model_2, models, resource


@pytest.fixture
def endpoint(resource: RestResource):
    return InstanceEndpoint(resource)


@pytest.mark.asyncio
async def test_get_returns_correct_instance(endpoint: InstanceEndpoint, resource: RestResource, model_1: Model):
    response = await endpoint.get(model_1.id)

    assert json.loads(response.body.decode('utf-8')) == resource.render(model_1)
    assert response.status == 200
    assert response.content_type == 'application/json'


@pytest.mark.asyncio
async def test_get_should_raise_404_if_instance_not_found(endpoint: InstanceEndpoint):
    response = await endpoint.get('does not exist')

    assert response.status == 404


@pytest.mark.asyncio
async def test_put_should_create_a_new_model(endpoint: InstanceEndpoint, models: dict):
    instance_id = uuid.uuid4().hex
    request = create_mock(method='PUT', json=coroutine(lambda: {'name': 'john', 'age': 3}))

    response = await endpoint.put(request, instance_id=instance_id)

    assert [model for model in models.values() if model.id == instance_id and model.name == 'john' and model.age == 3]
    assert response.status == 201
    assert response.content_type == 'application/json'


@pytest.mark.asyncio
async def test_put_should_overwrite_existing_model(endpoint: InstanceEndpoint, model_1: Model, models: dict):
    request = create_mock(method='PUT', json=coroutine(lambda: {'name': 'john', 'age': 3}))

    response = await endpoint.put(request, instance_id=model_1.id)

    assert len(models) == 2
    assert models[model_1.id].name == 'john' and models[model_1.id].age == 3
    assert response.status == 201
    assert response.content_type == 'application/json'


@pytest.mark.asyncio
async def test_delete_should_remove_from_collection(endpoint: InstanceEndpoint, model_1: Model, models: dict):
    response = await endpoint.delete(model_1.id)

    assert model_1 not in models
    assert response.status == 204


@pytest.mark.asyncio
async def test_delete_should_raise_404_when_instance_not_found(endpoint: InstanceEndpoint):
    response = await endpoint.delete('does not exist')

    assert response.status == 404
