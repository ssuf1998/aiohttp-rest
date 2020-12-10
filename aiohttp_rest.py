import inspect
import json
from collections import OrderedDict
from functools import wraps

from aiohttp.web_exceptions import HTTPMethodNotAllowed, HTTPBadRequest
from aiohttp.web import Request, Response
from aiohttp.web_urldispatcher import UrlDispatcher

__version__ = '0.1.2'

DEFAULT_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'GET')


class RestEndpoint:
    def __init__(self):
        self.methods = {}

        for method_name in DEFAULT_METHODS:
            method = getattr(self, method_name.lower(), None)
            if method:
                self.methods[method_name.upper()] = method

    async def dispatch(self, request: Request):
        method = self.methods.get(request.method.upper())
        if not method:
            raise HTTPMethodNotAllowed(
                method=request.method.upper(),
                allowed_methods=self.methods.keys()
            )

        wanted_args = list(inspect.signature(method).parameters.keys())
        available_args = request.match_info.copy()
        available_args.update({'request': request})

        unsatisfied_args = set(wanted_args) - set(available_args.keys())
        if unsatisfied_args:
            # Expected match info that doesn't exist
            raise HTTPBadRequest()

        return await method(**{arg_name: available_args[arg_name] for arg_name in wanted_args})


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
            raise HTTPBadRequest()
            # raise HttpBadRequest("{id_field} is defined in the payload, use PUT on /{name}/{id} instead".format(
            #     id_field=self.resource.id_field, name=self.resource.name, id=data[self.resource.id_field]))
        try:
            if self.resource.ignore_prop:
                for _ in self.resource.ignore_prop:
                    data[_] = None

            instance = self.resource.factory(**data)
        except TypeError:
            return HTTPBadRequest()
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
        try:
            if self.resource.ignore_prop:
                for _ in self.resource.ignore_prop:
                    data[_] = None

            instance = self.resource.factory(**data)
        except TypeError:
            return HTTPBadRequest()
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
        if instance_id not in self.resource.collection.keys() or property_name not in self.resource.properties:
            return Response(status=404)
        instance = self.resource.collection[instance_id]
        value = getattr(instance, property_name)
        return Response(status=200, body=self.resource.encode({property_name: value}), content_type='application/json')

    async def put(self, request, instance_id, property_name):
        if instance_id not in self.resource.collection.keys() or property_name not in self.resource.properties:
            return Response(status=404)
        value = (await request.json())[property_name]
        instance = self.resource.collection[instance_id]
        setattr(instance, property_name, value)
        return Response(status=200, body=self.resource.encode({property_name: value}), content_type='application/json')


class RestResource:
    def __init__(self, name, factory, collection):
        self.name = name
        self.factory = factory
        self.collection = collection

        self.ignore_prop = None
        temp_prop = list(inspect.signature(factory.__init__).parameters.keys())[1:]
        if 'ignore_prop' in dir(factory.__init__):
            self.ignore_prop = factory.__init__.ignore_prop
            for _ in factory.__init__.ignore_prop:
                temp_prop.remove(_)
        assert len(temp_prop) >= 1, 'Must include at least one arg for id'

        self.properties = tuple(temp_prop)
        self.id_field = self.properties[0]

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


def ignore_prop(*args):
    def _ignore_prop(func):
        assert type(func).__name__ == 'type', 'Must wrap a class.'
        setattr(func.__init__, 'ignore_prop', args)

        @wraps(func)
        def wrapper(*wrap_args, **wrap_kwargs):
            return func(*wrap_args, **wrap_kwargs)

        return wrapper

    return _ignore_prop
