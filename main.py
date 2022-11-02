import os, sys
import logging

# 1, load repos
REPOS = set()
with open("repos", "r") as f:
    for l in f.readlines():
        REPOS.add(l.strip())
print("local:", REPOS)

# 2, access github information
from github import Github
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
g = Github(GITHUB_TOKEN)

repo_infos = {name:g.get_repo(name) for name in REPOS}

print([(k,v) for k,v in repo_infos.items()])

# 3, access notion database
from notion_client import Client
from notion_client import APIErrorCode, APIResponseError

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE"]
notion = Client(auth=NOTION_TOKEN, log_level=logging.DEBUG,)

notion_pageids = set()
pageids_map = dict()
# db = notion.databases.retrieve(
#     database_id=DATABASE_ID,
# )
try:
    cursor = None
    while True:
        database = notion.databases.query(
            database_id=DATABASE_ID,
            # filter={"property": "Name"},
            page_size=200,
            start_cursor=cursor,
        )
        for item in database["results"]:
            name = item["properties"]["Name"]["title"][0]["plain_text"]
            pageids_map[name] = item["id"]
            notion_pageids.add(name)
        if not database["has_more"]: break
        cursor = database["next_cursor"]
except APIResponseError as error:
    if error.code == APIErrorCode.ObjectNotFound:
        logging.error(error)
    else:
        # Other error handling code
        logging.error(error)

# 4, filter already in notion / new in notion
new_pageids = REPOS.difference(notion_pageids)
cur_pageids = REPOS.intersection(notion_pageids)
print("\n\n\nNEED:", REPOS, "NOTION:", notion_pageids)
print("NEW:", new_pageids, "OLD:", cur_pageids, "\n\n\n")
# 'properties': {'Stars': {'id': 'EgbH', 'type': 'number', 'number': 123}, 'Commit': {'id': 'Th%7Bt', 'type': 'date', 'date': {'start': '2022-11-02T00:00:00.000+08:00', 'end': None, 'time_zone': None}}, 'Keywords': {'id': 'lE%3Fk', 'type': 'multi_select', 'multi_select': [{'id': '762d5de3-ae8f-47e3-85ad-77522066ea7b', 'name': 'ASR', 'color': 'purple'}, {'id': '3866d2f8-adb2-4018-8ed8-148f21bb7c4c', 'name': 'E2E', 'color': 'brown'}]}, 'URL': {'id': 'qF%5Dn', 'type': 'url', 'url': 'https://gg.com'}, 'Description': {'id': '%7DnDg', 'type': 'rich_text', 'rich_text': [{'type': 'text', 'text': {'content': 'aaaa', 'link': None}, 'annotations': {'bold': False, 'italic': False, 'strikethrough': False, 'underline': False, 'code': False, 'color': 'default'}, 'plain_text': 'aaaa', 'href': None}]}, 'Name': {'id': 'title', 'type': 'title', 'title': [{'type': 'text', 'text': {'content': 'test', 'link': None}, 'annotations': {'bold': False, 'italic': False, 'strikethrough': False, 'underline': False, 'code': False, 'color': 'default'}, 'plain_text': 'test', 'href': None}]}}, 'url': 'https://www.notion.so/test-fc43d4a9b3a54096bec9790de0a19f3a'}

import pytz
# 5, update
for pageid in new_pageids:
    repo =  repo_infos[pageid]
    properties = {
        'Name': {'id': 'title', 'type': 'title', 'title': [
            {'type': 'text', 'text': {'content': repo.full_name}},
        ]},
        'Stars': {'type': 'number', 'number': repo.stargazers_count}, 
        'Commit': {'type': 'date', 'date': {'start': repo.pushed_at.astimezone(pytz.timezone("Asia/Shanghai")).strftime("2022-11-02")}},

        'Keywords': {'type': 'multi_select', 'multi_select': [{"name": i} for i in repo.topics]},
        'URL': {'type': 'url', 'url': "https://github.com/" + repo.full_name},
        'Description': {'type': 'rich_text', 'rich_text': [{'type': 'text', 'text': {'content': repo.description}}]},
    }
    cnt = 0
    try:
        while cnt < 3:
            notion.pages.create(parent=dict(database_id=DATABASE_ID), properties=properties)
    except APIResponseError as error:
        logging.error(error)
        import time; time.sleep(3)
        cnt += 1

for pageid in cur_pageids:
    repo =  repo_infos[pageid]
    properties = {
        'Name': {'id': 'title', 'type': 'title', 'title': [
            {'type': 'text', 'text': {'content': repo.full_name}},
        ]},
        'Stars': {'type': 'number', 'number': repo.stargazers_count}, 
        'Commit': {'type': 'date', 'date': {'start': repo.pushed_at.astimezone(pytz.timezone("Asia/Shanghai")).strftime("2022-11-02")}},
    }
    # print(pageid, properties)
    cnt = 0
    try:
        while cnt < 3:
            notion.pages.update(page_id=pageids_map[pageid], properties=properties)
    except APIResponseError as error:
        logging.error(error)
        import time; time.sleep(3)
        cnt += 1