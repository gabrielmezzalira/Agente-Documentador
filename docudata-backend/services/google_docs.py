import json
import os
import re
from datetime import datetime

from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


def _get_services():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

    if not (client_id and client_secret and refresh_token):
        raise RuntimeError(
            "Configure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REFRESH_TOKEN no .env"
        )

    creds = OAuthCredentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())

    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return docs, drive


def _clone_template(drive, template_id: str, title: str, folder_id: str) -> str:
    copy = drive.files().copy(
        fileId=template_id,
        body={"name": title, "parents": [folder_id]},
        supportsAllDrives=True,
    ).execute()
    return copy["id"]


def _replace_placeholders(docs, doc_id: str, replacements: dict):
    requests = [
        {
            "replaceAllText": {
                "containsText": {"text": f"{{{{{k}}}}}", "matchCase": True},
                "replaceText": v,
            }
        }
        for k, v in replacements.items()
    ]
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def _parse_markdown(text: str) -> list:
    """Converte markdown em segmentos para o Docs API.
    Cada segmento: {text, heading (1/2/3/None), bullet, bold_ranges [(start, end)]}
    """
    result = []
    for line in text.split("\n"):
        seg = {"text": "", "heading": None, "bullet": False, "bold_ranges": []}

        for lvl, prefix in [(1, "# "), (2, "## "), (3, "### ")]:
            if line.startswith(prefix):
                line = line[len(prefix):]
                seg["heading"] = lvl
                break

        if re.match(r"^[-*] ", line):
            line = line[2:]
            seg["bullet"] = True

        clean, pos = "", 0
        for m in re.finditer(r"\*\*(.+?)\*\*", line):
            clean += line[pos:m.start()]
            start = len(clean)
            clean += m.group(1)
            seg["bold_ranges"].append((start, len(clean)))
            pos = m.end()
        clean += line[pos:]
        seg["text"] = clean
        result.append(seg)
    return result


def _find_placeholder_index(document: dict, placeholder: str) -> int | None:
    for element in document.get("body", {}).get("content", []):
        if "paragraph" not in element:
            continue
        for pe in element["paragraph"].get("elements", []):
            content = pe.get("textRun", {}).get("content", "")
            if placeholder in content:
                return pe["startIndex"] + content.index(placeholder)
    return None


def _apply_content(docs, doc_id: str, segments: list):
    document = docs.documents().get(documentId=doc_id).execute()
    content_index = _find_placeholder_index(document, "{{CONTENT}}")
    if content_index is None:
        raise RuntimeError("Placeholder {{CONTENT}} não encontrado no template")

    # Remove o placeholder
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"deleteContentRange": {"range": {
            "startIndex": content_index,
            "endIndex": content_index + len("{{CONTENT}}"),
        }}}]},
    ).execute()

    # Insere todo o texto de uma vez para que os índices não se deslocam entre inserções
    full_text = "".join(seg["text"] + "\n" for seg in segments)
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": content_index}, "text": full_text}}]},
    ).execute()

    # Aplica estilos com índices corretos (calculados sequencialmente sobre o texto já inserido)
    style_requests = []
    idx = content_index
    for seg in segments:
        line_text = seg["text"] + "\n"
        end_idx = idx + len(line_text)
        text_end = end_idx - 1  # exclui o \n ao aplicar bold em texto

        if seg["heading"]:
            named = {1: "HEADING_1", 2: "HEADING_2", 3: "HEADING_3"}[seg["heading"]]
            style_requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": end_idx},
                "paragraphStyle": {"namedStyleType": named},
                "fields": "namedStyleType",
            }})
            # Garante negrito em todos os títulos
            style_requests.append({"updateTextStyle": {
                "range": {"startIndex": idx, "endIndex": text_end},
                "textStyle": {"bold": True},
                "fields": "bold",
            }})
        if seg["bullet"]:
            style_requests.append({"createParagraphBullets": {
                "range": {"startIndex": idx, "endIndex": end_idx},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }})
        for bstart, bend in seg["bold_ranges"]:
            style_requests.append({"updateTextStyle": {
                "range": {"startIndex": idx + bstart, "endIndex": idx + bend},
                "textStyle": {"bold": True},
                "fields": "bold",
            }})

        idx = end_idx

    if style_requests:
        docs.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": style_requests},
        ).execute()


def export_to_gdocs(
    markdown_content: str,
    doc_type_label: str,
    projeto_nome: str,
    cliente: str,
    sprint_numero: int | None,
    created_at: str,
) -> str:
    template_id = os.environ.get("GDOCS_TEMPLATE_ID", "")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID", "")
    if not template_id or not folder_id:
        raise RuntimeError("GDOCS_TEMPLATE_ID ou GDRIVE_FOLDER_ID não configurados")

    docs, drive = _get_services()

    sprint_label = f"Sprint {sprint_numero}" if sprint_numero else "Projeto completo"
    title = f"{doc_type_label} — {projeto_nome} — {sprint_label}"
    doc_id = _clone_template(drive, template_id, title, folder_id)

    data_fmt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    _replace_placeholders(docs, doc_id, {
        "PROJETO": projeto_nome,
        "CLIENTE": cliente,
        "TIPO_DOC": doc_type_label,
        "SPRINT": sprint_label,
        "DATA": data_fmt,
    })

    segments = _parse_markdown(markdown_content)
    _apply_content(docs, doc_id, segments)

    return f"https://docs.google.com/document/d/{doc_id}/edit"
