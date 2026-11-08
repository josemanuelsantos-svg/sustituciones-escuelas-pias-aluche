"""
Servicio para la generación de documentos Word (.docx) editables
para el Colegio Nuestra Señora de las Escuelas Pías (Aluche).
Gestión de Sustituciones - Vero.
"""

import io
import os
from datetime import datetime
from typing import List, Dict
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
from models import SubstitutionRecord

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "static", "img", "logo_escuelas_pias.png")

DIAS_SEMANA_ES = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
MESES_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def set_cell_background(cell, fill_hex: str):
    """Aplica color de fondo hexadecimal a una celda de Word."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=140, right=140):
    """Aplica márgenes internos (padding) a una celda."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def generate_weekly_docx(sustituciones: List[SubstitutionRecord], fecha_inicio: str = "", fecha_fin: str = "") -> io.BytesIO:
    """
    Genera un documento Word (.docx) profesional con el logo oficial del centro,
    agrupado por días de la semana y con las 6 columnas exactas + casilla de firma.
    """
    doc = docx.Document()

    # Configuración de página horizontal o vertical con márgenes cómodos
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

    # 1. ENCABEZADO CON LOGO OFICIAL
    header_table = doc.add_table(rows=1, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_table.autofit = False
    
    cell_logo = header_table.rows[0].cells[0]
    cell_info = header_table.rows[0].cells[1]
    cell_logo.width = Inches(3.2)
    cell_info.width = Inches(4.3)

    # Insertar logo si existe
    if os.path.exists(LOGO_PATH):
        try:
            p_logo = cell_logo.paragraphs[0]
            p_logo.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p_logo.paragraph_format.space_before = Pt(0)
            p_logo.paragraph_format.space_after = Pt(0)
            p_logo.add_run().add_picture(LOGO_PATH, width=Inches(2.5))
        except Exception:
            p_logo = cell_logo.paragraphs[0]
            p_logo.add_run("ESCUELAS PÍAS ALUCHE").bold = True
    else:
        p_logo = cell_logo.paragraphs[0]
        p_logo.add_run("ESCUELAS PÍAS ALUCHE").bold = True

    # Texto del encabezado a la derecha
    p_info = cell_info.paragraphs[0]
    p_info.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_info.paragraph_format.space_before = Pt(0)
    p_info.paragraph_format.space_after = Pt(0)

    run_title = p_info.add_run("CUADRANTE DE SUSTITUCIONES ESCOLARES\n")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(13)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(30, 58, 138)

    rango_texto = f"Semana del {fecha_inicio} al {fecha_fin}" if fecha_inicio and fecha_fin else "Documento Semanal Compartido"
    run_sub = p_info.add_run(f"{rango_texto}\n")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(10)
    run_sub.font.bold = True
    run_sub.font.color.rgb = RGBColor(71, 85, 105)

    run_coord = p_info.add_run("Coordinación: Vero · Infantil y Primaria")
    run_coord.font.name = "Calibri"
    run_coord.font.size = Pt(9)
    run_coord.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 2. AGRUPAR SUSTITUCIONES POR FECHA / DÍA
    grupos_por_dia: Dict[str, List[SubstitutionRecord]] = {}
    for s in sorted(sustituciones, key=lambda x: (x.fecha, x.periodo_id)):
        if s.fecha not in grupos_por_dia:
            grupos_por_dia[s.fecha] = []
        grupos_por_dia[s.fecha].append(s)

    headers = [
        "Hora",
        "Quién falta",
        "Clase",
        "Asignatura",
        "Quién sustituye",
        "Qué deben hacer en su hora",
        "Firma / OK"
    ]
    col_widths = [
        Inches(1.0),   # Hora
        Inches(1.3),   # Quién falta
        Inches(0.8),   # Clase
        Inches(1.2),   # Asignatura
        Inches(1.3),   # Quién sustituye
        Inches(1.6),   # Qué deben hacer
        Inches(0.6)    # Firma / OK
    ]

    if not grupos_por_dia:
        p_vacio = doc.add_paragraph()
        p_vacio.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_vacio.paragraph_format.space_before = Pt(20)
        run_vacio = p_vacio.add_run("No hay sustituciones registradas para esta semana.")
        run_vacio.font.italic = True
        run_vacio.font.size = Pt(11)
        run_vacio.font.color.rgb = RGBColor(148, 163, 184)
    else:
        for fecha_str, items in grupos_por_dia.items():
            # Encabezado del día (ej. LUNES, 10 DE NOVIEMBRE)
            dia_nombre = fecha_str
            try:
                dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                dia_nombre = f"{DIAS_SEMANA_ES[dt.weekday()]}, {dt.day} DE {MESES_ES[dt.month].upper()} DE {dt.year}"
            except Exception:
                pass

            p_dia = doc.add_paragraph()
            p_dia.paragraph_format.space_before = Pt(10)
            p_dia.paragraph_format.space_after = Pt(3)
            run_dia = p_dia.add_run(f"📅  {dia_nombre}")
            run_dia.font.name = "Calibri"
            run_dia.font.size = Pt(11)
            run_dia.font.bold = True
            run_dia.font.color.rgb = RGBColor(30, 58, 138)

            # Tabla del día
            table = doc.add_table(rows=1, cols=len(headers))
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False

            # Cabecera de la tabla
            hdr_cells = table.rows[0].cells
            for i, h_text in enumerate(headers):
                cell = hdr_cells[i]
                cell.width = col_widths[i]
                set_cell_background(cell, "1E3A8A")  # Azul Escolapio
                set_cell_margins(cell, top=130, bottom=130, left=100, right=100)
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(h_text)
                run.font.name = "Calibri"
                run.font.size = Pt(9)
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)

            # Filas de sustituciones
            for idx, sub in enumerate(items):
                row = table.add_row()
                bg_color = "F8FAFC" if idx % 2 == 1 else "FFFFFF"

                hora_corta = sub.periodo_nombre.replace(" (", "\n(").replace("ª Hora", "ªH")
                que_hacer = sub.que_hacer or sub.observaciones or "—"

                row_data = [
                    hora_corta,
                    sub.profesor_ausente_nombre,
                    sub.curso_grupo or sub.aula or "—",
                    sub.materia or "—",
                    sub.profesor_sustituto_nombre,
                    que_hacer,
                    "[   ]"
                ]

                for c_idx, val in enumerate(row_data):
                    cell = row.cells[c_idx]
                    cell.width = col_widths[c_idx]
                    set_cell_background(cell, bg_color)
                    set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
                    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)

                    if c_idx in [0, 2, 6]:
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    else:
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                    run = p.add_run(val)
                    run.font.name = "Calibri"
                    run.font.size = Pt(9)
                    if c_idx == 4:  # Sustituto
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(30, 58, 138)
                    elif c_idx == 5:  # Tarea
                        run.font.color.rgb = RGBColor(15, 23, 42)
                    elif c_idx == 6:  # Firma
                        run.font.color.rgb = RGBColor(148, 163, 184)
                    else:
                        run.font.color.rgb = RGBColor(51, 65, 85)

    # 3. PIE DE PÁGINA
    p_footer = doc.add_paragraph()
    p_footer.paragraph_format.space_before = Pt(16)
    p_footer.paragraph_format.space_after = Pt(0)
    p_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_foot = p_footer.add_run(f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')} · Colegio Ntra. Sra. de las Escuelas Pías (Aluche)")
    run_foot.font.name = "Calibri"
    run_foot.font.size = Pt(8)
    run_foot.font.italic = True
    run_foot.font.color.rgb = RGBColor(148, 163, 184)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
