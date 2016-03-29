aiohttp_rest
============

.. image:: https://travis-ci.org/atbentley/aiohttp-rest.svg?branch=master
  :target:  https://travis-ci.org/atbentley/aiohttp-rest

aiohttp_rest makes it easy to create RESTful aiohttp endpoints that bind directly to models with minimal modification.

Usage
-----

Create your model:

.. code-block:: python

  class Person:
      def __init__(self, name, age):
          self.name = name
          self.age = age

Create an aiohttp application that makes use of a ``aiohttp_rest.RestResource``:

.. code-block:: python

  from aiohttp.web import Application, run_app
  from aiohttp_rest import RestResource

  from person import Person


  people = {}

  app = Application()
  person_resource = RestResource('people', people, Person, ('name', 'age'), 'name')
  person_resource.register(app.router)

  run_app(app)

Interact with the API:

.. code-block:: bash

  http POST localhost:8000/people name=andrew age=24
  http localhost:8000/people/andrew
  http PUT localhost:8000/people/andrew/age age=25
  http DELETE localhost:8000/people/andrew

Several things are required by the ``RestResource`` to make all this work:

- A name for the resource, this will form the base of the URL.
- A factory method for the model, as seen above, this can simply be the init method for the model or something more complex.
- A collection to store the models, this should be a ``dict``-like object.
- A list of properties to expose to the API.
- A property to treat as the id for the collection. In the above example we used the name as the id, so that's what we used in our URLs to refer to a specific instance in the collection.

Installing
----------

.. code-block::

  git clone github.com/atbentley/aiohttp_rest
  cd aiohttp_rest
  python setup.py install

Tests
-----

.. code-block::

  pip install -r build-requirements.txt
  py.test tests

License
-------

MIT
