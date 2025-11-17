import os
import re
import tempfile
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests
from django.conf import settings


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EFETCH_URL = f"{EUTILS_BASE}/efetch.fcgi"
ESUMMARY_URL = f"{EUTILS_BASE}/esummary.fcgi"
SRA_FASTQ_URL = "https://trace.ncbi.nlm.nih.gov/Traces/sra-reads-be/fastq"
ENA_FILEREPORT_URL = "https://www.ebi.ac.uk/ena/portal/api/filereport"

DEFAULT_MAX_BYTES = getattr(settings, "NCBI_MAX_DOWNLOAD_BYTES", 1024 * 1024 * 1024)  # 1 GiB
DEFAULT_TIMEOUT = getattr(settings, "NCBI_HTTP_TIMEOUT", 120)


class NCBIDownloadError(Exception):
  """Raised when an NCBI resource cannot be fetched."""


class NCBIDownloadTooLarge(NCBIDownloadError):
  """Raised if the download exceeds the configured size limit."""


@dataclass
class NCBIDownloadResult:
  accession: str
  db: str
  filename: str
  file_path: str
  file_format: str
  document_type: str
  metadata: Dict[str, object]


RESOURCE_MAP: Dict[str, Dict[str, str]] = {
  "nuccore": {"db": "nuccore", "rettype": "fasta", "retmode": "text", "ext": "fasta", "document_type": "Dataset"},
  "nucleotide": {"db": "nuccore", "rettype": "fasta", "retmode": "text", "ext": "fasta", "document_type": "Dataset"},
  "protein": {"db": "protein", "rettype": "fasta", "retmode": "text", "ext": "fasta", "document_type": "Dataset"},
  "gene": {"db": "gene", "rettype": "xml", "retmode": "xml", "ext": "xml", "document_type": "Dataset"},
  "pubmed": {"db": "pubmed", "rettype": "abstract", "retmode": "text", "ext": "txt", "document_type": "Paper"},
  "bioproject": {"db": "bioproject", "rettype": "xml", "retmode": "xml", "ext": "xml", "document_type": "Dataset"},
  "biosample": {"db": "biosample", "rettype": "xml", "retmode": "xml", "ext": "xml", "document_type": "Dataset"},
  # Special handling keys use the "strategy" field
  "sra": {"strategy": "sra_fastq", "ext": "fastq.gz", "document_type": "Dataset"},
}

ACCESSION_PREFIX_MAP = {
  "SR": "sra",
  "ER": "sra",
  "DR": "sra",
  "PRJ": "bioproject",
  "SAM": "biosample",
  "GSE": "pubmed",  # fallback to summary text
  "GSM": "pubmed",
}

FORMAT_MAP = {
  "fasta": "FASTA",
  "fa": "FASTA",
  "fastq": "FASTQ",
  "fastq.gz": "FASTQ",
  "fq": "FASTQ",
  "fq.gz": "FASTQ",
  "gb": "other",
  "gbff": "other",
  "xml": "XML",
  "txt": "txt",
  "pdb": "other",
}


