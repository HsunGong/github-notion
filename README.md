##  Github Action: Github-repos to Notion

参考于 https://github.com/lcjnil/github-notion-star

优化：
- 全python执行
- 不需要github-token
- 自定义repo

## 设置

- 在 Notion 上复制这个[模板](https://lcj.notion.site/Github-Notion-Star-f07e2f086e4d4f5b9f25693814c836de)
- Fork 当前的这个 Repo
- 在 Repo 的设置里面，新建一个名为 notion-sync 的 Environment，需要设置以下环境变量
    - `NOTION_API_KEY` 申请的 Notion API 的 Key，注意，你的模板需要被共享给这个 API
    - `NOTION_DATABASE_ID` 对应的 Notion Database ID

<details><summary>如何找到 NOTION_API_KEY？</summary>
请参考：https://www.notion.so/Add-and-manage-integrations-with-the-API-910ac902372042bc9da38d48171269cd#eeaa235ffe834d4f9a89a5893398f341
</details>

<details><summary>如何找到 NOTION DATABASE ID</summary>
请参考：https://stackoverflow.com/questions/67728038/where-to-find-database-id-for-my-database-in-notion
</details>
