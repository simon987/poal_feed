from hexlib.db import VolatileState, VolatileBooleanState


class PoalState:
    def __init__(self, prefix):
        self._posts = VolatileState(prefix)
        self._comments = VolatileBooleanState(prefix)
        self._users = VolatileBooleanState(prefix)

    def has_visited(self, item_id):
        return self._comments["comments"][item_id]

    def mark_visited(self, item_id):
        self._comments["comments"][item_id] = True

    def mark_post_as_visited(self, post, helper):
        self._posts["posts"][helper.item_unique_id(post)] = post["comments"]

    def has_new_comments(self, post, helper):
        comment_count = self._posts["posts"][helper.item_unique_id(post)]
        return comment_count is None or post["comments"] > comment_count

    def has_visited_user(self, uid):
        return self._users["users"][uid.replace("-", "")]

    def mark_user_as_visited(self, uid):
        self._users["users"][uid.replace("-", "")] = True
