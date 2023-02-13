import os, sys
import logging
import time
import re
from notion_client import Client
from notion_client import APIErrorCode, APIResponseError

import arxiv
import pytz

logging.getLogger().setLevel("DEBUG")

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_PAPER_DATABASE"]
notion = Client(
    auth=NOTION_TOKEN,
    log_level=logging.INFO,
)

def update_notion(properties, pid):
    print(pid, properties)
    cnt = 0
    try:
        while cnt < 3:
            notion.pages.update(page_id=pid, properties=properties)
            break
    except APIResponseError as error:
        logging.error(error)
        import time; time.sleep(3)
        cnt += 1
    return cnt < 3

def create_notion(properties):
    print(properties)
    cnt = 0
    try:
        while cnt < 3:
            notion.pages.create(parent=dict(database_id=DATABASE_ID), properties=properties)
            break
    except APIResponseError as error:
        logging.error(error)
        import time; time.sleep(3)
        cnt += 1
    return cnt < 3

process_name = lambda name: re.sub("[^A-Za-z0-9]+", "", name.upper())

PAPERS = set()
AUTHORS = set()

def load():
    with open("paper/papers", "r") as f:
        for l in f.readlines():
            name = process_name(l.strip())
            PAPERS.add(name)

    with open("paper/authors", "r") as f:
        for l in f.readlines():
            name = l.strip()
            try:
                au = name.split(";")[0].strip().title() + " ; " + name.split(";")[1].strip()
            except:
                au = name.strip().title()
            AUTHORS.add(au)
load()

def check_and_add_au(name):
    """
    Long author name: `XXXX; insitute`
    author name XXXX
    """
    if name == "": return name
    try:
        ori_name = name.split(";")[0].strip().title() + "; " + name.split(";")[1].strip()
    except:
        ori_name = name.strip().title()

    for _au in AUTHORS:
        if _au.startswith(ori_name) or ori_name.startswith(_au):
            if len(ori_name) > len(_au) and ori_name not in AUTHORS:
                AUTHORS.remove(_au)
                AUTHORS.add(ori_name)
                logging.info(f"authors add {ori_name}, pop {_au}")
            return _au
    else:
        AUTHORS.add(ori_name)
        logging.info(f"authors add {ori_name}")
        return ori_name

notion_pages = dict()
def get_paper_notion():
    cursor = None
    while True:
        try:
            database = notion.databases.query(
                database_id=DATABASE_ID,
                page_size=200,
                start_cursor=cursor,
            )
        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                logging.error(error)
            else:
                # Other error handling code
                logging.error(error)
        finally:
                time.sleep(1)
        for item in database["results"]:
            p = item["properties"]
            try:
                name = p["Name"]["title"][0]["plain_text"]
                name = process_name(name)
            except:
                continue
            try:
                for i in p["Authors"]["multi_select"]:
                    i["name"] = check_and_add_au(i["name"])
            except:
                pass

            PAPERS.add(name)
            notion_pages[name] = (item["id"], p,)
        if not database["has_more"]:
            break
        cursor = database["next_cursor"]
get_paper_notion()

def update_authors():
    def process_authors(properties):
        _process_authors = lambda authors: [i.strip() for i in authors.replace(" and ", ", ").split(",")]
        authors = []
        try:
            for au in _process_authors(properties["authors"]["rich_text"][0]["text"]["content"]):
                new_au = check_and_add_au(au)
                if new_au != au:
                    authors.append(new_au)
            return authors
        except:
            pass

        try:
            for i in properties["Authors"]["multi_select"]:
                au = i["name"]
                new_au = check_and_add_au(au)
                if new_au != au:
                    logging.warning(f"new author name: {new_au} author name: {au}")
        except:
            pass
        return []

    # 1 first update relative authors
    for _, (pid, properties) in notion_pages.items():
        new_authors = process_authors(properties)
        if len(new_authors) == 0:
            continue
        update_notion({
            "Authors": {'type': 'multi_select', 'multi_select': [{'name': x} for x in new_authors]},
            'authors': {'type': 'rich_text', 'rich_text': []},
        }, pid)
update_authors()

arxiv_map = {}
def update_by_arxiv():
    search = arxiv.Search(
        query='all:"speech recognition"',
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    for result in search.results():
        name = process_name(result.title)
        if name in PAPERS:
            print(name, "is added")
            continue


        # result.entry_id: A url http://arxiv.org/abs/{id}.
        # result.updated: When the result was last updated.
        # result.published: When the result was originally published.
        # result.title: The title of the result.
        # result.authors: The result's authors, as arxiv.Authors.
        # result.summary: The result abstract.
        # result.comment: The authors' comment if present.
        # result.journal_ref: A journal reference if present.
        # result.doi: A URL for the resolved DOI to an external resource if present.
        # result.primary_category: The result's primary arXiv category. See arXiv: Category Taxonomy.
        # result.categories: All of the result's categories. See arXiv: Category Taxonomy.
        # result.links: Up to three URLs associated with this result, as arxiv.Links.
        # result.pdf_url: A URL for the result's PDF if present. Note: this URL also appears among result.links.
        others = f"comment:{result.comment}\ndoi:{result.doi}\njournal_ref:{result.journal_ref}"

        properties = {
            "Name": {"id": "title", "type": "title", "title": [{'type': 'text', 'text': {'content': result.title}}]},
            "bibtexs": {"type": "rich_text", "rich_text": []},
            "conference": {
                "type": "select",
                "select": {
                    "name": "arxiv",
                },
            },
            "Method": {"type": "files", "files": []},
            "Date": {"type": "date", "date": {"start": result.updated.astimezone(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d"), "end": None, "time_zone": None}},
            # {'id': 'Th%7Bt', 'type': 'date', 'date': {'start': '2022-11-02T00:00:00.000+08:00', 'end': None, 'time_zone': None}}
            "Highlight": {"type": "rich_text", "rich_text": []},
            "Reader": {"type": "multi_select", "multi_select": []},
            "URL": {"type": "url", "url": result.pdf_url},
            "Authors": {"type": "multi_select", "multi_select": [{"name": check_and_add_au(au.name)} for au in result.authors]},
            "Keys": {"type": "multi_select", "multi_select": []},

            "keywords": {"type": "multi_select", "multi_select": []},
            "authors": {"type": "rich_text", "rich_text": []},
            "abstracts": {"type": "rich_text", "rich_text": [{'type': 'text', 'text': {'content': result.summary}}]},
            "sessions": {"type": "select", "select": None},
            "others": {"type": "rich_text", "rich_text": [{'type': 'text', 'text': {'content': others}}]},
        }
        print(properties)
        if create_notion(properties):
            PAPERS.add(name)
update_by_arxiv()


def save():
    global PAPERS, AUTHORS
    PAPERS = sorted(list(PAPERS))
    with open("paper/papers", "w") as f:
        for k in PAPERS:
            f.write(f"{k}\n")
    AUTHORS = sorted(list(AUTHORS))
    with open("paper/authors", "w") as f:
        for k in AUTHORS:
            f.write(f"{k}\n")
save()
