from asyncio import coroutine

import pytest
from aiohttp import HttpBadRequest, HttpMethodNotAllowed
from fluentmock import create_mock

from aiohttp_rest import RestEndpoint


class CustomEndpoint(RestEndpoint):
    def get(self):
        pass

    def patch(self):
        pass


@pytest.fixture
def endpoint():
    return RestEndpoint()


@pytest.fixture
def custom_endpoint():
    return CustomEndpoint()


def test_exiting_methods_are_registered_during_initialisation(custom_endpoint: CustomEndpoint):
    assert len(custom_endpoint.methods) == 2
    assert ('GET', custom_endpoint.get) in custom_endpoint.methods.items()
    assert ('PATCH', custom_endpoint.patch) in custom_endpoint.methods.items()


def test_register_method(endpoint: RestEndpoint):
    def sample_method():
        pass

    endpoint.register_method('verb', sample_method)

    assert ('VERB', sample_method) in endpoint.methods.items()


@pytest.mark.asyncio
async def test_dispatch_uses_correct_handler_for_verb(endpoint: RestEndpoint):
    endpoint.register_method('VERB1', coroutine(lambda: 5))
    endpoint.register_method('VERB2', coroutine(lambda: 17))

    assert await endpoint.dispatch(create_mock(method='VERB1', match_info={})) == 5
    assert await endpoint.dispatch(create_mock(method='VERB2', match_info={})) == 17


@pytest.mark.asyncio
async def test_dispatch_passes_request_when_required(endpoint: RestEndpoint):
    endpoint.register_method('REQUEST', coroutine(lambda request: request))
    request = create_mock(method='REQUEST', match_info={})

    assert await endpoint.dispatch(request) == request


@pytest.mark.asyncio
async def test_dispatch_passes_match_info_when_required(endpoint: RestEndpoint):
    endpoint.register_method('MATCH_INFO', coroutine(lambda prop1, prop2: (prop2, prop1)))
    request = create_mock(method='MATCH_INFO', match_info={'prop1': 1, 'prop2': 2})

    assert await endpoint.dispatch(request) == (2, 1)


@pytest.mark.asyncio
async def test_dispatch_raises_bad_request_when_match_info_does_not_exist(endpoint: RestEndpoint):
    endpoint.register_method('BAD_MATCH_INFO', coroutine(lambda no_match: no_match))
    request = create_mock(method='BAD_MATCH_INFO', match_info={})

    with pytest.raises(HttpBadRequest):
        await endpoint.dispatch(request)


@pytest.mark.asyncio
async def test_dispatch_raises_method_not_allowed_when_verb_not_matched(endpoint: RestEndpoint):
    request = create_mock(method='NO_METHOD')

    with pytest.raises(HttpMethodNotAllowed):
        await endpoint.dispatch(request)
