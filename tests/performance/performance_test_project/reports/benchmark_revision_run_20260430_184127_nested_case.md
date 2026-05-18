# MetaServe Benchmark Run Report

- 运行时间: 2026-04-30T18:41:27.343786 至 2026-04-30T18:47:06.670875
- 设计依据: `Benchmark 设计部分.markdown`
- 实例: `http://127.0.0.1:8000` 本地 Django 开发服务
- 项目标识: `BenchAlpha_20260430_184127`
- 原始结果: `/Users/shenyz/projects/github/Download_system_project/tests/performance/performance_test_project/reports/benchmark_revision_run_20260430_184127.json`
- 运行配置: 服务以 `CELLXGENE_PYTHON=$(which python3)` 启动，未修改任何仓库代码

## Method
- 只对 T1-T3 统计 API/server-side latency；T4-T6 采用 expected-vs-observed 定性验证。
- T1-T3 每项执行 5 次 warm-up、30 次正式测量。
- 用户角色包括 owner/data steward、internal member、external collaborator、outsider。

## Dataset
| File | Format | Access | Purpose |
| --- | --- | --- | --- |
| bench_internal_variants.vcf | VCF | Internal | T1/T2 internal dataset |
| bench_internal_reads.fastq | FASTQ | Internal | T1/T2 internal dataset |
| bench_internal_viewer.h5ad | H5AD | Internal | T3 viewer handoff |
| bench_restricted_image.tiff | TIFF | Restricted | T4/T5 explicit ACL subset |
| bench_notes.csv | CSV | Internal | extra dataset coverage |
| bench_protocol.pdf | PDF | Internal | non-dataset coverage |

## Quantitative Results
| Task | Endpoint | n | Median (ms) | IQR (ms) | P95 (ms) | Min-Max (ms) | Observed output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 Metadata-based discovery | `/api/files/search/` | 30 | 14.78 | 1.5 | 16.37 | 13.38-16.9 | median 5 results |
| T2 Manifest generation | `/api/files/manifest/` | 30 | 7.14 | 0.69 | 8.08 | 6.1-9.0 | median 5 paths |
| T3 Viewer handoff request | `/api/files/114/publish-cellxgene/` | 30 | 9851.76 | 281.9 | 10371.38 | 8996.49-10488.66 | layout=['prepared']; cellxgene=['started'] |

## Authorization Validation
| Case | Expected | Observed |
| --- | --- | --- |
| Owner downloads Internal VCF | allowed | HTTP 200 |
| Internal member downloads owner Internal VCF | allowed | HTTP 200 |
| Outsider downloads owner Internal VCF | hidden or denied | HTTP 404 |
| External collaborator downloads Restricted TIFF before share | denied | HTTP 404 |
| External collaborator downloads Restricted TIFF after share | allowed | HTTP 200 |
| External collaborator downloads Restricted TIFF after revoke | denied | HTTP 404 |
| Internal member accesses `org-internal` listing | same-org Internal files visible | count=5 |
| External collaborator publishes owner H5AD | denied | HTTP 404 |

## Discovery Boundary Observation
| User | Search result count with same filter | Interpretation |
| --- | --- | --- |
| owner | 5 | owner-scoped discovery sees benchmark files |
| internal | 0 | current implementation does not expose owner files through search endpoint |
| external | 0 | current implementation does not expose owner files through search endpoint |
| outsider | 0 | current implementation does not expose owner files through search endpoint |

## ACL Management
| Step | Result |
| --- | --- |
| Create FileShare | HTTP 201 |
| Delete FileShare | HTTP 200 |
| Download status before/after share/after revoke | 404 / 200 / 404 |

## Path-Boundary Rejection
| Probe | Expected | Observed |
| --- | --- | --- |
| `GET /api/downloads/status/?log=../../etc/passwd` | rejected | HTTP 400 |

## Nested Restriction Case
- 最小用例:
  - owner 创建私有父文件夹 `nested_restricted_parent`
  - 在该父文件夹下上传一个 `Restricted` 子文件
  - external collaborator 在未共享前访问父文件夹与子文件
  - owner 再对子文件创建直接 `FileShare`
  - external collaborator 重新访问父文件夹与子文件
- 观测结果:
  - 共享前: 父文件夹 `404`，子文件下载 `404`
  - 共享后: 父文件夹仍为 `404`，但子文件下载 `200`，子文件 detail `200`
- 解释:
  - 当前实现中，父文件夹的私有/受限上下文并没有对已共享子文件形成“parent restriction takes precedence”的最终约束。
  - 换言之，直接 `FileShare` 子文件可以绕过父文件夹可见性边界。
- 这意味着:
  - 如果论文要声称“nested restrictive parent always overrides child-level sharing”，当前代码证据不支持该表述。
  - 更准确的说法应是：当前系统对文件下载/详情主要执行 file-level access control；folder visibility 与 file share 不是统一收敛到单一 most-restrictive hierarchy。

## Operational Traceability
- 本轮主 benchmark 未观察到针对 `search`、`manifest`、`publish-cellxgene`、`FileShare create/delete` 的独立结构化 audit 记录返回。
- 运行可见性主要来自应用日志、数据库对象状态和下载子系统的 `DownloadJob` 设计，而不是统一审计 API。

## Manuscript-Facing Findings
- `search` 当前是 owner-scoped，不是统一 permission-filtered cross-user metadata discovery。
- `publish-cellxgene` 仅允许 owner 命中文件；internal member 不具备同组织代发布能力。
- `manifest` 输出宿主机绝对路径；是否构成 HPC zero-copy handoff 取决于外部共享挂载。
- 当前 traceability 更接近应用日志/任务记录，而非完整结构化 audit layer。
- nested case 实测显示：父文件夹限制不会自动覆盖已共享子文件；若论文声称 parent restriction 优先，需要修正为“当前未完全实现”或单独标注为设计目标而非现状。
