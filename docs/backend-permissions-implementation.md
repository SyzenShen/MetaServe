# 后端分层权限实现步骤（执行说明） / Backend Layered Permission Implementation Steps (Execution Guide)

本文档概述在现有 `file_upload` / `file_download` 应用中实现分层权限与用户层级的具体执行步骤。目标是让前端已有的权限配置在后端落地，支持组织、成员角色、资源共享和访问控制。
<br>This document outlines the specific execution steps to implement layered permissions and user hierarchy in the existing `file_upload` / `file_download` application. The goal is to implement the frontend permission configurations in the backend, supporting organizations, member roles, resource sharing, and access control.

## 1. 范围与目标 / Scope and Objectives
- 为上传/下载、文件夹浏览、搜索等接口提供一致的权限校验。
  <br>Provide consistent permission validation for upload/download, folder browsing, search, and other interfaces.
- 支持用户层级：组织（Organization）与成员关系（Membership/Role）。
  <br>Support user hierarchy: Organization and Membership/Role.
- 支持资源共享：面向用户和公共链接（后续可扩展时限/一次性链接）。
  <br>Support resource sharing: User-facing and public links (extensible for time-limited/one-time links).
- 与现有 `File.access_level`（Public/Internal/Restricted）协同工作。
  <br>Work in synergy with existing `File.access_level` (Public/Internal/Restricted).

## 2. 数据模型 / Data Models
在 `authentication` 或独立新应用中新增以下模型（建议放在 `authentication` 中，避免额外 app）：
<br>Add the following models in `authentication` or a new independent app (recommended in `authentication` to avoid extra apps):

- Organization：名称、创建者、创建时间。
  <br>Organization: Name, Creator, Creation Time.
- Membership：`user` 与 `organization` 的关联，含 `role`（Owner/Admin/Member/Viewer）。
  <br>Membership: Association between `user` and `organization`, containing `role` (Owner/Admin/Member/Viewer).
- FileShare：文件共享记录，支持共享到 `user` 或 `organization`，并可设置到期时间；可选 `can_download`、`can_edit_metadata`。
  <br>FileShare: File sharing record, supports sharing to `user` or `organization`, with expiration time; optional `can_download`, `can_edit_metadata`.

说明 / Notes:
- `File` 与 `Folder` 保持现有结构不变；通过 `FileShare` 和 `File.access_level` 决定访问范围。
  <br>`File` and `Folder` structures remain unchanged; access scope is determined by `FileShare` and `File.access_level`.
- 后续可扩展 `FolderShare`，当前版本仅对 `File` 做共享控制。
  <br>`FolderShare` can be extended later; current version controls sharing only for `File`.

## 3. 权限判定策略 / Permission Determination Strategy
统一权限函数 `can_view_file(user, file)` / `can_download_file(user, file)`：
<br>Unified permission functions `can_view_file(user, file)` / `can_download_file(user, file)`:

1) 超级用户（`is_superuser`）直接允许。
   <br>Superuser (`is_superuser`) allowed directly.
2) 文件拥有者（`file.user == user`）允许。
   <br>File owner (`file.user == user`) allowed.
3) `file.access_level == Public` 允许任何已登录用户查看，下载可选限制（按需调整）。
   <br>`file.access_level == Public` allows any logged-in user to view; download optional restriction (adjust as needed).
4) `Internal` 仅同组织成员允许：判断用户与文件拥有者是否存在同一个 `Organization` 的 `Membership`。
   <br>`Internal` allowed only for same-organization members: Check if user and file owner share a `Membership` in the same `Organization`.
5) `Restricted` 仅显式共享允许：存在 `FileShare` 面向该 `user` 或其所在 `organization`。
   <br>`Restricted` allowed only via explicit sharing: Existence of `FileShare` targeting the `user` or their `organization`.

备注：如果文件位于某 `Folder`，可在后续版本引入文件夹级共享；当前以文件为主。
<br>Note: If a file is in a `Folder`, folder-level sharing can be introduced in future versions; currently focuses on files.

## 4. DRF 权限类与工具 / DRF Permission Classes & Utilities
- 新建 `permissions.py` / Create `permissions.py`:
  - `IsFileReadable`：用于 `GET file_list / file_download` 的对象级校验。
    <br>`IsFileReadable`: For object-level validation in `GET file_list / file_download`.
  - `IsFolderReadable`：用于 `folder_detail/list` 的校验（当前仅返回自己的资源，若开放内部可在此扩展）。
    <br>`IsFolderReadable`: For validation in `folder_detail/list` (currently returns only own resources; extend here if opening internal access).
