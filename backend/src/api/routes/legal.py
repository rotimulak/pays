"""Legal documents endpoints (oferta, privacy policy)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import markdown

router = APIRouter(prefix="/legal", tags=["legal"])

# Path to legal documents (relative to backend root)
LEGAL_DIR = Path(__file__).parent.parent.parent.parent.parent / "legal"


def _render_markdown_to_html(md_path: Path, title: str) -> str:
    """Render markdown file to HTML page."""
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    content = md_path.read_text(encoding="utf-8")
    html_content = markdown.markdown(content, extensions=["tables", "fenced_code"])

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | HHHelper</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background: #fafafa;
        }}
        h1, h2, h3 {{
            color: #1a1a1a;
            margin-top: 1.5em;
        }}
        h1 {{
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        hr {{
            border: none;
            border-top: 1px solid #eee;
            margin: 2em 0;
        }}
        ul {{
            padding-left: 20px;
        }}
        strong {{
            color: #1a1a1a;
        }}
        a {{
            color: #007bff;
        }}
        @media (prefers-color-scheme: dark) {{
            body {{
                background: #1a1a1a;
                color: #e0e0e0;
            }}
            h1, h2, h3, strong {{
                color: #fff;
            }}
            h1 {{
                border-bottom-color: #4da3ff;
            }}
            h2 {{
                border-bottom-color: #444;
            }}
            hr {{
                border-top-color: #444;
            }}
            a {{
                color: #4da3ff;
            }}
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""


def _render_txt_to_html(txt_path: Path, title: str) -> str:
    """Render plain text file to HTML page."""
    if not txt_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    content = txt_path.read_text(encoding="utf-8")
    # Escape HTML and preserve line breaks
    import html
    escaped = html.escape(content)
    html_content = escaped.replace("\n", "<br>\n")

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | HHHelper</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background: #fafafa;
        }}
        @media (prefers-color-scheme: dark) {{
            body {{
                background: #1a1a1a;
                color: #e0e0e0;
            }}
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""


@router.get("", response_class=HTMLResponse)
async def get_legal_index() -> str:
    """Return legal documents index page."""
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Юридические документы | HH Helper</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #333;
            background: #fafafa;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 40px;
        }
        .doc-list {
            list-style: none;
            padding: 0;
        }
        .doc-list li {
            margin-bottom: 20px;
            padding: 20px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .doc-list a {
            color: #007bff;
            text-decoration: none;
            font-size: 18px;
            font-weight: 500;
        }
        .doc-list a:hover {
            text-decoration: underline;
        }
        .doc-desc {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }
        @media (prefers-color-scheme: dark) {
            body {
                background: #1a1a1a;
                color: #e0e0e0;
            }
            h1 {
                color: #fff;
            }
            .subtitle, .doc-desc {
                color: #999;
            }
            .doc-list li {
                background: #2a2a2a;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            .doc-list a {
                color: #4da3ff;
            }
        }
    </style>
</head>
<body>
    <h1>HH Helper</h1>
    <p class="subtitle">Юридические документы сервиса</p>

    <ul class="doc-list">
        <li>
            <a href="/legal/oferta">Публичная оферта</a>
            <p class="doc-desc">Договор об оказании услуг</p>
        </li>
        <li>
            <a href="/legal/privacy">Политика конфиденциальности</a>
            <p class="doc-desc">Порядок обработки и защиты персональных данных</p>
        </li>
    </ul>
</body>
</html>"""


@router.get("/oferta", response_class=HTMLResponse)
async def get_oferta() -> str:
    """Return public offer agreement."""
    oferta_path = LEGAL_DIR / "oferta.txt"
    return _render_txt_to_html(oferta_path, "Публичная оферта")


@router.get("/privacy", response_class=HTMLResponse)
async def get_privacy_policy() -> str:
    """Return privacy policy."""
    privacy_path = LEGAL_DIR / "privacy-policy.md"
    return _render_markdown_to_html(privacy_path, "Политика конфиденциальности")
