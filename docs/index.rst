.. Fox documentation master file, created by
   sphinx-quickstart on Sun Mar  3 17:41:16 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Fox
==============

Fox is a Python package for creating quick and dirty server automation scripts. For example to jump
into the late nineties::

  from fox.conf import env
  from fox.api import run, sudo

  env.host_string = "server.example.com"
  env.sudo_password = "very secret"

  run("./configure --with-prefix=/90s", cd="/code/project")
  sudo("make install", cd="/code/project")

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