- 新建 `permission_utils.py`：封装上述 `can_*` 逻辑与组织成员判定函数。
  <br>Create `permission_utils.py`: Encapsulate the above `can_*` logic and organization member determination functions.

## 5. 接口接入点 / Interface Integration Points
- `file_upload/api_views.py`:
  - `file_list`：目前仅返回 `request.user` 的资源；若要支持同组织浏览，需加入基于 `Internal` / `Restricted` 的合并查询与筛选（本迭代先维持自己的资源）。
    <br>`file_list`: Currently returns only `request.user` resources; to support browsing within the organization, add merged query and filtering based on `Internal` / `Restricted` (maintain own resources for this iteration).
  - `file_download(file_id)`：替换直接 `File.objects.get(id=file_id, user=request.user)` 的查询，改为按权限函数判定对象级访问。
    <br>`file_download(file_id)`: Replace direct `File.objects.get(id=file_id, user=request.user)` query with object-level access determination via permission functions.
  - 其他如 `folder_detail`、`folder_all`：保持现状；如需开放组织内访问再扩展。
    <br>Others like `folder_detail`, `folder_all`: Maintain status quo; extend if organization access is needed.

## 6. 迁移与回滚 / Migration & Rollback
- 为新增模型生成迁移：`python manage.py makemigrations`。
  <br>Generate migrations for new models: `python manage.py makemigrations`.
- 执行迁移：`python manage.py migrate`。
  <br>Execute migrations: `python manage.py migrate`.
- 回滚：使用 `python manage.py migrate <app> <previous_migration>`。
  <br>Rollback: Use `python manage.py migrate <app> <previous_migration>`.

## 7. 前端协作点 / Frontend Collaboration Points
- 前端保持 Token 认证不变。
  <br>Frontend maintains Token authentication unchanged.
- 若要展示共享到我的文件列表，需要新增接口（后续迭代）。
  <br>To display "Shared with me" file list, a new interface is needed (future iteration).
- 现阶段：下载接口按权限返回 403/404，前端据此反馈。
  <br>Current stage: Download interface returns 403/404 based on permissions; frontend provides feedback accordingly.

## 8. 实施步骤（本次迭代） / Implementation Steps (Current Iteration)
1) 在 `authentication/models.py` 中新增 `Organization` 与 `Membership` 模型。
   <br>Add `Organization` and `Membership` models in `authentication/models.py`.
2) 在 `file_upload/models.py` 中新增 `FileShare` 模型。
   <br>Add `FileShare` model in `file_upload/models.py`.
3) 新增 `file_upload/permission_utils.py` 与 `file_upload/permissions.py` 实现权限判断与 DRF 权限类。
   <br>Add `file_upload/permission_utils.py` and `file_upload/permissions.py` to implement permission determination and DRF permission classes.
4) 更新 `file_upload/api_views.py` 的 `file_download` 使用权限工具检查对象可见性；保留 `file_list` 仅返回自己的资源以保持行为稳定。
   <br>Update `file_download` in `file_upload/api_views.py` to use permission tools for object visibility checks; keep `file_list` returning only own resources to maintain stable behavior.
5) 生成并执行迁移。
   <br>Generate and execute migrations.
6) 验证 / Verification:
   - 资源所有者可下载。 (Resource owner can download.)
   - 同组织成员对 `Internal` 可下载（若允许）。 (Same-org members can download `Internal` (if allowed).)
   - `Restricted` 仅共享对象可下载。 (`Restricted` only downloadable by shared targets.)
   - `Public` 已登录用户可下载（或仅查看，按策略设置）。 (`Public` downloadable by logged-in users (or view-only, per policy).)

## 9. 后续扩展（非本迭代） / Future Extensions (Non-Current Iteration)
- 组织级列表与搜索（展示组织共享的资源）。
  <br>Organization-level list and search (display shared resources).
- 文件夹共享与继承规则。
  <br>Folder sharing and inheritance rules.
- 临时下载链接（一次性或限时）。
  <br>Temporary download links (one-time or time-limited).
- 审计日志（谁在何时下载了什么）。
  <br>Audit logs (who downloaded what and when).