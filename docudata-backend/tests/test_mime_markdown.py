from services.file_parser import mime_efetivo


def test_md_sem_tipo_vira_markdown():
    assert mime_efetivo("notas.md", "") == "text/markdown"
    assert mime_efetivo("notas.MD", None) == "text/markdown"
    assert mime_efetivo("notas.md", "application/octet-stream") == "text/markdown"


def test_tipos_existentes_ficam_iguais():
    assert mime_efetivo("a.md", "text/markdown") == "text/markdown"
    assert mime_efetivo("a.pdf", "application/pdf") == "application/pdf"
    assert mime_efetivo("a.png", None) == ""
