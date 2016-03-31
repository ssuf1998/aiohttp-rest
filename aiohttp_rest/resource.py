import json
from collections import OrderedDict

from aiohttp import HttpBadRequest
from aiohttp.web import Response
from aiohttp.web_urldispatcher import UrlDispatcher

from .endpoint import RestEndpoint


class CollectionEndpoint(RestEndpoint):
    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    async def get(self) -> Response:
        data = []
        for instance in self.resource.collection.values():
            data.append(self.resource.render(instance))
        data = self.resource.encode(data)
        return Response(status=200, body=data, content_type='application/json')

    async def post(self, request):
        data = await request.json()
        if self.resource.id_field in data.keys():
            raise HttpBadRequest("{id_field} is defined in the payload, use PUT on /{name}/{id} instead".format(
                id_field=self.resource.id_field, name=self.resource.name, id=data[self.resource.id_field]))
        instance = self.resource.factory(**data)
        self.resource.collection[getattr(instance, self.resource.id_field)] = instance
        new_url = '/{name}/{id}'.format(name=self.resource.name, id=getattr(instance, self.resource.id_field))
        return Response(status=201, body=self.resource.render_and_encode(instance),
                        content_type='application/json', headers={'LOCATION': new_url})


class InstanceEndpoint(RestEndpoint):
    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    async def get(self, instance_id):
        instance = self.resource.collection.get(instance_id)
        if not instance:
            return Response(status=404)
        data = self.resource.render_and_encode(instance)
        return Response(status=200, body=data, content_type='application/json')

    async def put(self, request, instance_id):
        data = await request.json()
        data[self.resource.id_field] = instance_id
        instance = self.resource.factory(**data)
        self.resource.collection[instance_id] = instance
        return Response(status=201, body=self.resource.render_and_encode(instance),
                        content_type='application/json')

    async def delete(self, instance_id):
        if instance_id not in self.resource.collection.keys():
            return Response(status=404)
        self.resource.collection.pop(instance_id)
        return Response(status=204)


class PropertyEndpoint(RestEndpoint):
    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    async def get(self, instance_id, property_name):
        instance = self.resource.collection[instance_id]
        value = getattr(instance, property_name)
        return Response(status=200, body=self.resource.encode({property_name: value}), content_type='application/json')

    async def put(self, request, instance_id, property_name):
        value = (await request.json())[property_name]
        instance = self.resource.collection[instance_id]
        setattr(instance, property_name, value)
        return Response(status=200, body=self.resource.encode({property_name: value}), content_type='application/json')

    async def delete(self, instance_id, property_name):
        instance = self.resource.collection[instance_id]
        setattr(instance, property_name, None)
        return Response(status=204)


class RestResource:
    def __init__(self, name, factory, collection, properties, id_field):
        self.name = name
        self.factory = factory
        self.collection = collection
        self.properties = properties
        self.id_field = id_field

        self.collection_endpoint = CollectionEndpoint(self)
        self.instance_endpoint = InstanceEndpoint(self)
        self.property_endpoint = PropertyEndpoint(self)

    def register(self, router: UrlDispatcher):
        router.add_route('*', '/{name}'.format(name=self.name), self.collection_endpoint.dispatch)
        router.add_route('*', '/{name}/{{instance_id}}'.format(name=self.name), self.instance_endpoint.dispatch)
        router.add_route('*', '/{name}/{{instance_id}}/{{property_name}}'.format(name=self.name),
                         self.property_endpoint.dispatch)

    def render(self, instance):
        return OrderedDict((name, getattr(instance, name)) for name in self.properties)

    @staticmethod
    def encode(data):
        return json.dumps(data, indent=4).encode('utf-8')

    def render_and_encode(self, instance):
        return self.encode(self.render(instance))
