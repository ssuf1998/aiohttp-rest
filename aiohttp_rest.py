import inspect
import json
from collections import OrderedDict
from functools import wraps

from aiohttp.web_exceptions import HTTPMethodNotAllowed, HTTPBadRequest
from aiohttp.web import Request, Response
from aiohttp.web_urldispatcher import UrlDispatcher
from pymongo.collection import Collection

__version__ = '0.2.0'

DEFAULT_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'GET')
_ENDPOINT_CLASS_CB_MAP = {
    'CollectionEndpoint': 'collection',
    'InstanceEndpoint': 'instance',
    'PropertyEndpoint': 'property'
}


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

    async def trigger_callback(self, **kwargs):
        resource = getattr(self, 'resource')
        req_type = _ENDPOINT_CLASS_CB_MAP[self.__class__.__name__]
        method = inspect.stack()[1][3]

        if resource.callbacks and resource.callbacks.get(req_type):
            cb = resource.callbacks.get(req_type).get(method)
            if cb:
                await cb(**kwargs)


class CollectionEndpoint(RestEndpoint):
    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    async def get(self) -> Response:
        data = []
        if self.resource.use_mongodb:
            data = list(self.resource.col.find({}, {'_id': 0}))
        else:
            for instance in self.resource.col.values():
                data.append(self.resource.render(instance))

        await self.trigger_callback(data=data)
        return Response(status=200, body=self.resource.encode(data),
                        content_type='application/json')

    async def post(self, request: Request):
        data = await request.json()
        if self.resource.id_field in data.keys():
            raise HTTPBadRequest()
        try:
            if self.resource.factory.protect_prop:
                for _ in self.resource.factory.protect_prop:
                    data[_] = None
            if self.resource.factory.read_only_prop:
                for _ in self.resource.factory.read_only_prop:
                    if _ in data.keys():
                        data.pop(_)

            instance = self.resource.factory(**data)
        except TypeError:
            return HTTPBadRequest()
        instance_id = getattr(instance, self.resource.id_field)

        if self.resource.use_mongodb:
            self.resource.col.insert_one(
                self.resource.render(instance)
            )
        else:
            self.resource.col[instance_id] = instance

        new_url = '/{name}/{id}'.format(name=self.resource.name, id=instance_id)
        await self.trigger_callback(instance_id=instance_id, instance=instance)
        return Response(status=201, body=self.resource.render_and_encode(instance),
                        content_type='application/json', headers={'LOCATION': new_url})


class InstanceEndpoint(RestEndpoint):
    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    async def get(self, instance_id):
        if self.resource.use_mongodb:
            instance = self.resource.col.find_one(
                {self.resource.id_field: instance_id},
                {'_id': 0}
            )
            instance = self.resource.factory(**instance)
        else:
            instance = self.resource.col.get(instance_id)

        if not instance:
            return Response(status=404)
        await self.trigger_callback(instance_id=instance_id, instance=instance)
        return Response(status=200, body=self.resource.render_and_encode(instance),
                        content_type='application/json')

    async def put(self, request, instance_id):
        data = await request.json()
        if self.resource.id_field in data.keys():
            return HTTPBadRequest()

        data[self.resource.id_field] = instance_id
        try:
            if self.resource.factory.protect_prop:
                for _ in self.resource.factory.protect_prop:
                    data[_] = None
            if self.resource.factory.read_only_prop:
                for _ in self.resource.factory.read_only_prop:
                    if _ in data.keys():
                        data.pop(_)

            instance = self.resource.factory(**data)
        except TypeError as e:
            print(e)
            return HTTPBadRequest()

        if self.resource.use_mongodb:
            if self.resource.col.count_documents(
                    {self.resource.id_field: instance_id}
            ) > 0:
                return HTTPBadRequest()
            self.resource.col.insert_one(
                self.resource.render(instance)
            )
        else:
            if instance_id in self.resource.col.keys():
                return HTTPBadRequest()
            self.resource.col[instance_id] = instance

        await self.trigger_callback(instance_id=instance_id, instance=instance)
        return Response(status=201, body=self.resource.render_and_encode(instance),
                        content_type='application/json')

    async def delete(self, instance_id):
        if self.resource.use_mongodb:
            count = self.resource.col.delete_one({
                self.resource.id_field: instance_id
            }).deleted_count
            if count == 0:
                return Response(status=404)
        else:
            if instance_id not in self.resource.col.keys():
                return Response(status=404)
            self.resource.col.pop(instance_id)

        return Response(status=204)


class PropertyEndpoint(RestEndpoint):
    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    async def get(self, instance_id, property_name):
        if property_name not in self.resource.properties:
            return Response(status=404)

        if self.resource.use_mongodb:
            value = self.resource.col.find_one(
                {self.resource.id_field: instance_id},
                {'_id': 0}
            ).get(property_name, None)
        else:
            if instance_id not in self.resource.col.keys():
                return Response(status=404)
            instance = self.resource.col[instance_id]
            value = getattr(instance, property_name)

        await self.trigger_callback(instance_id=instance_id, property_name=property_name, value=value)
        return Response(status=200, body=self.resource.encode({property_name: value}),
                        content_type='application/json')

    async def put(self, request, instance_id, property_name):
        if property_name not in self.resource.properties:
            return Response(status=404)

        if property_name in self.resource.factory.read_only_prop:
            return HTTPBadRequest()

        value = (await request.json())[property_name]
        if self.resource.use_mongodb:
            count = self.resource.col.update_one(
                {self.resource.id_field: instance_id},
                {'$set': {property_name: value}}
            ).modified_count
            if count == 0:
                return Response(status=404)
        else:
            if instance_id not in self.resource.col.keys():
                return Response(status=404)
            instance = self.resource.col[instance_id]
            setattr(instance, property_name, value)

        await self.trigger_callback(instance_id=instance_id, property_name=property_name, value=value)
        return Response(status=200, body=self.resource.encode({property_name: value}),
                        content_type='application/json')


class RestResource:
    def __init__(self, name, factory, col,
                 callbacks: dict = None):
        self.name = name
        assert 'aiohttp_rest_model' in dir(factory), 'please wrap "factory" by model.'
        self.factory = factory
        assert isinstance(col, Collection) or isinstance(col, dict), \
            '"col" should be instance of Collection or dict-like'
        if isinstance(col, Collection):
            self.use_mongodb = True
        else:
            self.use_mongodb = False
        self.col = col

        temp_prop = list(inspect.signature(factory).parameters.keys())
        for _ in factory.protect_prop:
            temp_prop.remove(_)
        assert len(temp_prop) >= 1, 'Must include at least one arg for id'

        self.properties = tuple(temp_prop)
        self.id_field = factory.id_field if factory.id_field else self.properties[0]

        self.callbacks = callbacks

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


def model(
        id_field: str = None,
        protect_prop: tuple = (),
        read_only_prop: tuple = ()
):
    def _model(func):
        assert type(func).__name__ == 'type', 'Must wrap a class.'
        setattr(func, 'aiohttp_rest_model', 1)
        setattr(func, 'id_field', id_field)
        setattr(func, 'protect_prop', protect_prop)
        setattr(func, 'read_only_prop', read_only_prop)

        @wraps(func)
        def wrapper(*wrap_args, **wrap_kwargs):
            ret = func(*wrap_args, **wrap_kwargs)
            return ret

        return wrapper

    return _model
