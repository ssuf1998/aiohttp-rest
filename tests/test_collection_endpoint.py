import json
import uuid
from asyncio import coroutine

import pytest
from aiohttp import HttpBadRequest
from fluentmock import create_mock

from aiohttp_rest.resource import CollectionEndpoint, RestResource


class Model:
    def __init__(self, name, age, id=None):
        if id is None:
            id = uuid.uuid4().hex
        self.id = id
        self.name = name
        self.age = age


@pytest.fixture
def model_1():
    return Model('george', 24)


@pytest.fixture
def model_2():
    return Model('william', 25)


@pytest.fixture
def models(model_1, model_2):
    return {model_1.id: model_1, model_2.id: model_2}


@pytest.fixture
def resource(models):
    return RestResource('people', Model, models, ('id', 'name', 'age'), 'id')


@pytest.fixture
def endpoint(resource: RestResource):
    return CollectionEndpoint(resource)


@pytest.fixture
def empty_endpoint():
    return CollectionEndpoint(RestResource('people', Model, {}, ('id', 'name', 'age'), 'id'))


@pytest.mark.asyncio
async def test_get_should_return_empty_list_for_empty_collection(empty_endpoint: CollectionEndpoint):
    response = await empty_endpoint.get()

    assert json.loads(response.body.decode('utf-8')) == []
    assert response.status == 200
    assert response.content_type == 'application/json'


@pytest.mark.asyncio
async def test_get_should_return_all_instances(endpoint: CollectionEndpoint, resource: RestResource, model_1, model_2):
    response = await endpoint.get()

    people = json.loads(response.body.decode('utf-8'))
    assert len(people) == 2
    assert resource.render(model_1) in people
    assert resource.render(model_2) in people
    assert response.status == 200
    assert response.content_type == 'application/json'


@pytest.mark.asyncio
async def test_post_should_create_new_model(endpoint: CollectionEndpoint, resource: RestResource, models):
    request = create_mock(method='POST', json=coroutine(lambda: {'name': 'henry', 'age': 469}))

    response = await endpoint.post(request)
    assert response.status == 201
    assert response.content_type == 'application/json'
    person = json.loads(response.body.decode('utf-8'))
    assert response.headers['LOCATION'] == '/{name}/{id}'.format(name=resource.name, id=person['id'])
    assert person['name'] == 'henry'
    assert person['age'] == 469
    assert person in [resource.render(model) for model in models.values()]
    assert len(models) == 3


@pytest.mark.asyncio
async def test_post_with_id_defined_should_raise_401(endpoint: CollectionEndpoint):
    request = create_mock(method='POST', json=coroutine(lambda: {'name': 'henry', 'age': 469, 'id': 123}))

    with pytest.raises(HttpBadRequest):
        await endpoint.post(request)
