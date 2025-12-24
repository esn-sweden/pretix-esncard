# ESNcard Validity Checker

A plugin for [Pretix](https://github.com/pretix/pretix) allowing automated validation of [ESNcard](https://esncard.org/) numbers.

## Installation

Make sure to run from Pretix's virtual environment

````bash
sudo -u pretix -s
source /var/pretix/venv/bin/activate
````

Then install the wheel and update the database just in case

````
pip3 install path/to/file.whl
python -m pretix migrate
python -m pretix rebuild
````

Finally restart Pretix

````bash
sudo systemctl restart pretix-web pretix-worker
````

You can now activate the plugin from the organizer or event settings.

For more information, see [Pretix documentation](https://docs.pretix.eu/self-hosting/installation/manual_smallscale/#install-a-plugin)

# Development setup

1. Make sure that you have a working [pretix development setup](https://docs.pretix.eu/en/latest/development/setup.html)

2. Clone this repository.

3. Activate the virtual environment you use for pretix development.

4. Execute `python setup.py develop` within this directory to register this application with pretix's plugin registry.

5. Execute `make` within this directory to compile translations.

6. Restart your local pretix server. You can now use the plugin from this repository for your events by enabling it in
   the 'plugins' tab in the settings.

This plugin has CI set up to enforce a few code style rules. To check locally, you need these packages installed:

    pip install flake8 isort black

To check your plugin for rule violations, run:

    black --check .
    isort -c .
    flake8 .

You can auto-fix some of these issues by running:

    isort .
    black .

To automatically check for these issues before you commit, you can run `.install-hooks`.

## License

Copyright 2023 ESN Sea Battle OC

Released under the terms of the Apache License 2.0
