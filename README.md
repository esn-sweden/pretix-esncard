[![PyPI - Version](https://img.shields.io/pypi/v/pretix-esncard)](https://pypi.org/project/pretix-esncard/)
![PyPI - License](https://img.shields.io/pypi/l/pretix-esncard)

# ESNcard Validity Checker

A plugin for [Pretix](https://github.com/pretix/pretix) allowing automated validation of ESNcard numbers.

## Installation

Make sure to run from Pretix's virtual environment:

````sh
sudo -u pretix -s
source /var/pretix/venv/bin/activate
````

Install the package and update the database:

````sh
pip3 install pretix-esncard
python -m pretix migrate
python -m pretix rebuild
````

Restart Pretix:

````sh
sudo systemctl restart pretix-web pretix-worker
````

For more information about plugin installation, see the [Pretix documentation](https://docs.pretix.eu/self-hosting/installation/manual_smallscale/#install-a-plugin).

## Usage

### Setup

Activate the plugin from the organizer or event settings.

Go to **Products > Questions** and select **"Create a new question"**

* **Question**: "ESNcard number"
* **Type**: Text (one line)
* **Products**: Select all products with an ESNcard discount
* **Check** "required question"

Go to the **Advanced** tab

**Internal identifier**: `esncard`

> [!NOTE]
> You must write exactly this identifier for the plugin to work.

### Validation

The ESNcard number is validated against the ESNcard API during checkout and the customer is notified of any errors.

The validation fails if the entered ESNcard number:

* is not found
* is expired
* is unregistered (the user must register their card on [esncard.org](https://esncard.org))
* is used several times in the same order (each person must have their own ESNcard)

### Cloudflare bypass token

To avoid getting blocked by Cloudflare when sending many requests, you may ask the WPA of ESN International for a bypass token which you can configure in the global Pretix settings. You can access the global settings by enabling admin mode and look for the option in the bottom of the left sidebar.

## Development

### Setup

1. Make sure that you have a working [pretix development setup](https://docs.pretix.eu/en/latest/development/setup.html), including a virtual environment. Running on Linux is highly recommended as you may face issues with Windows.

2. Activate the virtual environment (from the pretix repository, not here!).

3. `cd` to the `pretix-esncard` repository and run `python3 setup.py develop`. This will install the plugin on the Pretix instance.

4. Go back to the `pretix` repository. `cd` into `src` and run `python3 manage.py runserver`.

5. Enable the plugin in the event settings.

In VS Code configure `Python: Select Interpreter` and point it to `path/to/pretix/env/bin/python`. Never create a virtual environment within `pretix-esncard`, it will lead to errors.

### Linting

This plugin has CI set up to enforce a few code style rules. To check locally, you need these packages installed:

````sh
pip install flake8 isort black
````

To check your plugin for rule violations, run:

````sh
black --check .
isort -c .
flake8 .
````

You can auto-fix some of these issues by running:

````sh
isort .
black .
````

To automatically check for these issues before you commit, add the following to `.git/hooks/pre-commit`:

````bash
#!/bin/bash

source /home/user/pretix/env/bin/activate  # Adjust this to the path on your computer
for file in $(git diff --cached --name-only | grep -E '\.py$' | grep -Ev "migrations|mt940\.py|pretix/settings\.py|make>
do
  echo $file
  git show ":$file" | flake8 - --stdin-display-name="$file" || exit 1 # we only want to lint the staged changes, not an>
  git show ":$file" | isort -c - | grep ERROR && exit 1 || true
done
````

### Translations

Update translatable strings:

````sh
make localegen
````

After translating the strings in the `.po` files, run

````sh
make
````

to generate the binary `.mo` files.


Add a new language by copying the file structure. `LANGUAGE_CODE/LC_MESSAGES/django.po`.
Make sure `Language:` in the header contains the correct language code.

## License

Copyright 2023 ESN Sea Battle OC

Released under the terms of the Apache License 2.0
