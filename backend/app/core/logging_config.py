import logging
import sys

def setup_logging():
    """
    Configure production-safe, structured INFO-level logging for stdout/stderr visibility on Render.
    Ensures application logs, publishing trace events, and uvicorn logs are formatted and printed.
    """
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing default handlers to avoid duplicate output
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Ensure app modules and web server loggers log at INFO level
    for name in ["app", "uvicorn", "uvicorn.access", "uvicorn.error", "celery", "__main__"]:
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)

def sanitize_url(url: str | None) -> str:
    """Return a safe/sanitized version of a media URL without credentials or base64 blobs."""
    if not url:
        return "<none>"
    url_str = str(url)
    if url_str.startswith("data:"):
        header = url_str.split(",", 1)[0]
        return f"{header};base64,[length={len(url_str)}]"
    
    # Strip any potential token query params
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
    try:
        parsed = urlparse(url_str)
        if parsed.query:
            query_params = parse_qs(parsed.query)
            # Redact sensitive parameters if present
            for sensitive_key in ["access_token", "token", "secret", "key", "signature"]:
                if sensitive_key in query_params:
                    query_params[sensitive_key] = ["[REDACTED]"]
            clean_query = urlencode(query_params, doseq=True)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, clean_query, parsed.fragment))
        return url_str
    except Exception:
        return url_str[:100]
