# MetaServe benchmark working notes

## Purpose
- Summarize what is measured in the current benchmark artifacts.
- Record the scope of what is included in the current artifacts.
 - Reports use CIMR production instance as the source instance label.

## What is measured (current artifacts)

### MetaServe
- Metadata discovery: `/api/files/search/`
- Manifest generation: `/api/files/manifest/`

Evidence:
- `tests/performance/performance_test_project/results/galaxy_benchmark_mvp_*.csv`

### Galaxy
- History operations via Galaxy REST API:
  - Create history
  - Upload dataset
  - List history contents
  - Export history (server-side packaging)
  - Download export archive

Evidence:
- `tests/performance/performance_test_project/results/galaxy_api_benchmark_*.csv`

## Task mapping notes
- Galaxy “metadata-based dataset discovery” in Table 3 uses `list_history_contents`.
- Galaxy export times include server-side archive generation, which introduces extra packaging/copy/compression work compared with MetaServe manifest generation.

## Viewer/HPC handoff notes
- viewer: `/api/files/<id>/publish-cellxgene/` prefers symlink, falls back to copy
- HPC: manifest download provides filesystem paths for pipeline access
