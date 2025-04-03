============
Installation
============

You can install ``brickalize`` using pip or directly from the source repository.

Using pip (Recommended)
-----------------------

This is the standard way to install the package if it has been published to the Python Package Index (PyPI). Open your terminal or command prompt and run:

.. code-block:: bash

   pip install brickalize

This command downloads the package from PyPI and installs it along with all its required dependencies.

Installing from Source (GitHub)
-------------------------------

If you want the latest development version or the package is not yet on PyPI, you can install it directly from the GitHub repository:

.. code-block:: bash

   pip install git+https://github.com/CreativeMindstorms/brickalize.git

This command will clone the repository and install the package, also taking care of dependencies listed in ``pyproject.toml``.

Dependencies
------------

Installing ``brickalize`` using either method will automatically install the following required libraries:

*   numpy
*   open3d
*   trimesh
*   tqdm
*   opencv-python
*   scipy
*   rtree

Ensure you have a compatible Python version (>= 3.8) installed.