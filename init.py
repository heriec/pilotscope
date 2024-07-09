import os
import sys

from concurrent.futures.thread import ThreadPoolExecutor

from tortoise import Tortoise

sys.path.append("Core")
import agentscope


async def init_db():
    # Here we create a SQLite DB using file "db.sqlite3"
    #  also specify the app name of "models"
    #  which contain models from "app.models"
    await Tortoise.init(
        db_url='sqlite://{}/AppWielder.sqlite3'.format(os.path.join(config.app_data_dir, "UserData")),
        modules={'models': ["Database.Models.SessionModel"]}
    )
    # Generate the schema
    await Tortoise.generate_schemas()


async def init_server(app):
    await init_db()


async def close_server(app):
    await Tortoise.close_connections()


from Common.Config import Config

config = Config("config.ini")

agentscope.init(save_dir="AppSupports/SmartVscodeExtension/runs/Ignore", save_log=False, save_code=False, save_api_invoke=False,
                use_monitor=False)

from Common.SysLogger import get_logger

sys_logger = get_logger(config)

from Index.EmbedIndexManager import EmbedIndexManager

index_manager = EmbedIndexManager(config)

from Api.ApiManager import ApiManager

api_manager = ApiManager(config)
api_manager.init()

model_response_thread_pool = ThreadPoolExecutor(max_workers=config.model_response_thread_size)

session_id_2_pipeline = {}
session_id_2_test_manager = {}
