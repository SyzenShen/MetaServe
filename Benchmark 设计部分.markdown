# 一、Benchmark 设计部分

## 1. Benchmark 总定位

建议把本轮 benchmark 定义为四个维度：

| 评估维度                                   | 性质           | 目的                                                         | 是否定量       |
| ------------------------------------------ | -------------- | ------------------------------------------------------------ | -------------- |
| System response time                       | 性能指标       | 测系统在检索、manifest 生成、viewer handoff 请求上的响应时间 | 是             |
| Traceability / operational records         | 治理指标       | 看关键操作后是否留下可追踪记录                               | 否，功能性检查 |
| User management and authorization boundary | 安全/权限指标  | 看内部用户、外部例外用户执行相同操作时边界是否正确           | 否，功能性检查 |
| Operational complexity                     | 使用复杂度指标 | 看完成任务需要哪些人工动作、是否需要管理员介入、是否依赖共享存储 | 否，定性描述   |

**核心原则：**

不要再把 user steps 和毫秒级时间放在同一个性能表里。
 毫秒级时间只表示 **server-side / API-side response latency**。
 用户管理、审计日志、操作复杂度全部作为 **qualitative operational characterization**。

------

## 2. 测试规模：不要做大计算，使用当前部署即可

当前稿件已经报告了测试环境：48 个用户、5 个 organization、6 个 project、42 个文件、5.79 GiB 数据、150 条 query logs。这个规模虽然不适合做“大规模性能优越性”论证，但足够做一个 **single-site operational benchmark**。

所以不要再做 1 TB、10 TB、1 million files 这种压力测试。老师说“目标是不增加太多计算量”，那就用当前部署数据做：

- metadata search；
- manifest generation；
- viewer handoff request；
- permission / ACL 操作；
- delivery-boundary rejection；
- operational record 检查。

文件类型选择可以覆盖代表性类别即可，例如 VCF、H5AD、TIFF/HDF5、FASTQ、CSV、PDF。文件格式综合表可以作为选择这些代表格式的依据，因为它已经列出常见 bioinformatics 和 biomedical 文件格式、扩展名、识别特征和压缩支持。

------

## 3. 用户角色设计

建议用四类用户，不要太复杂：

| 用户类型                          | 论文中的角色                                   | 权限状态                                              | 用途                                |
| --------------------------------- | ---------------------------------------------- | ----------------------------------------------------- | ----------------------------------- |
| Admin / data steward              | facility administrator 或 project data manager | 可管理项目、用户和共享规则                            | 测用户管理、ACL 创建/撤销、操作记录 |
| Internal project member           | 内部项目成员                                   | 对项目内资产有 project-scoped read access             | 代表设计内正常用户                  |
| External collaborator             | 外部合作者                                     | 只通过 explicit ACL 访问部分 TIFF/HDF5 或 Visium 资产 | 代表“例外用户”                      |
| Unauthorized or out-of-scope user | 非项目用户或未授权用户                         | 无访问权限                                            | 测边界拒绝、隐藏结果、路径拒绝      |

老师说的“设计内的用户，和例外的用户相同操作的边界反馈”，重点就是：

> **internal project member 和 external collaborator 执行同一个 search / download / manifest / viewer handoff 操作时，系统是否给出不同且正确的结果。**

------

## 4. Benchmark 具体任务和指标

建议设 6 个任务，其中只有 T1–T3 计响应时间，T4–T6 做定性验证。

### 推荐任务表

| Task | 任务名称                                  | 操作对象                                               | 用户                                                      | 主要输出                                  | 指标                                                         |
| ---- | ----------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------ |
| T1   | Metadata-based discovery                  | 按 project、file type、sample 或 assay 搜索文件        | internal member；external collaborator                    | permission-filtered result set            | response latency；结果是否符合权限边界                       |
| T2   | Manifest generation / controlled delivery | 生成 VCF 或 FASTQ 文件集合的 manifest，或准备下载      | internal member；external collaborator                    | manifest 或 download-ready selection      | response latency；manifest 是否只含授权文件；是否产生操作记录 |
| T3   | Viewer handoff request                    | H5AD 文件 handoff 到兼容 viewer，如 cellxgene          | owner 或 internal member；external collaborator           | handoff response / publish record         | response latency；未授权用户是否被拒绝                       |
| T4   | User and ACL management                   | 给 external collaborator 授权 TIFF/HDF5 子集，然后撤销 | admin / data steward                                      | ACL state change                          | expected vs observed；是否有操作记录                         |
| T5   | Authorization boundary validation         | 相同查询、下载、manifest 操作在不同用户下执行          | internal member；external collaborator；unauthorized user | allow / hidden / deny / filtered manifest | expected vs observed                                         |
| T6   | Path-boundary rejection                   | 构造 path traversal 或未注册路径请求                   | any user                                                  | request rejected                          | expected vs observed；是否记录异常或拒绝事件                 |

