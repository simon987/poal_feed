import json

from hexlib.env import get_redis, redis_publish

from poal import PoalScanner
from state import PoalState


def publish(item, item_type):
    item["_v"] = 2.0

    board = item["_sub"] if "_sub" in item else item["sub"]
    message = json.dumps(item, separators=(',', ':'), ensure_ascii=False, sort_keys=True)

    redis_publish(
        rdb,
        item=message,
        item_type=item_type,
        item_project="poal",
        item_category=board
    )


if __name__ == "__main__":
    state = PoalState("poalv2")
    rdb = get_redis()

    s = PoalScanner(state)

    while True:
        for item, item_type in s.all_items():
            publish(item, item_type)
