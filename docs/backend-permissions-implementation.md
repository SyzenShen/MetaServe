# 后端分层权限实现步骤（执行说明）

本文档概述在现有 `file_upload` / `file_download` 应用中实现分层权限与用户层级的具体执行步骤。目标是让前端已有的权限配置在后端落地，支持组织、成员角色、资源共享和访问控制。

## 1. 范围与目标
- 为上传/下载、文件夹浏览、搜索等接口提供一致的权限校验。
- 支持用户层级：组织（Organization）与成员关系（Membership/Role）。
- 支持资源共享：面向用户和公共链接（后续可扩展时限/一次性链接）。
- 与现有 `File.access_level`（Public/Internal/Restricted）协同工作。

## 2. 数据模型
在 `authentication` 或独立新应用中新增以下模型（建议放在 `authentication` 中，避免额外 app）：

- Organization：名称、创建者、创建时间。
- Membership：`user` 与 `organization` 的关联，含 `role`（Owner/Admin/Member/Viewer）。
- FileShare：文件共享记录，支持共享到 `user` 或 `organization`，并可设置到期时间；可选 `can_download`、`can_edit_metadata`。

说明：
- `File` 与 `Folder` 保持现有结构不变；通过 `FileShare` 和 `File.access_level` 决定访问范围。
- 后续可扩展 `FolderShare`，当前版本仅对 `File` 做共享控制。

## 3. 权限判定策略
统一权限函数 `can_view_file(user, file)` / `can_download_file(user, file)`：

1) 超级用户（`is_superuser`）直接允许。
2) 文件拥有者（`file.user == user`）允许。
3) `file.access_level == Public` 允许任何已登录用户查看，下载可选限制（按需调整）。
4) `Internal` 仅同组织成员允许：判断用户与文件拥有者是否存在同一个 `Organization` 的 `Membership`。
5) `Restricted` 仅显式共享允许：存在 `FileShare` 面向该 `user` 或其所在 `organization`。

备注：如果文件位于某 `Folder`，可在后续版本引入文件夹级共享；当前以文件为主。

## 4. DRF 权限类与工具
- 新建 `permissions.py`：
  - `IsFileReadable`：用于 `GET file_list / file_download` 的对象级校验。
  - `IsFolderReadable`：用于 `folder_detail/list` 的校验（当前仅返回自己的资源，若开放内部可在此扩展）。
- 新建 `permission_utils.py`：封装上述 `can_*` 逻辑与组织成员判定函数。

## 5. 接口接入点
- `file_upload/api_views.py`：
  - `file_list`：目前仅返回 `request.user` 的资源；若要支持同组织浏览，需加入基于 `Internal` / `Restricted` 的合并查询与筛选（本迭代先维持自己的资源）。
  - `file_download(file_id)`：替换直接 `File.objects.get(id=file_id, user=request.user)` 的查询，改为按权限函数判定对象级访问。
  - 其他如 `folder_detail`、`folder_all`：保持现状；如需开放组织内访问再扩展。

## 6. 迁移与回滚
- 为新增模型生成迁移：`python manage.py makemigrations`。
- 执行迁移：`python manage.py migrate`。
- 回滚：使用 `python manage.py migrate <app> <previous_migration>`。

## 7. 前端协作点
- 前端保持 Token 认证不变。
- 若要展示共享到我的文件列表，需要新增接口（后续迭代）。
- 现阶段：下载接口按权限返回 403/404，前端据此反馈。

## 8. 实施步骤（本次迭代）
1) 在 `authentication/models.py` 中新增 `Organization` 与 `Membership` 模型。
2) 在 `file_upload/models.py` 中新增 `FileShare` 模型。
3) 新增 `file_upload/permission_utils.py` 与 `file_upload/permissions.py` 实现权限判断与 DRF 权限类。
4) 更新 `file_upload/api_views.py` 的 `file_download` 使用权限工具检查对象可见性；保留 `file_list` 仅返回自己的资源以保持行为稳定。
5) 生成并执行迁移。
6) 验证：
   - 资源所有者可下载。
   - 同组织成员对 `Internal` 可下载（若允许）。
   - `Restricted` 仅共享对象可下载。
   - `Public` 已登录用户可下载（或仅查看，按策略设置）。

## 9. 后续扩展（非本迭代）
- 组织级列表与搜索（展示组织共享的资源）。
- 文件夹共享与继承规则。
- 临时下载链接（一次性或限时）。
- 审计日志（谁在何时下载了什么）。