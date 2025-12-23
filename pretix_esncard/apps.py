from django.utils.translation import gettext_lazy

from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class ESNcardApp(PluginConfig):
    default = True
    name = "pretix_esncard"
    verbose_name = "ESNcard Validity Checker"

    class PretixPluginMeta:
        name = gettext_lazy("ESNcard Validity Checker")
        author = "ESN Sea Battle OC"
        description = gettext_lazy(
            "A plugin for pretix allowing automated validation of ESNcard numbers"
        )
        visible = True
        version = __version__
        category = "INTEGRATION"
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


default_app_config = "pretix_esncard.ESNcardApp"
