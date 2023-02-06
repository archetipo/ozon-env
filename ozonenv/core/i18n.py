import gettext as support
from pathlib import Path
from babel import Locale
from babel.messages.frontend import CommandLineInterface
import os

i18ncwd = Path(__file__).cwd()
i18nlocaledir = f"{i18ncwd}/i18n"
babel_mapping = f"{i18ncwd}/babel-mapping.ini"


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs
            )
        return cls._instances[cls]


class I18n(metaclass=Singleton):
    def __init__(self):
        self.localedir = os.environ["OZON_LOCALEDIR"]
        self.lang = os.environ["OZON_APPLANG"]
        self.mapping_path = babel_mapping
        self.resource_paths = [Path(__file__).parent.parent.absolute()]
        self.active_lanuages = ["it", "en"]
        self.lanuages = ["it", "en"]

    def set_locale(self, lang="en", update=False):
        os.environ["OZON_APPLANG"] = lang
        if update:
            return self.update_translations(lang)
        self.get_translation()

    def make_language(self, lang, resource_code_folders=[]):
        if lang not in self.lanuages:
            self.lanuages.append(lang)
        self._extract_base_pot(resource_code_folders)
        self._make_pot_lang(lang)
        # self.update_translations(lang)
        os.environ["OZON_APPLANG"] = lang

    def update_translations(self, lang):
        if lang not in self.active_lanuages:
            self.active_lanuages.append(lang)
        # make *.mo files from lan.po file
        CommandLineInterface().run(
            argv=["pybabel", "compile", "-d", f"{self.localedir}"]
        )
        t = support.translation(
            "messages",
            localedir=self.localedir,
            languages=[lang],
            fallback=True,
        )
        t.install()
        # installa

    def add_reources_path(self, pathdir):
        self.resource_paths.append(pathdir)

    def set_babel_mapping_dir(self, babel_mapping_pathdir):
        self.mapping_path = babel_mapping_pathdir

    def _extract_base_pot(self, resource_code_folders=[]):
        # pybabel extract -F babel-mapping.ini -o locale/messages.pot ./
        self.resource_paths = self.resource_paths + resource_code_folders
        for path in self.resource_paths:
            CommandLineInterface().run(
                argv=[
                    "pybabel",
                    "extract",
                    f"{path.absolute()}",
                    "-o",
                    f"{self.localedir}/messages.pot",
                ]
            )

    def _make_pot_lang(self, lang):
        # pybabel init -d locale -l it -i locale/messages.pot
        CommandLineInterface().run(
            argv=[
                "pybabel",
                "init",
                "-d",
                f"{self.localedir}",
                "-l",
                f"{lang}",
                "-i" f"{self.localedir}/messages.pot",
            ]
        )

    def list_translations(self):
        """Returns a list of all the locales translations exist for.  The
        list returned will be filled with actual locale objects and not just
        strings.
        .. versionadded:: 0.6
        """
        result = []

        for dirname in self.localedir:
            if not Path(dirname).is_dir():
                continue

            for folder in Path(dirname).iterdir():
                locale_dir = folder.joinpath("LC_MESSAGES")
                if not locale_dir.is_dir():
                    continue

                if any(x.suffix == ".mo" for x in locale_dir.iterdir()):
                    result.append(Locale.parse(folder.absolute()))

        # If not other translations are found, add the default locale.
        if not result:
            result.append(Locale.parse(self.lang))

        return result

    def get_translation(self):
        self.localedir = os.environ["OZON_LOCALEDIR"]
        t = support.translation(
            "messages",
            localedir=self.localedir,
            languages=[self.lang],
            fallback=True,
        )
        return t

    def gettext(self, string, **variables):
        t = self.get_translation()
        s = t.gettext(string)
        return s if not variables else s % variables


def update_translation(lang, path=""):
    I18n().lang = lang
    if path:
        I18n().localedir = path


def gettext(*args, **kwargs):
    return I18n().gettext(*args, **kwargs)


_ = gettext
