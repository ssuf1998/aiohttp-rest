from aiohttp.web import Application, run_app

from aiohttp_rest import RestResource, ignore_prop


@ignore_prop('ignore_me')
class Person:
    def __init__(self, name, age, ignore_me):
        self.name = name
        self.age = age
        self.ignore_me = ignore_me


people = {}
app = Application()
person_resource = RestResource('people', Person, people)
person_resource.register(app.router)

if __name__ == '__main__':
    run_app(app)