def parse_ncbi_url(url: str) -> Tuple[str, str]:
  """
  Attempt to infer (resource, accession) from an arbitrary NCBI URL.
  Raises NCBIDownloadError if parsing fails.
  """
  parsed = urlparse(url)
  path_parts = [part for part in parsed.path.split("/") if part]
  host = (parsed.netloc or "").lower()

  resource = path_parts[0].lower() if path_parts else ""
  accession = path_parts[1] if len(path_parts) > 1 else ""

  def _find_accession(text: str) -> Optional[str]:
    m = re.search(r"(PRJ[A-Z0-9]+|SAMN[0-9]+|SR[RPX][0-9]+|ER[RPX][0-9]+|DR[RPX][0-9]+|GSE[0-9]+|GSM[0-9]+|[A-Z]{2}_[0-9.]+|(?:SRR|ERR|DRR)\d{6,})", text)
    return m.group(1) if m else None

  def _find_best_sra_candidate(texts: list[str]) -> Optional[str]:
    candidates = []
    pattern = re.compile(r"((?:SRR|ERR|DRR)\d{6,})", re.IGNORECASE)
    for t in texts:
      for m in pattern.findall(t):
        candidates.append(m)
    if not candidates:
      return None
    # Prefer the candidate with the longest numeric part; tie-breaker: last occurrence
    def score(acc: str) -> tuple[int, int]:
      digits = re.findall(r"(\d+)", acc)
      length = len(digits[0]) if digits else 0
      return (length, 0)
    # choose last max by length
    best_len = max(len(re.findall(r"\d+", c)[0]) for c in candidates)
    best = None
    for c in candidates:
      if len(re.findall(r"\d+", c)[0]) == best_len:
        best = c
    return best

  # If the path-derived accession doesn't look valid, clear it
  if accession and not _find_accession(accession):
    accession = ""

  # Try common query keys
  query = parse_qs(parsed.query)
  candidate_keys = ("id", "term", "acc", "run")
  if not accession:
    for key in candidate_keys:
      if key in query and query[key]:
        candidate = query[key][0]
        acc = _find_accession(candidate) or candidate.strip()
        accession = acc
        break

  # Fallback: search whole URL for a recognizable accession token
  if not accession:
    # Prefer best SRA candidate from path parts and full URL
    acc = _find_best_sra_candidate(path_parts + [url])
    if acc:
      accession = acc
    else:
      acc2 = _find_accession(url)
      if acc2:
        accession = acc2

  if accession:
    accession = accession.strip()

  # Resource inference
  if not resource or resource == "entrez":
    # Guess resource from accession prefix
    if accession:
      for prefix, mapped in ACCESSION_PREFIX_MAP.items():
        if accession.upper().startswith(prefix):
          resource = mapped
          break

  # Handle non-standard SRA download hosts/paths (e.g., sra-downloadb, sra-reads-be, sos6)
  known_resources = set(RESOURCE_MAP.keys())
  if resource not in known_resources:
    has_sra_host = ("sra" in host) or ("ncbi" in host and any("sra" in p.lower() for p in path_parts))
    has_sra_acc = bool(accession and re.match(r"^(SRR|ERR|DRR)\d+", accession, flags=re.IGNORECASE))
    if has_sra_host or has_sra_acc:
      resource = "sra"

  if not resource:
    raise NCBIDownloadError("无法识别 NCBI 链接类型")
  if not accession:
    raise NCBIDownloadError("无法从链接中解析出 accession/ID")

  resource = resource.lower()
  return resource, accession


def _download_streaming(url: str, params: Optional[Dict[str, str]], suffix: str, max_bytes: int) -> Tuple[str, int, Dict[str, str]]:
  with requests.get(url, params=params, stream=True, timeout=DEFAULT_TIMEOUT) as resp:
    if resp.status_code != 200:
      # 尝试读取少量文本以提供更清晰的错误信息
      try:
        msg = resp.text[:200]
        msg = msg.strip()
      except Exception:
        msg = ""
      detail = f"NCBI 返回错误状态码 {resp.status_code}"
      if msg:
        detail = f"{detail}：{msg}"
      raise NCBIDownloadError(detail)
    total_bytes = 0
    headers = resp.headers
    content_length = headers.get("Content-Length")
    if content_length and int(content_length) > max_bytes:
      raise NCBIDownloadTooLarge(f"文件大小 {content_length} 超过限制 {max_bytes}")

    handle, file_path = tempfile.mkstemp(suffix=f".{suffix}")
    with os.fdopen(handle, "wb") as tmp:
      for chunk in resp.iter_content(chunk_size=8192):
        if not chunk:
          continue
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
          tmp.close()
          os.remove(file_path)
          raise NCBIDownloadTooLarge(f"文件大小超过限制 {max_bytes} 字节")
        tmp.write(chunk)
    return file_path, total_bytes, headers


