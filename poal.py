from bs4 import BeautifulSoup
from hexlib.env import get_web

from state import PoalState


class PoalScanner:

    def __init__(self, state: PoalState):
        self._state = state
        self._web = get_web()

    def _parse_post(self, r, soup, pid):
        sub = r.url.split("/")[-2]

        post = {
            "_id": pid,
            "pid": pid,
            "sub": sub,
        }

        try:
            post["user"] = soup.find("div", class_="postinfo").find("a", href=lambda x: x and x.startswith("/u/")).text
        except:
            post["user"] = "[deleted]"

        post["score"] = int(soup.find("div", class_="score").text)
        post["title"] = soup.find("a", id="title").text.strip()
        post["link"] = soup.find("a", id="title").get("href")

        post["upvotes"] = int(soup.find("a", class_="pscorep").text)
        post["downvotes"] = int(soup.find("a", class_="pscoren").text)

        post["posted"] = soup.find("div", id="postinfo").find("time-ago").get("datetime")
        content_elem = soup.find("div", id="postcontent")
        if content_elem:
            post["content"] = str(content_elem)

        return post

    def _parse_comments(self, r, soup, pid):

        for comment_elem in soup.find_all("article"):
            sub = r.url.split("/")[-2]

            comment = {
                # Save v2 comments on purpose because we save the parent_pid field and not in v1
                "_id": "v2_" + comment_elem.get("id"),
                "_sub": sub,
                "cid": comment_elem.get("id"),
                "parent_pid": pid,
                "content": str(comment_elem.find("div", class_="content")),
                "posted": comment_elem.find("time-ago").get("datetime")
            }

            comment_head = comment_elem.find("div", class_="commenthead")
            author_elem = comment_head.find("a", href=lambda x: x and x.startswith("/u/"))
            if author_elem:
                comment["user"] = author_elem.text
            else:
                comment["user"] = "[deleted]"

            parent_elem = comment_elem.parent
            if parent_elem.get("id").startswith("child"):
                comment["parentcid"] = parent_elem.get("id")[len("child-"):]

            yield comment

    def all_items(self):
        not_found_in_a_row = 0

        for pid in range(1, 500_000):
            if self._state.has_visited(pid):
                continue
            url = f"https://poal.co/s/all/{pid}"

            r = self._web.get(url)
            if r.status_code == 404:
                not_found_in_a_row += 1

                if not_found_in_a_row > 10:
                    break

                if self._state.has_visited(pid + 1):
                    self._state.mark_visited(pid)

                continue

            not_found_in_a_row = 0

            if r.status_code == 406:
                # " This sub is disabled You're not allowed to see this stuff"
                self._state.mark_visited(pid)
                continue

            soup = BeautifulSoup(r.content, "html.parser")

            yield self._parse_post(r, soup, pid), "post"

            for com in self._parse_comments(r, soup, pid):
                yield com, "comment"

            self._state.mark_visited(pid)
