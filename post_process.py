from hexlib.regex import LINK_RE


def post_process(item, board, helper):
    item["_v"] = 1.0
    item["_id"] = helper.item_unique_id(item)

    if helper.item_type(item) != "user":
        item["_urls"] = helper.item_urls(item)
    if helper.item_type(item) == "comment":
        item["_sub"] = board

    return item


def get_links_from_body(body):
    result = []

    for match in LINK_RE.finditer(body):
        url = match.group(1)
        result.append(url)
    return result