------

## 5. 响应时间测量定义

这是最重要的部分，要写清楚。

### System-side latency 的定义

| 操作                   | Start event                      | End event                                      | 明确排除                                     |
| ---------------------- | -------------------------------- | ---------------------------------------------- | -------------------------------------------- |
| Metadata query         | server receives query request    | permission-filtered response is returned       | login、UI 点击、人工输入、文件传输           |
| Manifest generation    | server receives manifest request | manifest file / manifest response is available | workflow execution、HPC 运行、后续文件读取   |
| Viewer handoff request | server receives handoff request  | handoff response / publish record is available | cellxgene 实际加载时间、浏览器渲染、人工注释 |

### 重复次数

建议最低写：

> Each latency measurement was repeated 30 times after 5 warm-up runs.

报告：

- n；
- median；
- IQR；
- P95。

如果时间紧，至少要有：

- n；
- median；
- P95；
- range 或 IQR。

------

## 6. 审计日志 / 操作记录怎么测

不要写成 formal audit logging。建议在论文里叫：

> **operational traceability records**
>  或
>  **delivery and permission-related operational records**

检查项：

| 操作                     | 需要检查的记录字段                                           |
| ------------------------ | ------------------------------------------------------------ |
| file download / delivery | actor、resource、operation type、timestamp、outcome          |
| manifest generation      | actor、selected file set 或 manifest ID、timestamp、outcome  |
| viewer handoff           | actor、asset、handoff / publish event、timestamp             |
| ACL grant / revoke       | actor、target user、resource scope、operation type、timestamp |
| rejected access          | actor、resource 或 request、deny / reject outcome、timestamp，如果系统记录 |

如果某些 search 事件没有结构化审计记录，不要强行写“全部 search 都被 audit”。可以写：

> Delivery and permission-changing events were checked for traceability records; read-only metadata searches were evaluated for permission-filtered behavior and may be represented only in application logs depending on deployment configuration.

------

## 7. 用户管理 / 安全部分怎么兼容回答审稿人

这个部分可以直接做成一个 authorization validation matrix。

关键测试不是性能，而是：

> expected behavior 是否等于 observed behavior。

推荐验证 case：

| Case                              | 用户                       | 操作                               | 预期                                |
| --------------------------------- | -------------------------- | ---------------------------------- | ----------------------------------- |
| Owner access                      | 文件 owner                 | 下载 private asset                 | allowed                             |
| Internal member access            | project member             | 搜索 / 下载 project internal asset | allowed                             |
| Out-of-scope internal user        | 非项目成员                 | 搜索 private/internal asset        | hidden or denied                    |
| External collaborator with ACL    | 外部合作者                 | 搜索 / 下载被授权 TIFF/HDF5        | allowed only for shared subset      |
| External collaborator without ACL | 外部合作者                 | 搜索 / 下载 VCF/H5AD               | hidden or denied                    |
| Revoked collaborator              | 被撤销权限的外部用户       | 重复之前允许的操作                 | denied                              |
| Nested restrictive parent         | 子资源有共享，但父级更严格 | 访问子资源                         | parent restriction takes precedence |
| Path traversal                    | 任意用户                   | 请求 `../` 或未注册路径            | rejected                            |
| Unauthorized permission change    | 普通用户                   | 尝试修改 ACL                       | denied                              |

这个表可以同时回应 security reviewer 的问题。

------

## 8. 操作复杂度怎么写

老师说“除了系统响应时间，其他都是定性评估”，所以 user steps 不要作为主结果数字再出现。

建议写成：

| 任务                         | 操作复杂度描述                                               |
| ---------------------------- | ------------------------------------------------------------ |
| Metadata discovery           | Requires selecting project and metadata filters; complexity mainly comes from metadata specificity rather than computation |
| Manifest generation          | Requires selecting filtered result set and confirming export; avoids manual path transcription under shared storage |
| Viewer handoff               | Requires compatible viewer configuration; complexity is deployment-dependent |
| ACL management               | Requires data steward or admin intervention; complexity reflects governance controls rather than computational cost |
| External collaborator access | Simple after ACL is created, but intentionally restricted to shared subset |

如果一定要保留步骤数，放 supplementary，不放主 benchmark 表。

------

## 9. Galaxy 怎么处理

Galaxy 不建议再放在响应时间表里。建议只在 qualitative reference 里说：

> Galaxy was used as a workflow-oriented reference environment, not as a functionally equivalent governance system.

而且不要再写 Galaxy 必然需要 copy。Galaxy Data Libraries 的官方说明里明确提到，是否 link files instead of copying 取决于管理员和保存策略；Galaxy training 也说明在 NFS 等场景下可以使用 link files instead of copying。

所以论文里应该写：

> Copying or restaging in Galaxy is configuration-dependent and should not be treated as an intrinsic limitation of Galaxy.

这样可以避免 reviewer 再攻击比较不公平。