# MetaServe 代码技术摸底报告（仅用于论文修订，未修改任何代码）

范围：本报告仅基于当前仓库中由 `file_project` 启动的 MetaServe 后端（`file_upload` / `file_download` / `authentication` / `ml_interface`）与配套前端（`frontend/`）进行“实现现状”核对；不对代码做任何改动，仅给出可定位到文件/函数/路由/测试的证据点与风险差异。

---

## Metadata extraction

### 1) 数据模型：哪些字段可被“自动填充/自动提取”
- 文件核心模型：`File`（[models.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/models.py#L75-L416)）
  - 手填/业务字段：`title`, `project`, `uploader`, `document_type`, `access_level`, `organism`, `experiment_type`, `tags`, `description`
  - 技术字段：`file_size`, `original_filename`, `checksum`, `file_format`
  - 自动提取承载：`extracted_metadata`（JSONField）
  - 搜索向量：`search_vector`（将若干字段拼接为小写文本，用于“简化全文搜索”）

### 2) 触发点：什么时候会跑“元数据提取”
- 普通上传：`FileUploadSerializer.create()` 调用 `_extract_metadata_async(file_obj)`（[serializers.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/serializers.py#L156-L195)）
  - 实际是同步执行（函数名叫 async，但没有线程/队列），失败仅写日志不影响上传。
  - 提取入口：`extract_file_metadata(file_obj.file.path, file_obj.file_format)`（同上）
- NCBI 导入：`ncbi_import()` 会在保存 `File` 时直接写入 `organism/experiment_type/description/extracted_metadata`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L730-L809)）
  - NCBI 侧元信息解析与下载逻辑：`download_ncbi_resource()`（[ncbi_client.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/ncbi_client.py#L400-L498)）

### 3) “实际实现”的 extractor：支持哪些格式、提了哪些字段（以 extracted_metadata keys 为准）
实现文件：`file_upload/metadata_extractor.py`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L1-L392)）

| file_format 入参 | 实现函数位置 | 实际写入 extracted_metadata 的字段（keys） |
| --- | --- | --- |
| `FASTA` | `_extract_fasta_metadata()`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L61-L108)） | `sequence_count`, `average_length`, `sample_headers`, `detected_organism`（匹配到才有） |
| `FASTQ` | `_extract_fastq_metadata()`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L110-L160)） | `read_count`, `average_read_length`, `average_quality`, `sample_headers`, `sequencing_platform`（检测到才有） |
| `VCF` | `_extract_vcf_metadata()`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L162-L198)） | `variant_count_sample`, `sample_count`, `sample_names`, `header_info` |
| `PDF` | `_extract_pdf_metadata()`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L200-L239)） | `page_count`, `text_preview`, `detected_keywords`, `pdf_info`（依赖 `pypdf`） |
| `CSV` | `_extract_csv_metadata()`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L241-L278)） | `column_count`, `separator`, `columns`, `sample_rows` |
| `txt` | `_extract_text_metadata()`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L280-L305)） | `line_count`, `word_count`, `char_count`, `preview`, `detected_keywords` |
| 其他/未命中 | `_extract_basic_metadata()`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L49-L59)） | `file_size`, `file_extension`, `extracted_at` |

