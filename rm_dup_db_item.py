import os, sys
import logging
import time
import re
logging.getLogger().setLevel("DEBUG")

# 3, access notion database
from notion_client import Client
from notion_client import APIErrorCode, APIResponseError

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_IDS = os.environ["NOTION_RM_DUP_DATABASES"].split(":")
notion = Client(auth=NOTION_TOKEN, log_level=logging.INFO,)

def dict_merge(main_dct, merge_dct):
    """merge non-exist item to main_dct"""
    for k in merge_dct.keys():
        if k == "id": continue
        try:
            if isinstance(main_dct[k], dict) and isinstance(merge_dct[k], dict):
                dict_merge(main_dct[k], merge_dct[k])
            elif main_dct[k] is None or len(main_dct[k]) == 0: # "" or None or [] ...
                main_dct[k] = merge_dct[k]
            elif type(main_dct[k]) == list: # merge multi select only
                if k == "multi_select":
                    main_dct[k].extend(merge_dct[k])
                else:
                    pass
        except Exception as e:
            logging.error(e)

def process_db(db_id):
    notion_pagedata = dict()
    updateids_map = set()
    pageids_map = set()
    # db = notion.databases.retrieve(
    #     database_id=DATABASE_ID,
    # )
    cursor = None
    while True:
        try:
            database = notion.databases.query(
                database_id=db_id,
                # filter={"property": "Name"},
                page_size=200,
                start_cursor=cursor,
            )
        except APIResponseError as error:
            # if error.code == APIErrorCode.ObjectNotFound:
            logging.error(error)
        else:
            for item in database["results"]:
                print(item["properties"]["Name"])
                name:str = item["properties"]["Name"]["title"][0]["plain_text"]
                name = re.sub('[^A-Za-z0-9]+', '', name.upper())
                item["properties"].pop("Name")

                if name in notion_pagedata:
                    pageids_map.add(item["id"])
                    updateids_map.add(name)

                    def get_url(_property):
                        # priority: arxiv < manually add items
                        # url has more priority
                        try:
                            url = _property["URL"]["url"]
                            if url.startswith("https://arxiv"): url = ""
                        except:
                            url = ""
                        return url
                    logging.info(f"\n\t{item}\n\t{notion_pagedata[name]}")

                    if get_url(item["properties"]) < get_url(notion_pagedata[name]["properties"]):
                        dict_merge(notion_pagedata[name]["properties"], item["properties"])
                    else:
                        dict_merge(item["properties"], notion_pagedata[name]["properties"])
                        notion_pagedata[name]["properties"] = item["properties"]
                    logging.info(f"{name}"+ str(notion_pagedata[name]["properties"]))
                else:
                    notion_pagedata[name] = item
            logging.info(f"{cursor}: "+str(len(database["results"])))
            if not database["has_more"]: break
            cursor = database["next_cursor"]
        finally:
            time.sleep(1)
    
    logging.info(f"Remove pageids: {pageids_map}")
    for pageid in pageids_map:
        notion.blocks.delete(pageid)
        time.sleep(0.5)

    logging.info(f"Update pageids: {updateids_map}")
    for pagename in updateids_map:
        page = notion_pagedata[pagename]
        notion.pages.update(page_id=page["id"], properties=page["properties"])
        time.sleep(0.5)

for db_id in DATABASE_IDS:
    if db_id == "":
        continue
    process_db(db_id)
