# aiohttp-rest

---
aiohttp-rest makes it easy to create RESTful aiohttp endpoints that bind directly to models with minimal modification.

⭐ Now support mongodb.

## Usage

---
Create your model:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
```

If you want some properties in model not to expose to RESTful API, you can use `ignore_prop` decorator to make it
happen, this property will be `None` in API.

Just like this:

```python
from aiohttp_rest import model


@model(protect_prop=('ignore_me',))
class Person:
    def __init__(self, name, age, ignore_me):
        self.name = name
        self.age = age
        self.ignore_me = ignore_me
```

Then create an aiohttp application that makes use of a `aiohttp_rest.RestResource`:

```python
from aiohttp.web import Application, run_app

from aiohttp_rest import RestResource


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age


people = {}
app = Application()
person_resource = RestResource('people', Person, people)
person_resource.register(app.router)

if __name__ == '__main__':
    run_app(app)
```
You can take a look at `example.py` to learn more.

Interact with the API:

```shell
http PUT localhost:8080/people/andrew age=24
http localhost:8080/people/andrew
http PUT localhost:8080/people/andrew/age age=25
http DELETE localhost:8080/people/andrew
```

Several things are required by the ``RestResource`` to make all this work:

- A name for the resource, this will form the base of the URL.
- A factory method for the model, as seen above, this can simply be the init method for the model or something more
  complex.
- A collection to store the models, this should be a ``dict``-like object.

No need to specific `properties` or `id_field` like original project, it will generate automatically.

- Properties to expose to the API will generate automatically, exclude ignored some.
- ID will automatically use the first one in your model init method's parameters

## Installing & Requirement

---
Haven't placed it in PyPi, just download `aiohttp_rest.py` to use, and it requires aiohttp.

## License

---
MIT, forked from [atbentley's aiohttp-rest](https://github.com/atbentley/aiohttp-rest)

