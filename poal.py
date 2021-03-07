import json
import os
from json import JSONDecodeError
from urllib.parse import urljoin

from hexlib.env import get_web
from hexlib.log import logger

from post_process import get_links_from_body
from state import PoalState

PF_MAX_PAGE = int(os.environ.get("PF_MAX_PAGE", 9999999))


class PoalHelper:

    def __init__(self, url, boards):
        self._boards = boards
        self._url = url

    def item_unique_id(self, item):
        item_type = self.item_type(item)
        if item_type == "post":
            return item["pid"]
        if item_type == "comment":
            return item["cid"]

        return item["uid"]

    def item_urls(self, item):
        item_type = self.item_type(item)
        if item_type == "post":
            urls = [
                item["link"],
                *(get_links_from_body(item["content"]) if item["content"] else [])
            ]
            if item["thumbnail"]:
                urls.append(urljoin("https://poal.co/static/thumbs/", item["thumbnail"]))
            return urls
        return get_links_from_body(item["content"]) if item["content"] else []

    def item_type(self, item):
        if "cid" in item:
            return "comment"
        if "pid" in item:
            return "post"
        return "user"

    def item_user(self, item):
        return (item["user"], item["uid"]) if "uid" in item and item["user"] != "[Deleted]" else (None, None)

    def boards(self):
        return [b.replace("\\_", "_") for b in self._boards if not b.startswith("_")]

    def posts_url(self, board, page=1):
        return "%s/api/getPostList/%s/new/%d" % (self._url, board, page)

    def comments_url(self, post_id, page=1):
        return "%s/api/getPostComments/%s/%d" % (self._url, str(post_id), page)

    def user_url(self, username):
        return "%s/api/getUser/%s" % (self._url, username)

    def parse_posts_list(self, r, board):
        try:
            j = json.loads(r.content.decode('utf-8', 'ignore'))
            if "posts" not in j:
                logger.warning("No posts in response for %s: %s" % (r.url, r.text,))
                return [], None
        except JSONDecodeError:
            logger.warning("JSONDecodeError for %s:" % (r.url,))
            logger.warning(r.text)
            return [], None

        posts = j["posts"]
        if len(posts) == 25:
            if len(r.history):
                page = 1
            else:
                page = int(r.url.split("/")[-1])
            if page + 1 > PF_MAX_PAGE:
                return posts, None
            return posts, self.posts_url(board, page=page + 1)
        return posts, None

    def parse_comments(self, r):
        try:
            j = json.loads(r.content.decode('utf-8', 'ignore'))
        except JSONDecodeError:
            logger.warning("JSONDecodeError for %s:" % (r.url,))
            logger.warning(r.text)
            return []

        comments = j["comments"]
        if len(comments) == 50:
            if len(r.history):
                pid = int(r.url.split("/")[-1])
                page = 1
            else:
                pid = int(r.url.split("/")[-2])
                page = int(r.url.split("/")[-1])
            return comments, self.comments_url(pid, page=page + 1)
        return comments, None


class PoalScanner:

    def __init__(self, state: PoalState, helper: PoalHelper):
        self._state = state
        self._helper = helper
        self._web = get_web()

    def _posts(self, board):
        r = self._web.get(self._helper.posts_url(board))
        if not r or r.status_code != 200:
            return []

        while True:
            threads, next_url = self._helper.parse_posts_list(r, board)
            for thread in threads:
                yield thread
            if not next_url:
                break
            r = self._web.get(next_url)
            if not r or r.status_code != 200:
                break

    def _fetch_comments(self, post):
        r = self._web.get(self._helper.comments_url(post["pid"]))
        if not r or r.status_code != 200:
            return []

        while True:
            comments, next_url = self._helper.parse_comments(r)
            for comment in comments:
                yield comment
            if not next_url:
                break
            r = self._web.get(next_url)
            if not r or r.status_code != 200:
                break

    def _fetch_user(self, username):
        r = self._web.get(self._helper.user_url(username))
        if not r or r.status_code != 200:
            return None
        return self.parse_user(r)

    def parse_user(self, r):
        try:
            j = json.loads(r.content.decode('utf-8', 'ignore'))
            if "error" in j:
                return None
            return j
        except JSONDecodeError:
            logger.warning("JSONDecodeError for %s:" % (r.url,))
            logger.warning(r.text)

    def _fetch_user_from_item(self, item):
        user, uid = self._helper.item_user(item)
        if user and not self._state.has_visited_user(uid):
            j = self._fetch_user(user)
            if j and "user" in j:
                j["user"]["uid"] = uid
                self._state.mark_user_as_visited(uid)
                return j["user"]
        return None

    def all_items(self):
        for board in self._helper.boards():
            for post in self._posts(board):
                cur_board = post["sub"]
                yield post, cur_board

                user = self._fetch_user_from_item(post)
                if user:
                    yield user, cur_board

                if self._state.has_new_comments(post, self._helper):
                    for comment in self._fetch_comments(post):
                        yield comment, cur_board
                        user = self._fetch_user_from_item(post)
                        if user:
                            yield user, cur_board
                    self._state.mark_post_as_visited(post, self._helper)
