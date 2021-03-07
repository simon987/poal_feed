import json
from queue import Queue
from threading import Thread

from hexlib.concurrency import queue_iter
from hexlib.env import get_redis

from poal import PoalScanner, PoalHelper
from post_process import post_process
from state import PoalState


def publish_worker(queue: Queue, helper):
    for item, board in queue_iter(queue):
        publish(item, board, helper)


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
    rdb.lpush("arc.poal." + routing_key, message)


HELPER = PoalHelper(
    boards=(
        "all",
        # TODO: Are there hidden boards that do not show up in /all ?
    ),
    url="https://poal.co"
)

if __name__ == "__main__":

    state = PoalState("poal")
    rdb = get_redis()

    publish_q = Queue()
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
            publish_q.put((None, None))
            break
