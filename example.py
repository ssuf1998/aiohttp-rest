from aiohttp.web import Application, run_app

from aiohttp_rest import RestResource


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age


people = {}
app = Application()
person_resource = RestResource('people', Person, people, ('name', 'age'), 'name')
person_resource.register(app.router)


if __name__ == '__main__':
    run_app(app)
