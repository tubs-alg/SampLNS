=================
Installation
=================

This package requires a valid license of the commercial MIP-solver
Gurobi. You can get a free license for academic purposes. These academic
licenses are fairly easy to obtain, as explained in `this
video <https://www.youtube.com/watch?v=oW6ma8rdZk8>`__:

1. Register an academic account.
2. Install Gurobi (very easy with Conda, you only need the tool
   ``grbgetkey``).
3. Use ``grbgetkey`` to set up a license on your computer. You may have
   to be within the university network for this to work.

After you got your license, move into the folder with ``setup.py`` and
run

.. code:: shell

   pip install .

This command should automatically install all dependencies and build the
package. The package contains native C++-code that is compiled during
installation. This requires a C++-compiler. On most systems, this should
be installed by default. If not, you can install it via

.. code:: shell

   sudo apt install build-essential  # Ubuntu
   sudo pacman -S base-devel         # Arch

If you don’t have initial samples at hand you might want to generate
initial samples for SampLNS with FeatJAR. This requires you to install
Java version 11 or higher.

.. code:: shell

   sudo apt-get install openjdk-11-jdk

Generally, the installation will take a while as it has to compile the
C++, but it should work out of the box. If you encounter any problems,
please open an issue. Unfortunately, the performance of native code is
bought with a more complex installation process, and it is difficult to
make it work on all systems. Windows systems are especially difficult to
support. We suggest using a Linux system.