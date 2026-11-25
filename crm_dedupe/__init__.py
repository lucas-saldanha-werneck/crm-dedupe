"""crm-dedupe: find duplicate company records across CRM / ERP exports."""
from .core import normalize_name, normalize_domain, find_duplicates, naive_duplicates, load_csv

__all__ = ["normalize_name", "normalize_domain", "find_duplicates", "naive_duplicates", "load_csv"]
