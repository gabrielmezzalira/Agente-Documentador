import io
import json
import os
import re
from datetime import datetime

from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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


def _get_or_create_folder(drive, name: str, parent_id: str) -> str:
    """Retorna o ID de uma pasta com `name` dentro de `parent_id`, criando se não existir."""
    q = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        f" and '{parent_id}' in parents and trashed=false"
    )
    result = drive.files().list(q=q, fields="files(id)", supportsAllDrives=True).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    folder = drive.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return folder["id"]


def _clone_template(drive, template_id: str, title: str, folder_id: str) -> str:
    meta = drive.files().get(
        fileId=template_id, fields="mimeType", supportsAllDrives=True
    ).execute()

    if meta["mimeType"] == "application/vnd.google-apps.document":
        copy = drive.files().copy(
            fileId=template_id,
            body={"name": title, "parents": [folder_id]},
            supportsAllDrives=True,
        ).execute()
        return copy["id"]

    # DOCX (ou outro Office): baixa e re-faz upload convertendo para Google Doc nativo.
    # files.copy com mimeType diferente NÃO converte — só download+create faz a conversão.
    content = drive.files().get_media(fileId=template_id).execute()
    media = MediaIoBaseUpload(
        io.BytesIO(content), mimetype=meta["mimeType"], resumable=False
    )
    new_file = drive.files().create(
        body={
            "name": title,
            "parents": [folder_id],
            "mimeType": "application/vnd.google-apps.document",
        },
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return new_file["id"]


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
    def _search_paragraphs(elements):
        for el in elements:
            if "paragraph" in el:
                for pe in el["paragraph"].get("elements", []):
                    content = pe.get("textRun", {}).get("content", "")
                    if placeholder in content:
                        return pe["startIndex"] + content.index(placeholder)
            elif "table" in el:
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        result = _search_paragraphs(cell.get("content", []))
                        if result is not None:
                            return result
        return None

    return _search_paragraphs(document.get("body", {}).get("content", []))


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


_TEMPLATE_ENV_BY_DOC_TYPE = {
    "planning": "GDOCS_TEMPLATE_ID_PLANNING",
    "review": "GDOCS_TEMPLATE_ID_REVIEW",
    "retrospectiva": "GDOCS_TEMPLATE_ID_RETROSPECTIVA",
}

# Mapeamento: trecho do header markdown (lowercase) → nome do placeholder no template
_SECTION_PLACEHOLDERS = {
    "planning": {
        "backlog da sprint": "BACKLOG",
        "riscos previstos":  "RISCOS",
    },
    "review": {
        "o que foi planejado":              "PLANEJADO_ENTREGUE",
        "o que foi efetivamente realizado": "REALIZADO",
        "delta":                            "DELTA",
        "decisões tomadas durante a sprint":"DECISOES",
        "impedimentos enfrentados":         "IMPEDIMENTOS",
        "aprendizados para próxima sprint": "APRENDIZADOS",
        "itens que passam para a próxima":  "ITENS_PROXIMA_SPRINT",
    },
    "retrospectiva": {
        "o que funcionou":           "O_QUE_FUNCIONOU",
        "o que não funcionou":       "O_QUE_NAO_FUNCIONOU",
        "causa raiz":                "CAUSA_RAIZ_IMPACTO",
        "ações de melhoria":         "ACOES_MELHORIA",
        "pedido fora de escopo":     "PEDIDO_FORA_ESCOPO_STATUS",
    },
}


def _format_backlog_items(raw: str) -> str:
    """Extrai só os nomes dos itens do backlog, um por linha, sem anotações de campo.

    O markdown de planning gera "- Item — Responsável: X — Prazo: Y — DoD: Z",
    mas o template tem colunas separadas para cada campo. Aqui ficam só os itens.
    """
    items = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            line = line[2:]
        item = line.split(" — ")[0].strip()
        if item:
            items.append(item)
    return "\n".join(items)


def _extract_section_replacements(markdown: str, doc_type: str) -> dict:
    """Parseia o markdown por headers ## e mapeia seções a placeholders do template."""
    mapping = _SECTION_PLACEHOLDERS.get(doc_type, {})
    if not mapping:
        return {}

    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in markdown.split("\n"):
        stripped = line.lstrip("# ")
        if line.startswith("## ") or line.startswith("# "):
            current = stripped.lower()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)

    result: dict[str, str] = {}
    for section_key, placeholder in mapping.items():
        for header, lines in sections.items():
            if section_key in header:
                content = "\n".join(lines).strip()
                if placeholder == "BACKLOG":
                    content = _format_backlog_items(content)
                result[placeholder] = content
                break

    return result


def export_to_gdocs(
    markdown_content: str,
    doc_type_label: str,
    projeto_nome: str,
    cliente: str,
    sprint_numero: int | None,
    created_at: str,
    doc_type: str = "",
) -> str:
    env_key = _TEMPLATE_ENV_BY_DOC_TYPE.get(doc_type, "")
    template_id = (env_key and os.environ.get(env_key, "")) or os.environ.get("GDOCS_TEMPLATE_ID", "")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID", "")
    if not template_id or not folder_id:
        raise RuntimeError("GDOCS_TEMPLATE_ID ou GDRIVE_FOLDER_ID não configurados")

    docs, drive = _get_services()

    sprint_label = f"Sprint {sprint_numero}" if sprint_numero else "Projeto completo"
    title = f"{doc_type_label} — {projeto_nome} — {sprint_label}"

    # Hierarquia: pasta raiz → pasta do projeto → pasta da sprint (ou Cross-Sprint)
    project_folder_id = _get_or_create_folder(drive, projeto_nome, folder_id)
    sprint_folder_name = f"Sprint {sprint_numero}" if sprint_numero else "Cross-Sprint"
    sprint_folder_id = _get_or_create_folder(drive, sprint_folder_name, project_folder_id)

    doc_id = _clone_template(drive, template_id, title, sprint_folder_id)

    data_fmt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    _replace_placeholders(docs, doc_id, {
        "PROJETO": projeto_nome,
        "CLIENTE": cliente,
        "TIPO_DOC": doc_type_label,
        "SPRINT": sprint_label,
        "SPRINT_NUM": str(sprint_numero) if sprint_numero else "—",
        "DATA": data_fmt,
        "SQUAD": "[A definir]",
        "PERIODO": "[A definir]",
    })

    # Substitui placeholders de seção ({{BACKLOG}}, {{RISCOS}}, etc.) se o template os tiver
    section_replacements = _extract_section_replacements(markdown_content, doc_type)
    if section_replacements:
        _replace_placeholders(docs, doc_id, section_replacements)
    else:
        # {{CONTENT}} recebe o markdown completo como fallback (templates sem placeholders de seção)
        segments = _parse_markdown(markdown_content)
        _apply_content(docs, doc_id, segments)

    return f"https://docs.google.com/document/d/{doc_id}/edit"
