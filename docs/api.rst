API Reference
=============

Here is the API reference for ``devopsx``.

.. contents:: Content
   :depth: 5
   :local:
   :backlinks: none


core
----

Some of the core classes and functions in ``devopsx``.

Message
~~~~~~~

A message in the conversation.

.. autoclass:: devopsx.message.Message
   :members:

Codeblock
~~~~~~~~~

A codeblock in a message, possibly executable by tools.

.. automodule:: devopsx.codeblock
   :members:

LogManager
~~~~~~~~~~

Holds the current conversation as a list of messages, saves and loads the conversation to and from files, supports branching, etc.

.. automodule:: devopsx.logmanager
   :members:


prompts
-------

See `Prompts <prompts.html>`_ for more information.

tools
-----

Supporting classes and functions for creating and using tools.

.. automodule:: devopsx.tools
   :members:

server
------

See `Server <server.html>`_ for more information.

.. automodule:: devopsx.server
   :members: