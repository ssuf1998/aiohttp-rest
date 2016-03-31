import uuid

import pytest

from aiohttp_rest import RestResource


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