### 4) NCBI 导入“额外提取”的字段（与 extracted_metadata 关系）
- 下载与 summary：`_fetch_summary()` 输出（[ncbi_client.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/ncbi_client.py#L252-L282)）
  - `title`, `organism`, `length`, `status`, `summary`, `experiment_type`, `links`
- 统一补充：`download_ncbi_resource()` 会额外注入（[ncbi_client.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/ncbi_client.py#L430-L498)）
  - `ncbi_db`, `download_bytes`, `source_url`，以及 SRA→ENA fallback 时的 `ena_mirror_urls`
- 保存到 `File`：`ncbi_import()` 将 `metadata` 同时写入 `File.extracted_metadata`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L780-L803)）

### 5) 重要实现细节/边界
- `file_format` 推断存在“大小写不一致”风险：
  - `File._detect_file_format()` 返回 `txt/csv/...` 的小写/混合值（[models.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/models.py#L265-L380)）
  - 但 `FileUploadSerializer.validate()` 的 `format_mapping` 会写入 `TXT/JPG/PNG/...` 等大写值（[serializers.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/serializers.py#L131-L146)）
  - `MetadataExtractor.extractors` 只注册了 `CSV`、`PDF`、`FASTA`、`FASTQ`、`VCF`、`txt`（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L15-L27)），因此 `TXT` 之类会直接走 basic extractor（不提关键词/行数等）。

---

## Authorization model

### 1) RBAC（组织与角色）
- 组织/成员模型：
  - `Organization` / `Membership(role=owner|admin|member|viewer)`（[authentication/models.py](file:///Users/shenyz/projects/github/Download_system_project/authentication/models.py#L58-L92)）

### 2) ABAC（属性：access_level）
- 文件属性：`File.access_level ∈ {Public, Internal, Restricted}`（[models.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/models.py#L196-L209)）
- 统一判定函数：`can_view_or_download_file(user, file)`（[permission_utils.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/permission_utils.py#L84-L105)）
  - `Public`：当前实现为“任意已登录用户可读”（未实现匿名公开）
  - `Internal`：同组织可读（`user_in_same_organization()`）+ 若父文件夹 `is_public=True` 则放行
  - `Restricted`：仅 owner 或显式共享（见 ACL）

### 3) ACL（FileShare）
- ACL 模型：`FileShare(file, shared_to_user/shared_to_organization, can_download, can_edit_metadata, expires_at)`（[models.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/models.py#L446-L471)）
- 生效判定：`FileShare.is_active()`（同上） + `has_file_share_access()`（[permission_utils.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/permission_utils.py#L24-L49)）
- 元数据编辑 ACL：`can_edit_file_metadata()`（[permission_utils.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/permission_utils.py#L51-L82)）

### 4) Most-restrictive-precedence（最严格优先）
- 组织文件夹强制 Restricted：
  - 上传后对 `parent_folder.organization` 做检测，强制 `file_obj.access_level='Restricted'`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L655-L666)）
  - 并拒绝在组织文件夹中上传 `Internal/Public`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L697-L707)）

### 5) 在哪些路由上做了对象级权限校验
- 下载：`GET /api/files/<id>/download/` → `file_download()`（[api_urls.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_urls.py#L15-L20), [api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L838-L965)）
  - 不再限定 `File.user=request.user`，改为 `can_view_or_download_file()`，并用 404 隐藏资源存在性。
- 删除：`DELETE /api/files/<id>/delete/` → `file_delete()`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L811-L836)）
  - `can_delete_file()`，同样倾向 404（隐藏存在性）。
- 列表：`GET /api/files/` → `file_list()`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L316-L383)）
  - 根目录合并“共享给我/共享给我的组织”的文件（`FileShare`）。
  - 另有“同组织 Internal 文件”单独端点：`GET /api/files/org-internal/`（[api_urls.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_urls.py#L11-L12), [api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L398-L417)）

### 6) 现有 authorization 测试覆盖位置
- 单元测试：
  - `file_upload/tests/test_permissions.py`（[test_permissions.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/tests/test_permissions.py#L9-L129)）
  - `file_upload/tests/test_security_matrix.py`（[test_security_matrix.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/tests/test_security_matrix.py)）
- 文档化的实现口径（与代码一致性需以代码为准）：[PERMISSIONS.md](file:///Users/shenyz/projects/github/Download_system_project/docs/PERMISSIONS.md)

### 7) 建议补的 authorization test cases（仅列用例，不修改代码）
- 下载对象级 404 隐藏存在性：
  - 对 `Restricted` 文件，非 owner/无 share 的用户访问 `/api/files/<id>/download/` 应为 404（已有类似断言见 [test_security_matrix.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/tests/test_security_matrix.py)）
- 组织文件夹强制 Restricted：
  - 通过真实 API 走 `POST /api/files/upload/`，在 `parent_folder` 指向组织文件夹且提交 `access_level=Internal/Public`，期望 403（对应 [api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L697-L707)）
- Restricted 权限门槛：
  - 非 owner/admin 用户提交 `access_level=Restricted` 且不提供 `organization_id` 期望 403（对应 [api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L690-L695)）
- Query token 下载：
  - 带 `?token=<Token.key>` 访问下载端点应通过鉴权（对应 [api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L19-L31) + [api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L838-L842)）

---

## Delivery modes

### 1) Web download（浏览器/脚本下载）
- 路由：`GET /api/files/<id>/download/`（[api_urls.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_urls.py#L15-L18)）
- 实现：`file_download()`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L838-L965)）
  - 鉴权：`QueryTokenAuthentication` + `TokenAuthentication` + `SessionAuthentication`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L838-L842)）
  - 权限：`can_view_or_download_file()`（同上）
  - 传输：支持 Range（206 Partial Content）与全量流式（FileResponse）

### 2) Viewer handoff（Cellxgene 预览链路）
- 后端发布：`POST /api/files/<id>/publish-cellxgene/`（[api_urls.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_urls.py#L19-L20)）
  - 实现：`publish_cellxgene()`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L967-L1057)）
  - 实现边界：
    - 仅支持 `.h5ad` 后缀（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L986-L990)）
    - 目标：将文件“复制或软链接”到 `CELLXGENE_DATA_DIR`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L991-L1014)）
    - 可选：生成布局（`prepare_h5ad_for_cellxgene()`）并尝试重启 cellxgene 进程（`restart_cellxgene_process()`）（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L1018-L1053)）
    - 权限边界：当前实现只允许文件 owner（`File.objects.get(id=file_id, user=request.user)`）（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L976-L980)），共享文件无法“发布到 viewer”。
- 前端承载：
  - `frontend/src/views/CellxgeneWrapper.vue` 通过 iframe 指向 `VITE_CELLXGENE_URL` 或 `/cellxgene/`（[CellxgeneWrapper.vue](file:///Users/shenyz/projects/github/Download_system_project/frontend/src/views/CellxgeneWrapper.vue#L1-L214)）
  - 该前端组件仅做可用性探测（GET `/cellxgene/api/v0.2/config`）与 URL 拼接，不负责后端发布。

### 3) Manifest / HPC handoff（清单导出、供外部流水线使用）
- 路由：`GET /api/files/manifest/`（[api_urls.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_urls.py#L25-L26)）
- 实现：`export_manifest()`（[search_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/search_views.py#L124-L163)）
  - 只导出“当前用户自己的文件”（`File.objects.filter(user=request.user)`）
  - 输出内容是后端宿主机上的绝对路径列表（`f.file.path`）
  - 代码层没有“将文件同步到 HPC / 下发作业 / 生成 signed URL”的逻辑；HPC 执行能力在代码外。

### 4) Benchmark protocol（可复现实验步骤草稿，供论文协议部分使用）
- 认证准备（Token）：
  - 登录/获取 token 的实际接口定义位于 `authentication/urls.py` 与 views（需按实际部署的 auth 路由为准）；后端统一使用 DRF Token（见 [settings.py](file:///Users/shenyz/projects/github/Download_system_project/file_project/settings.py#L175-L192)）
  - 下载端点额外支持 `?token=`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L19-L31)）
- 复现实验建议的最小 API/CLI 示例（示意）：
  - 搜索（metadata discovery）：`GET /api/files/search/?q=<kw>&experiment_type=RNA-seq&access_level=Internal`
    - 后端实现：`search_files()`（[search_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/search_views.py#L50-L121)）
  - 导出 manifest：`GET /api/files/manifest/?experiment_type=RNA-seq`
    - 后端实现：`export_manifest()`（[search_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/search_views.py#L124-L163)）
  - 下载文件：`GET /api/files/<id>/download/`
    - 后端实现：`file_download()`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L838-L965)）
  - Cellxgene 发布：`POST /api/files/<id>/publish-cellxgene/`
    - 后端实现：`publish_cellxgene()`（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L967-L1057)）

---

## Security boundary enforcement

### 1) Path canonicalization / traversal rejection 是否存在
- 存在，且主要用于“下载任务”的日志与输出目录参数：
  - `_safe_abs_path(base_dir, candidate)` 使用 `Path.resolve()` 并校验 `target` 必须位于 `base_dir` 之下（[file_download/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/api_views.py#L24-L29)）
  - 应用点：
    - `outdir`：`_schedule_job()` 对 `DOWNLOADS_BASE_DIR` 下的相对目录做 canonicalization，失败回退到 base（[file_download/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/api_views.py#L545-L554)）
    - `mail`：`_schedule_job()` 对 mail 路径也做 `_safe_abs_path(settings.BASE_DIR, rel_mail)`（[file_download/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/api_views.py#L564-L569)）
  - 日志读取端点：`downloads_status()` 限制 `log` 参数必须在 `BASE_DIR/logs` 下（`abspath + startswith`）（[file_download/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/api_views.py#L79-L86)）

### 2) 其他输入面的“路径安全”
- Cellxgene 发布：
  - 使用 `os.path.basename(original)` + 正则白名单替换，避免目标文件名注入路径分隔与特殊字符（[file_upload/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L996-L999)）
- 文件下载：
  - 下载路径来自 `FileField.path`（不直接接收用户自定义 path），但仍做“物理存在/可读”检查与 Range clamp（[file_upload/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L856-L915)）

### 3) 建议补的 path traversal rejection tests（仅列用例，不修改代码）
- `GET /api/downloads/status/?log=../../etc/passwd` 应返回 400（对应 [file_download/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/api_views.py#L79-L86)）
- `POST /api/downloads/start/` 带 `outdir=../../evil` 后续 job 执行应回退到 `DOWNLOADS_BASE_DIR`（对应 [file_download/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/api_views.py#L545-L554)）
- `POST /api/files/<id>/publish-cellxgene/` 对 `original_filename` 为恶意路径时，输出 `published_file` 不应包含 `/`（对应 [file_upload/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L996-L999)）

---

## Audit logging

### 1) 代码中“真实存在”的可审计记录载体
- 下载任务记录（数据库表）：`DownloadJob`（[file_download/models.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/models.py#L5-L30)）
  - 字段包含：`task_name`, `task_status`, `params`（JSON 字符串，含 url/outdir/mail/folder_id 等），`log_path/err_log_path`, `creator`, `created_at/updated_at`
- 下载/导入过程日志（文件）：
  - `downloads_status()` 读取 `BASE_DIR/logs/*` 下的 log 文件（[file_download/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/api_views.py#L64-L129)）
  - NCBI 下载进度写入 `NCBI_LOG_PATH` 指定的 log（[ncbi_client.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/ncbi_client.py#L22-L44)）

### 2) 代码中“仅有日志输出、但非结构化落库”的点
- 文件上传接口会将 `request.data`、`request.FILES`、`request.user` 以 `logger.error` 级别打印（[file_upload/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L640-L650)）
- manifest 导出有 `logger.info`（[search_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/search_views.py#L155-L156)）
- 下载接口有 `logger.info`（[file_upload/api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L893-L955)）

### 3) “操作审计表/统一审计中间件”是否存在
- 在当前由 `file_project/settings.py` 启动的 MetaServe 后端里：
  - `INSTALLED_APPS` 不包含任何 `OperationLog/LoginLog/AuditLog` 之类的 app（[settings.py](file:///Users/shenyz/projects/github/Download_system_project/file_project/settings.py#L34-L48)）
  - `MIDDLEWARE` 不包含 API 审计中间件（同上 [settings.py](file:///Users/shenyz/projects/github/Download_system_project/file_project/settings.py#L50-L59)）
- 仓库内确实存在“操作日志”实现，但属于另一个子项目 `Django-Vue3-Admin`：
  - `ApiLoggingMiddleware` 写 `dvadmin.system.models.OperationLog`（[middleware.py](file:///Users/shenyz/projects/github/Download_system_project/Django-Vue3-Admin/backend/dvadmin/utils/middleware.py)）
  - 该子项目的 settings 与当前 `file_project` 并非同一套启动配置；在 `file_project` 的 installed apps/middleware 中未见启用痕迹。

---

## High-risk mismatches between code and manuscript claims

以下为“论文表述可能声称/暗示的能力”与“当前代码实现证据”之间的高风险差异点（每条都给出可定位证据）：

1) “支持多格式并自动解析 GC 含量 / BAM 头信息 / 22 个生物字段”等主张风险
- README 中存在对“22 字段、GC 含量、BAM 头信息”等描述（[README.md](file:///Users/shenyz/projects/github/Download_system_project/README.md#L19-L23)）
- 但当前 extractor 仅实现 FASTA/FASTQ/VCF/PDF/CSV/txt 的轻量解析；未见 GC 含量与 BAM 头信息解析（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L15-L27), [metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L162-L198)）

2) “格式支持范围”与“实际 extractor 触发”存在不一致风险
- `File.FILE_FORMAT_CHOICES` 覆盖大量格式（包含 BAM/SAM/图片/压缩包等）（[models.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/models.py#L84-L183)）
- `MetadataExtractor.extractors` 仅注册少量格式（[metadata_extractor.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/metadata_extractor.py#L15-L27)）
- `FileUploadSerializer.validate()` 可能产生 `TXT/JPG/PNG` 等大写 format 值，导致提取器无法命中（[serializers.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/serializers.py#L131-L146)）

3) “Cellxgene 深度集成/无缝衔接”的实现边界
- 后端实际做的是：把 `.h5ad` 复制/软链接到 `CELLXGENE_DATA_DIR`，然后（可选）在同一台机器上重启 cellxgene 进程（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L967-L1053)）
- 不存在：将 cellxgene 作为受控服务编排、或为不同用户隔离 dataset 视图、或通过后端代理 cellxgene 的细粒度授权（当前仅 owner 可发布；共享文件不参与）（[api_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/api_views.py#L976-L980)）

4) “HPC/manifest 零拷贝交付”主张的可执行性边界
- manifest 实现仅返回后端宿主机的绝对路径（[search_views.py](file:///Users/shenyz/projects/github/Download_system_project/file_upload/search_views.py#L124-L163)）
- 是否能“零拷贝”完全取决于 HPC 运行节点是否与后端共享同一文件系统挂载；代码不做验证、也不输出挂载 scope/路径映射规则（仅在注释与日志中提到 zero-copy）。

5) “审计日志记录 reviewer 要求字段”的风险
- 当前 MetaServe 主后端未看到结构化审计落库（仅 python logger + `DownloadJob` 任务记录）（[settings.py](file:///Users/shenyz/projects/github/Download_system_project/file_project/settings.py#L34-L59), [file_download/models.py](file:///Users/shenyz/projects/github/Download_system_project/file_download/models.py#L5-L30)）
- 若论文声称“审计日志记录了用户、资源、动作、时间、结果、来源 IP 等字段”，需要特别核对：这些字段是否真实写入数据库（当前更像是日志文件/控制台输出，而非审计表）。

