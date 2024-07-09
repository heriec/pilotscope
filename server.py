import sys

from AppSupports.SmartVscodeExtension.code.tests.TestManager import TestManager
from Common.Recoder import Recorder
from Database.Models.SessionModel import SessionModel
from Pipeline.ChatPipeline import ChatPipeline
from Pipeline.IntentGodChatPipeline import IntentGodAgentChatPipeline

sys.path.append("Core")

from init import session_id_2_pipeline, config, index_manager, init_server, close_server, sys_logger, \
    session_id_2_test_manager
from aiohttp import web
from Common.Utils import update_model_config, load_model_config
from Common.ChatReposne import Response, ResponseStatusEnum
from Common.Context import Context
from Pipeline.GodChatPipeline import GodAgentChatPipeline


def is_valid_pipeline(context: Context):
    if context.session_id not in session_id_2_pipeline:
        return False

    if not session_id_2_pipeline[context.session_id].is_started:
        return False
    return True


def get_pipeline(context: Context):
    if context.session_id not in session_id_2_pipeline:
        # session_id_2_pipeline[context.session_id] = GodAgentChatPipeline(config, context)
        session_id_2_pipeline[context.session_id] = IntentGodAgentChatPipeline(config, context)
    pipeline = session_id_2_pipeline[context.session_id]
    pipeline.reset()
    return pipeline


def get_test_manager(context: Context):
    if context.session_id not in session_id_2_test_manager:
        session_id_2_test_manager[context.session_id] = TestManager(config, context)
    return session_id_2_test_manager[context.session_id]


async def start(request):
    context = Context.from_dict(await request.json())

    # update model config
    update_model_config(context)

    test_manager = get_test_manager(context)
    pipeline = get_pipeline(context)

    try:
        result: Response = await pipeline.start(context)
        if result.status != ResponseStatusEnum.TASK_QUESTION:
            test_manager.check(result)
    except Exception as e:
        result = Response.get_exception_response()
        sys_logger.error(e)
        test_manager.task_failed()

    # task may be cancelled
    if not is_valid_pipeline(context):
        clear(context)
        result = Response.get_task_cancelled_response()

    # task should be finished immediately when it is a question
    if result.status == ResponseStatusEnum.TASK_QUESTION:
        await finish_task(request)

    return web.json_response(result.to_json())


async def handle_api_results(request):
    context = Context.from_dict(await request.json())
    if not is_valid_pipeline(context):
        result = Response.get_task_cancelled_response()
    else:
        pipeline = session_id_2_pipeline[context.session_id]
        test_manager = get_test_manager(context)
        try:
            result = await pipeline.handle_api_results(context)
            test_manager.check(result)
        except Exception as e:
            result = Response.get_exception_response()
            test_manager.task_failed()
            sys_logger.error(e)

    if not is_valid_pipeline(context):
        clear(context)
        result = Response.get_task_cancelled_response()

    return web.json_response(result.to_json())


async def finish_task(request):
    context = Context.from_dict(await request.json())

    recorder = Recorder(config, context.session_id)
    await recorder.save()

    clear(context)

    return web.json_response({})


async def stop_task(request):
    context = Context.from_dict(await request.json())
    if context.session_id in session_id_2_pipeline:
        pipeline: ChatPipeline = session_id_2_pipeline[context.session_id]
        pipeline.is_started = False
    return web.json_response({})


def clear(context: Context):
    if context.session_id in session_id_2_pipeline:
        del session_id_2_pipeline[context.session_id]
        del session_id_2_test_manager[context.session_id]

    recorder = Recorder(config, context.session_id)
    recorder.close()


async def query_session(request):
    data = await request.json()
    model: SessionModel = await SessionModel.filter(session_id=data["session_id"]).first()
    print(model)
    return web.json_response({"model": model.to_json()})


app = web.Application()
app.add_routes([web.post('/start', start),
                web.post('/handle_api_results', handle_api_results),
                web.post('/finishTask', finish_task),
                web.post('/stopTask', stop_task),
                web.post('/query_session', query_session)])

# Set up the database initialization and closing hooks
app.on_startup.append(init_server)
app.on_cleanup.append(close_server)

if __name__ == '__main__':
    load_model_config("embed_model_config.json")
    index_manager.build_indexes()
    web.run_app(app, port=5000)
