# Setting up MedRecords

MedModels is built using Python. To contribute effectively, you'll need to set up a development environment for it.

**Requirements:**

- Python (3.10, 3.11, 3.12 or 3.13)

**Using the Makefile:**

MedModels utilizes a `Makefile` to manage development tasks. Here's a breakdown of the available commands and their functionalities:

- **install:** Sets up the virtual environment and installs the project in editable mode (meaning changes to the code are reflected without needing to reinstall).
- **install-dev:** Similar to `install`, but additionally installs development dependencies needed for running tests, linting, code formatting and the documentation.
- **install-tests:** Similar to install, but additionally installs development dependencies needed for running tests.
- **install-docs:** Similar to install, but additionally installs development dependencies needed for building the docs.
- **test:** Runs Python unit tests using `pytest`.
- **test-python-coverage:** Runs Python tests and shows the line numbers of statements in each module that weren't executed.
- **test-python-coverage-non-isolated:** Runs Python tests in a non-isolated manner, showing whether all modules are covered (including tests and `__init__.py` files).
- **docs:** Builds the docs using `sphinx`.
- **docs-serve:** Builds docs and live serves them to the localhost.
- **docs-clean:** Removes all locally generated documentation files.
- **lint:** Runs code linters for Python using `ruff`.
- **format:** Formats Python code using `ruff`.
- **clean:** Removes the virtual environment, cache directories, build artifacts, and other temporary files.
