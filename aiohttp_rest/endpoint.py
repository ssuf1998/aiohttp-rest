import inspect

from aiohttp import HttpMethodNotAllowed
from aiohttp.web import Request


DEFAULT_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'GET')


class RestEndpoint:
    def __init__(self):
        self.methods = {
            name: getattr(self, name.lower()) for name in DEFAULT_METHODS if getattr(self, name.lower(), None)}

    def register_method(self, method_name, method):
        self.methods[method_name.upper()] = method

    async def dispatch(self, request: Request):
        method = self.methods.get(request.method.upper())
        wanted_args = list(inspect.signature(method).parameters.keys())
        available_args = request.match_info.copy()
        available_args.update({'request': request})
        if method:
            return await method(**{arg_name: available_args[arg_name] for arg_name in wanted_args})
        return HttpMethodNotAllowed()
