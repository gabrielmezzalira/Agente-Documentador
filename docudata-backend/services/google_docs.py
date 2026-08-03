import io
import json
import os
import re
from datetime import datetime

from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from services.supabase_client import get_client

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

        # Linhas separadoras de tabela (|---|---|) — ignora
        if re.match(r"^\|[\s\-|:]+\|?\s*$", line):
            continue

        # Linhas de tabela (| col | col |) — converte em bullet "col — col"
        if line.startswith("|") and line.count("|") >= 2:
            cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
            if cells:
                seg["text"] = " — ".join(cells)
                seg["bullet"] = True
                result.append(seg)
            continue

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

        # Fonte Calibri para todo texto inserido (heading ou normal)
        style_requests.append({"updateTextStyle": {
            "range": {"startIndex": idx, "endIndex": text_end},
            "textStyle": {"weightedFontFamily": {"fontFamily": "Calibri"}},
            "fields": "weightedFontFamily",
        }})

        if seg["heading"]:
            named = {1: "HEADING_1", 2: "HEADING_2", 3: "HEADING_3"}[seg["heading"]]
            style_requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": end_idx},
                "paragraphStyle": {"namedStyleType": named},
                "fields": "namedStyleType",
            }})
            # Negrito, cor preta e Calibri (sobrescreve a cor azul do estilo Heading)
            style_requests.append({"updateTextStyle": {
                "range": {"startIndex": idx, "endIndex": text_end},
                "textStyle": {
                    "bold": True,
                    "foregroundColor": {"color": {"rgbColor": {"red": 0.0, "green": 0.0, "blue": 0.0}}},
                    "weightedFontFamily": {"fontFamily": "Calibri"},
                },
                "fields": "bold,foregroundColor,weightedFontFamily",
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


def _fmt_date(s: str) -> str:
    """Converte YYYY-MM-DD para DD/MM/AAAA."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else s


def _find_table_marker(document: dict, marker: str) -> tuple[int | None, int | None]:
    """Retorna (table_start_index, row_index) da linha que contém o marker."""
    for el in document.get("body", {}).get("content", []):
        if "table" not in el:
            continue
        for r_idx, row in enumerate(el["table"].get("tableRows", [])):
            for cell in row.get("tableCells", []):
                for para in cell.get("content", []):
                    for pe in para.get("paragraph", {}).get("elements", []):
                        if marker in pe.get("textRun", {}).get("content", ""):
                            return el["startIndex"], r_idx
    return None, None


def _fill_dynamic_table(docs, doc_id: str, marker: str, rows_data: list[list[str]]) -> None:
    """Deleta a linha de template com `marker`, insere uma linha por item e preenche as células."""
    document = docs.documents().get(documentId=doc_id).execute()
    table_start, row_idx = _find_table_marker(document, marker)
    if table_start is None:
        return

    # 1. Deletar linha de template
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": [{
        "deleteTableRow": {
            "tableCellLocation": {
                "tableStartLocation": {"index": table_start},
                "rowIndex": row_idx,
            }
        }
    }]}).execute()

    if not rows_data:
        return

    # 2. Inserir N linhas em sequência (rowIndex incrementa para manter a ordem)
    header_row = max(0, row_idx - 1)
    insert_requests = [
        {
            "insertTableRow": {
                "tableCellLocation": {
                    "tableStartLocation": {"index": table_start},
                    "rowIndex": header_row + i,
                },
                "insertBelow": True,
            }
        }
        for i in range(len(rows_data))
    ]
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": insert_requests}).execute()

    # 2b. Resetar estilo das linhas inseridas: fundo branco, texto normal
    num_cols = max(len(r) for r in rows_data) if rows_data else 0
    style_requests = []
    for row_offset in range(len(rows_data)):
        actual_row_idx = row_idx + row_offset
        for col_idx in range(num_cols):
            style_requests.append({
                "updateTableCellStyle": {
                    "tableCellStyle": {
                        "backgroundColor": {
                            "color": {"rgbColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
                        }
                    },
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": table_start},
                            "rowIndex": actual_row_idx,
                            "columnIndex": col_idx,
                        },
                        "rowSpan": 1,
                        "columnSpan": 1,
                    },
                    "fields": "backgroundColor",
                }
            })
    if style_requests:
        docs.documents().batchUpdate(documentId=doc_id, body={"requests": style_requests}).execute()

    # 3. Re-buscar documento e preencher células
    document = docs.documents().get(documentId=doc_id).execute()
    target_table = next(
        (el["table"] for el in document.get("body", {}).get("content", [])
         if "table" in el and el.get("startIndex") == table_start),
        None,
    )
    if target_table is None:
        return

    fill: list[tuple[int, str]] = []
    for row_offset, row_values in enumerate(rows_data):
        actual_row_idx = row_idx + row_offset
        if actual_row_idx >= len(target_table["tableRows"]):
            break
        row = target_table["tableRows"][actual_row_idx]
        for col_idx, cell_value in enumerate(row_values):
            if not cell_value or col_idx >= len(row["tableCells"]):
                continue
            elements = (
                row["tableCells"][col_idx]
                .get("content", [{}])[0]
                .get("paragraph", {})
                .get("elements", [])
            )
            if elements:
                fill.append((elements[0]["startIndex"], cell_value))

    # Preencher de trás pra frente para não deslocar índices
    fill.sort(key=lambda x: x[0], reverse=True)
    if fill:
        docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
            {"insertText": {"location": {"index": idx}, "text": val}}
            for idx, val in fill
        ]}).execute()

        # Resetar negrito e cor do texto inserido (re-busca índices após insertText)
        document = docs.documents().get(documentId=doc_id).execute()
        target_table = next(
            (el["table"] for el in document.get("body", {}).get("content", [])
             if "table" in el and el.get("startIndex") == table_start),
            None,
        )
        text_style_requests = []
        if target_table:
            for row_offset in range(len(rows_data)):
                actual_row_idx = row_idx + row_offset
                if actual_row_idx >= len(target_table["tableRows"]):
                    break
                for cell in target_table["tableRows"][actual_row_idx].get("tableCells", []):
                    for para in cell.get("content", []):
                        for pe in para.get("paragraph", {}).get("elements", []):
                            content = pe.get("textRun", {}).get("content", "")
                            if content.strip():
                                end = pe["endIndex"] - (1 if content.endswith("\n") else 0)
                                text_style_requests.append({
                                    "updateTextStyle": {
                                        "range": {"startIndex": pe["startIndex"], "endIndex": end},
                                        "textStyle": {
                                            "bold": False,
                                            "foregroundColor": {
                                                "color": {"rgbColor": {"red": 0.0, "green": 0.0, "blue": 0.0}}
                                            },
                                        },
                                        "fields": "bold,foregroundColor",
                                    }
                                })
        if text_style_requests:
            docs.documents().batchUpdate(documentId=doc_id, body={"requests": text_style_requests}).execute()


_TEMPLATE_ENV_BY_DOC_TYPE = {
    "planning": "GDOCS_TEMPLATE_ID_PLANNING",
    "review": "GDOCS_TEMPLATE_ID_REVIEW",
    "retrospectiva": "GDOCS_TEMPLATE_ID_RETROSPECTIVA",
}



def export_to_gdocs(
    project_id: str,
    markdown_content: str,
    doc_type_label: str,
    projeto_nome: str,
    cliente: str,
    sprint_numero: int | None,
    created_at: str,
    doc_type: str = "",
    squad: str = "—",
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

    # Busca campos estruturados do Supabase conforme o tipo de doc
    campos_planning: dict = {}
    campos_review: dict = {}
    campos_retrospectiva: dict = {}
    if doc_type == "planning" and sprint_numero is not None:
        client = get_client()
        resp = (
            client.table("ingestions")
            .select("extracted_content")
            .eq("project_id", project_id)
            .eq("sprint_number", sprint_numero)
            .eq("tipo_documentacao", "planning")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            campos_planning = resp.data[0].get("extracted_content", {}).get("campos_planning", {}) or {}

    if doc_type == "review" and sprint_numero is not None:
        client = get_client()
        resp = (
            client.table("ingestions")
            .select("extracted_content")
            .eq("project_id", project_id)
            .eq("sprint_number", sprint_numero)
            .eq("tipo_documentacao", "review")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            campos_review = resp.data[0].get("extracted_content", {}).get("campos_review", {}) or {}

    if doc_type == "retrospectiva" and sprint_numero is not None:
        client = get_client()
        resp = (
            client.table("ingestions")
            .select("extracted_content")
            .eq("project_id", project_id)
            .eq("sprint_number", sprint_numero)
            .eq("tipo_documentacao", "retrospectiva")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            campos_retrospectiva = resp.data[0].get("extracted_content", {}).get("campos_retrospectiva", {}) or {}

    def _cp(source: dict, key: str, default: str = "Não informado") -> str:
        return str(source.get(key) or default)

    def _col(items: list, key: str) -> str:
        return "\n".join(str(it.get(key, "") or "") for it in items)

    if doc_type == "planning":
        pi_raw = _cp(campos_planning, "periodo_inicio")
        pf_raw = _cp(campos_planning, "periodo_fim")
        pi = _fmt_date(pi_raw) if pi_raw not in ("—", "Não informado") else pi_raw
        pf = _fmt_date(pf_raw) if pf_raw not in ("—", "Não informado") else pf_raw
        periodo = f"{pi} a {pf}" if pi not in ("—", "Não informado") and pf not in ("—", "Não informado") else pi
        horas_reais = _cp(campos_planning, "horas_disponiveis")
        horas_estimadas = _cp(campos_planning, "horas_estimadas")
        bl  = campos_planning.get("backlog_items") or []
        dep = campos_planning.get("dependencias_items") or []
        ris = campos_planning.get("riscos_items") or []
        co  = campos_planning.get("carry_over_items") or []
    else:
        periodo = "—"
        horas_reais = "—"
        horas_estimadas = "—"
        bl = dep = ris = co = []

    if doc_type == "review":
        percepcao_cliente = _cp(campos_review, "percepcao_cliente")
        sinal_satisfacao = _cp(campos_review, "sinal_satisfacao")
        pedidos_fora_escopo = _cp(campos_review, "pedidos_fora_escopo")
    else:
        percepcao_cliente = "—"
        sinal_satisfacao = "—"
        pedidos_fora_escopo = "—"

    if doc_type == "retrospectiva":
        retro_observacoes = _cp(campos_retrospectiva, "observacoes")
        pedido_fora_escopo_status = _cp(campos_retrospectiva, "pedido_fora_escopo_status")
    else:
        retro_observacoes = "—"
        pedido_fora_escopo_status = "—"

    _replace_placeholders(docs, doc_id, {
        "PROJETO": projeto_nome,
        "CLIENTE": cliente,
        "TIPO_DOC": doc_type_label,
        "SPRINT": sprint_label,
        "SPRINT_NUM": str(sprint_numero) if sprint_numero else "—",
        "DATA": data_fmt,
        "SQUAD": squad,
        "PERIODO": periodo,
        "HORAS_REAIS": horas_reais,
        "HORAS_ESTIMADAS": horas_estimadas,
        "PERCEPCAO_CLIENTE": percepcao_cliente,
        "PEDIDO_FORA_ESCOPO_STATUS": pedido_fora_escopo_status,
        "OBSERVACOES_RETRO": retro_observacoes,
        "SINAL_SATISFACAO": sinal_satisfacao,
        "PEDIDOS_FORA_ESCOPO": pedidos_fora_escopo,
    })

    # Tabelas dinâmicas — uma linha por item (planning only)
    if doc_type == "planning":
        _fill_dynamic_table(docs, doc_id, "{{BACKLOG}}",
            [[i.get("item",""), i.get("responsavel",""), i.get("prazo",""), i.get("criterio","")] for i in bl])
        _fill_dynamic_table(docs, doc_id, "{{DEPENDENCIAS_CLIENTE}}",
            [[d.get("item",""), d.get("prazo",""), d.get("consequencia",""), d.get("confianca","")] for d in dep])
        _fill_dynamic_table(docs, doc_id, "{{RISCOS}}",
            [[r.get("risco",""), r.get("consequencia","")] for r in ris])
        _fill_dynamic_table(docs, doc_id, "{{CARRY_OVER}}",
            [[c.get("item",""), c.get("causa_raiz","")] for c in co])

    # Append structured fields to content so templates only need {{CONTENT}}
    if doc_type == "review":
        addendum = ""
        if percepcao_cliente not in ("—", "Não informado", ""):
            addendum += f"\n\n## Percepção do Cliente\n\n{percepcao_cliente}"
        if sinal_satisfacao not in ("—", "Não informado", ""):
            addendum += f"\n\n## Sinal de Satisfação do Cliente\n\n{sinal_satisfacao}"
        if pedidos_fora_escopo not in ("—", "Não informado", ""):
            addendum += f"\n\n## Pedidos Fora do Escopo\n\n{pedidos_fora_escopo}"
        markdown_content = markdown_content + addendum

    if doc_type == "retrospectiva":
        addendum = ""
        if pedido_fora_escopo_status not in ("—", "Não informado", ""):
            addendum += f"\n\n## Houve Pedido Fora de Escopo Nesta Sprint?\n\n{pedido_fora_escopo_status}"
        if retro_observacoes not in ("—", "Não informado", ""):
            addendum += f"\n\n## Observações\n\n{retro_observacoes}"
        markdown_content = markdown_content + addendum

    segments = _parse_markdown(markdown_content)
    _apply_content(docs, doc_id, segments)

    return f"https://docs.google.com/document/d/{doc_id}/edit"
