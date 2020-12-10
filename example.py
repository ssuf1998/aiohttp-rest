from aiohttp.web import Application, run_app

from aiohttp_rest import RestResource, model


@model(protect_prop=('ignore_me',), read_only_prop=('me_read_only',))
class Person:
    def __init__(self, name, age, ignore_me, me_read_only=0):
        self.name = name
        self.age = age
        self.ignore_me = ignore_me
        self.me_read_only = me_read_only


async def people_instance_put_cb(instance_id, instance: Person):
    print(f'You just add a new person called {instance.name}.')


people = {}
app = Application()
people_callbacks = {
    'instance': {
        'put': people_instance_put_cb
    }
}
person_resource = RestResource('people', Person, people, callbacks=people_callbacks)
person_resource.register(app.router)

if __name__ == '__main__':
    run_app(app)
