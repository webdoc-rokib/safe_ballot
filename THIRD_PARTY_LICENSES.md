Third-party dependencies and common licenses

This file summarizes licenses for third-party components commonly used by this project. It is a convenience reference and not a replacement for reviewing each dependency's full license text.

Python packages (verify exact versions in `requirements.txt`):

- Django — BSD (3-clause). See https://www.djangoproject.com/foundation/license/
- cryptography — Apache License 2.0 or BSD-like (depending on version). Verify with `pip-licenses`.

Frontend libraries found in `static/` or commonly used in this project:

- Bootstrap — MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)
- Chart.js — MIT (https://github.com/chartjs/Chart.js/blob/master/LICENSE.md)
- Feather icons — MIT (https://github.com/feathericons/feather/blob/master/LICENSE)

How to produce a precise bill of materials

1. Install `pip-licenses` in your venv:

```powershell
pip install pip-licenses
```

2. Generate a table of installed packages and their licenses:

```powershell
pip-licenses --format=columns > THIRD_PARTY_PYTHON_LICENSES.txt
```

3. For front-end libs, check the LICENSE file in each library's package under `node_modules` (if you use npm/yarn) or the project repo.

Notes

- This file is informational. Always verify licenses for each dependency version before publishing or redistributing.
