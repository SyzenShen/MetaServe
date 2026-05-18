# MetaServe Benchmark Run Report

- 运行时间: 2026-04-30T18:35:52.007209 至 2026-04-30T18:41:15.570839
- 设计依据: `Benchmark 设计部分.markdown`
- 实例: `http://127.0.0.1:8000` 本地 Django 开发服务
- 项目标识: `BenchAlpha_20260430_183552`
- 原始结果: `/Users/shenyz/projects/github/Download_system_project/tests/performance/performance_test_project/reports/benchmark_revision_run_20260430_183552.json`

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
| T1 Metadata-based discovery | `/api/files/search/` | 30 | 14.79 | 0.66 | 16.39 | 11.99-17.19 | median 5 results |
| T2 Manifest generation | `/api/files/manifest/` | 30 | 7.0 | 0.72 | 7.69 | 6.15-9.01 | median 5 paths |
| T3 Viewer handoff request | `/api/files/108/publish-cellxgene/` | 30 | 8812.25 | 610.73 | 10056.34 | 8651.78-10442.89 | layout=['prepared']; cellxgene=['started'] |

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

## Operational Traceability
- 本轮主 benchmark 未观察到针对 `search`、`manifest`、`publish-cellxgene`、`FileShare create/delete` 的独立结构化 audit 记录返回。
- 运行可见性主要来自应用日志、数据库对象状态和下载子系统的 `DownloadJob` 设计，而不是统一审计 API。

## Manuscript-Facing Findings
- `search` 当前是 owner-scoped，不是统一 permission-filtered cross-user metadata discovery。
- `publish-cellxgene` 仅允许 owner 命中文件；internal member 不具备同组织代发布能力。
- `manifest` 输出宿主机绝对路径；是否构成 HPC zero-copy handoff 取决于外部共享挂载。
- 当前 traceability 更接近应用日志/任务记录，而非完整结构化 audit layer。
