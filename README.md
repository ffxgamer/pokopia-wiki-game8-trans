# Pokémon Pokopia 中文镜像

这是一个基于 Game8《Pokémon Pokopia》攻略站整理的中文静态镜像站点。

仓库内直接提交已经生成好的静态文件：

- `index.html`
- `pages/`
- `pages.json`

GitHub Pages 使用 GitHub Actions 发布，不在 CI 中重新抓取或重新生成内容。

## 在线地址

启用 GitHub Pages 后，默认访问地址为：

`https://<your-github-user>.github.io/pokopia-wiki-game8-trans/`

如果仓库名或用户名不同，请把上面的占位符替换成实际值。

## 本地预览

```bash
python3 -m http.server 8000
```

然后访问：

`http://127.0.0.1:8000/`

## 链接检查

```bash
python3 tools/link_audit.py
```

当前站点发布前应保持输出为：

```json
{}
```

## 更新方式

1. 在本地修改静态页面或维护脚本
2. 运行 `python3 tools/link_audit.py` 确认链接无误
3. 提交并 push 到 `main`
4. GitHub Actions 自动部署到 GitHub Pages

## 仓库说明

- `build_site.py`：站点生成脚本
- `tools/translate_visible_text.py`：可见文本清洗脚本
- `tools/link_audit.py`：链接审计脚本

## 发布说明

GitHub 仓库设置中请将 Pages Source 设为 `GitHub Actions`。