def _fetch_summary(db: str, accession: str) -> Dict[str, object]:
  params = {"db": db, "id": accession, "retmode": "json"}
  try:
    resp = requests.get(ESUMMARY_URL, params=params, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
  except Exception:
    return {}

  result = data.get("result", {})
  uid = (result.get("uids") or [None])[0]
  if not uid:
    return {}

  summary = result.get(uid, {})
  metadata = {
    "title": summary.get("title") or summary.get("extra", ""),
    "organism": summary.get("organism") or summary.get("taxname"),
    "length": summary.get("slen") or summary.get("length"),
    "status": summary.get("status"),
    "summary": summary.get("summary") or summary.get("caption") or summary.get("subname"),
    "experiment_type": summary.get("strategy") or summary.get("librarystrategy"),
    "links": summary.get("linksetdbs"),
  }
  return {k: v for k, v in metadata.items() if v}


def _normalize_file_format(extension: str) -> str:
  extension = extension.lower()
  if extension in FORMAT_MAP:
    return FORMAT_MAP[extension]
  return "other"


def _ena_fetch_fastq_links(accession: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  """
  Query ENA filereport for FASTQ links. Returns (first_fastq_url, layout, all_urls).
  We normalize ftp-only links to https using ENA public mirror host.
  """
  params = {
    "accession": accession,
    "result": "read_run",
    # 注意：ENA 不再支持 fastq_http 字段，仅返回 fastq_ftp
    "fields": "fastq_ftp,library_layout",
    "format": "tsv",
  }
  try:
    resp = requests.get(ENA_FILEREPORT_URL, params=params, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    lines = resp.text.strip().splitlines()
    if len(lines) < 2:
      return None, None, None
    header = lines[0].split("\t")
    # Find the row matching accession (some responses may include multiple rows)
    target_cols = None
    for line in lines[1:]:
      parts = line.split("\t")
      cols = {h: (parts[i] if i < len(parts) else "") for i, h in enumerate(header)}
      # ENA filereport for read_run returns the requested run; accept the first
      target_cols = cols
      break
    if not target_cols:
      return None, None, None
    http_links = (target_cols.get("fastq_http") or "").strip()
    ftp_links = (target_cols.get("fastq_ftp") or "").strip()
    layout = (target_cols.get("library_layout") or "").strip()

    def normalize_links(raw: str) -> list[str]:
      if not raw:
        return []
      items = [u.strip() for u in raw.split(";") if u.strip()]
      normalized = []
      for u in items:
        if u.startswith("http://") or u.startswith("https://"):
          normalized.append(u)
        elif u.startswith("ftp://"):
          # Replace ftp://ftp.sra.ebi.ac.uk/... -> https://ftp.sra.ebi.ac.uk/...
          normalized.append(u.replace("ftp://", "https://"))
        else:
          # Likely host/path without scheme, e.g., ftp.sra.ebi.ac.uk/vol1/fastq/...
          normalized.append(f"https://{u}")
      return normalized

    urls = normalize_links(http_links) or normalize_links(ftp_links)
    if not urls:
      return None, (layout or None), None
    first = urls[0]
    return first, (layout or None), ";".join(urls)
  except Exception:
    return None, None, None


def _download_from_ena(accession: str, max_bytes: int) -> Optional[Tuple[str, int, Dict[str, str], str, str, str]]:
  """
  Try to download FASTQ from ENA mirror for given accession.
  Returns (file_path, total_bytes, headers, suffix, filename, all_urls) or None if unavailable.
  """
  first_url, _layout, all_urls = _ena_fetch_fastq_links(accession)
  if not first_url:
    return None
  # Determine suffix & filename from URL path
  parsed = urlparse(first_url)
  basename = os.path.basename(parsed.path)
  suffix = "fastq.gz" if basename.endswith(".fastq.gz") else (basename.split(".")[-1] if "." in basename else "fastq.gz")
  try:
    file_path, total_bytes, headers = _download_streaming(first_url, params=None, suffix=suffix, max_bytes=max_bytes)
    return file_path, total_bytes, headers, suffix, basename, all_urls
  except Exception:
    return None


def download_ncbi_resource(url: str, max_bytes: Optional[int] = None) -> NCBIDownloadResult:
  resource, accession = parse_ncbi_url(url)
  config = RESOURCE_MAP.get(resource)

  if not config:
    raise NCBIDownloadError(f"暂不支持的 NCBI 资源类型：{resource}")

  max_allowed = max_bytes or DEFAULT_MAX_BYTES
  strategy = config.get("strategy")

  if strategy == "sra_fastq":
    # 校验 SRA 运行号格式：至少 6 位数字的 SRR/ERR/DRR
    if not re.fullmatch(r"(SRR|ERR|DRR)\d{6,}", accession, flags=re.IGNORECASE):
      raise NCBIDownloadError(
        "无效的 SRA 运行号：需要 SRR/ERR/DRR+至少6位数字，例如 SRR12345678"
      )
    suffix = config["ext"]
    params = {"acc": accession}
    try:
      file_path, total_bytes, headers = _download_streaming(SRA_FASTQ_URL, params=params, suffix=suffix, max_bytes=max_allowed)
      file_format = _normalize_file_format(suffix)
      metadata = _fetch_summary("sra", accession)
      metadata.update({
        "ncbi_db": "sra",
        "download_bytes": total_bytes,
        "source_url": url,
      })
      filename = f"{accession}.{suffix}"
      return NCBIDownloadResult(
        accession=accession,
        db="sra",
        filename=filename,
        file_path=file_path,
        file_format=file_format,
        document_type=config.get("document_type", "Dataset"),
        metadata=metadata,
      )
    except NCBIDownloadError as exc:
      # Fallback to ENA mirror when NCBI indicates run too large for direct retrieval
      msg = str(exc).lower()
      if "too big" in msg or "sra toolkit" in msg or "501" in msg:
        ena_result = _download_from_ena(accession, max_allowed)
        if ena_result:
          file_path, total_bytes, headers, ena_suffix, ena_name, all_urls = ena_result
          file_format = _normalize_file_format(ena_suffix)
          metadata = _fetch_summary("sra", accession)
          metadata.update({
            "ncbi_db": "sra",
            "download_bytes": total_bytes,
            "source_url": url,
            "ena_mirror_urls": all_urls,
          })
          filename = ena_name or f"{accession}.{ena_suffix}"
          return NCBIDownloadResult(
            accession=accession,
            db="sra",
            filename=filename,
            file_path=file_path,
            file_format=file_format,
            document_type=config.get("document_type", "Dataset"),
            metadata=metadata,
          )
      # Otherwise, raise a clearer guidance message
      raise NCBIDownloadError(
        (
          f"NCBI 无法直接检索该运行（{accession}）：{exc}. "
          "建议使用 ENA 镜像或安装 SRA Toolkit 进行下载转换。"
          "参考 https://github.com/ncbi/sra-tools/wiki"
        )
      )

  db = config["db"]
  params = {
    "db": db,
    "id": accession,
    "rettype": config.get("rettype"),
    "retmode": config.get("retmode"),
  }
  suffix = config.get("ext", "txt")
  params = {k: v for k, v in params.items() if v}

  file_path, total_bytes, headers = _download_streaming(EFETCH_URL, params=params, suffix=suffix, max_bytes=max_allowed)
  file_format = _normalize_file_format(suffix)
  metadata = _fetch_summary(db, accession)
  metadata.update({
    "ncbi_db": db,
    "download_bytes": total_bytes,
    "source_url": url,
  })

  content_disposition = headers.get("Content-Disposition")
  if content_disposition:
    match = re.search(r'filename=\"?([^\";]+)', content_disposition)
    if match:
      filename = match.group(1)
    else:
      filename = f"{accession}.{suffix}"
  else:
    filename = f"{accession}.{suffix}"

  return NCBIDownloadResult(
    accession=accession,
    db=db,
    filename=filename,
    file_path=file_path,
    file_format=file_format,
    document_type=config.get("document_type", "Dataset"),
    metadata=metadata,
  )
