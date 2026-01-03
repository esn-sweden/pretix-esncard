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

### Environment

1. Make sure that you have a working [pretix development setup](https://docs.pretix.eu/en/latest/development/setup.html)

2. Clone this repository.

3. Activate the virtual environment you use for pretix development.

4. Execute `python setup.py develop` within this directory to register this application with pretix's plugin registry.

5. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.

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

To automatically check for these issues before you commit, you can run `.install-hooks`.

## License

Copyright 2023 ESN Sea Battle OC

Released under the terms of the Apache License 2.0
