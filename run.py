import json
import os
import traceback
from queue import Queue
from threading import Thread

import redis

from poal import PoalScanner, PoalHelper
from post_process import post_process
from state import PoalState
from util import logger

REDIS_HOST = os.environ.get("PF_REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("PF_REDIS_PORT", 6379)
PF_PUBLISH = os.environ.get("PF_PUBLISH", False)
PF_RPS = os.environ.get("PF_RPS", 1)

ARC_LISTS = os.environ.get("PF_ARC_LISTS", "arc").split(",")


def publish_worker(queue: Queue, helper):
    while True:
        try:
            item, board = queue.get()
            if item is None:
                break
            publish(item, board, helper)

        except Exception as e:
            logger.error(str(e) + ": " + traceback.format_exc())
        finally:
            queue.task_done()


def once(func):
    def wrapper(item, board, helper):
        if not state.has_visited(helper.item_unique_id(item)):
            func(item, board, helper)
            state.mark_visited(helper.item_unique_id(item))

    return wrapper


@once
def publish(item, board, helper):
    post_process(item, board, helper)

    item_type = helper.item_type(item)
    routing_key = "%s.%s" % (item_type, board)

    message = json.dumps(item, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
    if PF_PUBLISH:
        rdb.publish("poal." + routing_key, message)
    for arc in ARC_LISTS:
        rdb.lpush(arc + ".poal." + routing_key, message)


HELPER = PoalHelper(
    boards=(
        "all",
        # TODO: Are there hidden boards that do not show up in /all ?
    ),
    rps=PF_RPS,
    url="https://poal.co"
)

if __name__ == "__main__":

    state = PoalState("poal", REDIS_HOST, REDIS_PORT)
    rdb = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    publish_q = Queue()
    for _ in range(3):
        publish_thread = Thread(target=publish_worker, args=(publish_q, HELPER))
        publish_thread.setDaemon(True)
        publish_thread.start()

    s = PoalScanner(state, HELPER)
    while True:
        try:
            for item, board in s.all_items():
                publish_q.put((item, board))
        except KeyboardInterrupt as e:
            print("cleanup..")
            for _ in range(3):
                publish_q.put((None, None))
            break
