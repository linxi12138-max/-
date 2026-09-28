# 家庭点餐

家庭菜品浏览、评分和点餐记录应用，基于 Flask 与 SQLite。

## 本地运行

```powershell
cd 菜单
python -m pip install -r requirements.txt
$env:FLASK_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
$env:ADMIN_PASSWORD = "222313" # 可选；项目默认管理员密码已设为 222313
python app.py
```

访问 http://127.0.0.1:5000。首次启动会自动创建 `instance/family_menu.db` 并填入家庭菜单。管理登录地址为 `/admin/login`；默认管理员密码为 `222313`。如果未设置 `FLASK_SECRET_KEY`，本地开发会使用内置默认值；正式部署必须设置随机的 `FLASK_SECRET_KEY` 和 `ADMIN_PASSWORD`。

可设置 `$env:SESSION_COOKIE_SECURE = "1"` 来仅通过 HTTPS 发送登录 Cookie。仅在 HTTPS 部署时启用。

## 推送到 GitHub

在项目目录初始化 Git 并提交代码：

```bash
git init
git add .
git status
git commit -m "Initial family menu app"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库.git
git push -u origin main
```

`.gitignore` 会排除 `instance` 中的 SQLite 数据库和 `static/uploads` 中的用户上传图片，同时保留项目现有的 `static/placeholder.svg`（以及上传目录内同名占位图）。本项目为便于家庭使用，代码默认管理员密码为 `222313`；如果仓库或网站对外公开，请务必在部署平台用 `ADMIN_PASSWORD` 环境变量覆盖它，并不要将正式 `FLASK_SECRET_KEY` 写入仓库。

> GitHub Pages 只能托管静态文件，不能运行本项目所需的 Flask/Python/SQLite 后端。因此 GitHub 适合保存与发布源码；要让点餐、登录、评分和管理功能真正可用，请按下方 PythonAnywhere（或任意 Python 托管平台）步骤部署。

## 部署到 PythonAnywhere

1. 在 PythonAnywhere 创建 Web 应用，选择与你本地兼容的 Python 版本和手动 Flask 配置。
2. 在 Bash Console 克隆仓库到你的 home 目录，并创建虚拟环境、安装依赖：

	```bash
	cd ~
	git clone https://github.com/你的用户名/你的仓库.git
	cd 你的仓库
	mkvirtualenv --python=/usr/bin/python3.11 family-menu
	pip install -r requirements.txt
	```

	将 `python3.11` 替换为 Web 应用所选的 Python 版本。
3. 在 Web 页面设置 virtualenv 路径为 `/home/你的用户名/.virtualenvs/family-menu`，并将项目目录加入 Python path。
4. 编辑 WSGI 配置文件，在导入应用前设置环境变量并载入 `app` 对象：

	```python
	import os
	import sys

	project_dir = "/home/你的用户名/你的仓库"
	if project_dir not in sys.path:
		 sys.path.insert(0, project_dir)

	os.environ["FLASK_SECRET_KEY"] = "替换为随机长密钥"
	os.environ["ADMIN_PASSWORD"] = "替换为强管理员密码"
	os.environ["SESSION_COOKIE_SECURE"] = "1"

	from app import app as application
	```

	请只在 PythonAnywhere 的 WSGI 配置中填写部署密钥，不要提交到 GitHub。应用导入时会自动创建 `instance` 目录、SQLite 数据库和上传目录。
5. 在 Static files 配置中添加 URL `/static/` 到项目的 `static` 目录映射。完成后 Reload Web App，并访问 PythonAnywhere 提供的域名。

数据库和上传文件保存在项目目录中，重新部署代码时不要删除 `instance` 或 `static/uploads`；建议定期备份 SQLite 数据库及上传图片。不要在生产环境开启 Flask debug 模式。
