import pytest
from test_common import get_i18n_localedir_tr, get_i18n_localedir
from ozonenv.core.i18n import I18n, _
import os
import shutil
from pathlib import Path

pytestmark = pytest.mark.asyncio


# @pytestmark
def test_I18n_make_lang_data():
    locale_dir = get_i18n_localedir()
    lang = "it"
    os.environ["OZON_APPLANG"] = lang
    os.environ["OZON_LOCALEDIR"] = locale_dir
    i18n = I18n()
    i18n.make_language("it")
    po_path = Path(locale_dir).joinpath(
        'it/LC_MESSAGES/messages.po').absolute()
    with open(po_path, 'rb') as f:
        assert "# Italian translations for PROJECT." in str(f.read())
    i18n.make_language("en")
    po_path = Path(locale_dir).joinpath(
        'en/LC_MESSAGES/messages.po').absolute()
    with open(po_path, 'rb') as f:
        assert "# English translations for PROJECT." in str(f.read())
    # shutil.rmtree(f"{Path(locale_dir).absolute()}/.", ignore_errors=True)


# @pytestmark
def test_I18n_test_transaltion():
    os.environ["OZON_APPLANG"] = "it"
    path = get_i18n_localedir_tr()
    os.environ["OZON_LOCALEDIR"] = path
    i18n = I18n()
    i18n.localedir = path
    i18n.update_translations("it")
    a = b = "test"
    assert (
            _("Duplicate key error %s: %s") % (a, b) ==
            "Errore Duplicato test: test"
    )
