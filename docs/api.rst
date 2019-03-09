API
===

.. module:: fox

.. module:: fox.conf

Configuration Objects
---------------------

.. autoclass:: Environment
   :members:

   Fox is configured through the global variable `env` which is an instance of :class:`Environment`.

.. autodata:: env

.. currentmodule:: fox.api

API Methods
-----------

.. autofunction:: run

.. autofunction:: run_concurrent

.. autofunction:: sudo

.. autofunction:: get

.. autofunction:: put

.. autofunction:: read

.. autofunction:: file_exists

.. autofunction:: local
                  

.. module:: fox.connection
            
Connection Object
-----------------

.. autoclass:: Connection
   :members:
   :inherited-members:


.. module:: fox.cluster

Cluster Object
--------------

.. autoclass:: Cluster
   :members:
   :inherited-members:

.. autofunction:: connect_pipes


.. module:: fox.sshconfig

SSHConfig Object
----------------

.. autoclass:: SSHConfig
   :members:

.. autoexception:: Error


.. module:: fox.utils

CommandResult Object
--------------------

:class:`CommandResult` objects are returned by all the :func:`fox.api.run()`, :func:`fox.api.sudo()`,
:func:`fox.api.local()` functions and their corresponding methods in the
:class:`fox.connection.Connection` class and can be used to inspect the results of the execution of
a command.

.. autoclass:: CommandResult
   :members:

   Use the :attr:`CommandResult.stdout` and :attr:`CommandResult.stderr` attributes to inspect
   `stdout` and `stderr` of the process.
