Examples
========

A list of things you can do with devopsx.

To see example output without running the commands yourself, check out the :doc:`demos`.


.. code-block:: bash
    devopsx 'write a web app to particles.html which shows off an impressive and colorful particle effect using three.js'
    devopsx 'render mandelbrot set to mandelbrot.png'
    # stdin
    make test | devopsx 'fix the failing tests'
    # from a file
    devopsx 'summarize this' README.md
    devopsx 'refactor this' main.py
    # it can read files using tools, if contents not provided in prompt
    devopsx 'suggest improvements to my vimrc'
Do you have a cool example? Share it with us in the `Discussions <https://github.com/infractura/devopsx/discussions>`_!