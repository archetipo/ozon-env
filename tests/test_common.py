import pytest
from pathlib import Path
from test_utils import *
from ozonenv.core.BaseModels import BasicModel, List, Dict

pytestmark = pytest.mark.asyncio


# @pytest.fixture(scope='function', autouse=True)
# def exit_pytest_first_failure():
#     if pytest.TestReport.outcome == 'failed':
#         pytest.exit('Exiting pytest')


def get_i18n_localedir():
    dirname = f"{Path(__file__).parent.absolute()}/i18n"
    Path(dirname).mkdir(parents=True, exist_ok=True)
    return dirname


def get_i18n_localedir_tr():
    return f"{Path(__file__).parent.absolute()}/i18n_translated"


@pytestmark
async def init_db_collection(db, data, collection):
    coll = db.engine.get_collection(collection)
    objects = data
    datas = coll.find({})
    if not await datas.to_list(length=None):
        for obj in objects:
            await coll.insert_one(obj)


@pytestmark
async def init_collecetion(db, file_name, collection):
    data = await readfilejson('data', file_name)
    if not isinstance(data, list):
        await init_db_collection(db, [data], collection)
    else:
        await init_db_collection(db, data, collection)


@pytestmark
async def insert_session_collections(db):
    await init_collecetion(db, 'coll_session.json', "session")


@pytestmark
async def get_config():
    return await readfilejson('data', 'config.json')


@pytestmark
async def get_formio_schema():
    return await readfilejson('data', 'test_form_1_formio_schema.json')


@pytestmark
async def get_formio_data():
    return await readfilejson('data', 'test_form_1_formio_data.json')


@pytestmark
async def get_formio_schema_conditional():
    return await readfilejson(
        'data', 'test_formio_conditional_visibility_json_logic_schema.json')


@pytestmark
async def get_formio_schema_conditional_data_hide():
    return await readfilejson(
        'data',
        'test_formio_data_conditional_visibility_json_logic_hide_secret.json')


@pytestmark
async def get_formio_schema_conditional_data_show():
    return await readfilejson(
        'data',
        'test_formio_data_conditional_visibility_json_logic_show_secret.json')


@pytestmark
async def get_user_data():
    return await readfilejson(
        'data', 'coll_user.json')


@pytestmark
async def get_file_data():
    return await readfilejson('data', 'data_file_1.json')


@pytestmark
async def get_formio_doc_schema():
    return await readfilejson('data', 'test_form_2_formio_schema_doc.json')

@pytestmark
async def downlad_file(self, file_url):
    return await readfile(self.upload_folder, file_url)


class User(BasicModel):
    uid: str
    password: str
    token: str = ""
    req_id: str = ""
    parent: str = ""
    full_name: str = ""
    last_update: float = 0
    is_admin: bool = False
    is_bot: bool = False
    use_auth: bool = False
    nome: str = ""
    cognome: str = ""
    mail: str = ""
    matricola: str = ""
    codicefiscale: str = ""
    allowed_users: List = []
    user_data: Dict = {}
    list_order: int = 1
    process_id: str = ""
    process_task_id: str = ""
    user_preferences: dict = {}
    user_function: str = ""
    function: str = ""
    badge_number: str = ""
    serial_number: str = ""

    @classmethod
    def get_unique_fields(cls):
        return ["rec_name", "uid"]
