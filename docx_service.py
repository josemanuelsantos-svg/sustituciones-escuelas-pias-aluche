"""
Servicio para la generación de documentos Word (.docx) editables
para el Colegio Nuestra Señora de las Escuelas Pías (Aluche).
Gestión de Sustituciones - Vero.
"""

import io
from datetime import datetime
from typing import List
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
from models import SubstitutionRecord

DIAS_SEMANA_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

def set_cell_background(cell, fill_hex: str):
    """Aplica color de fondo hexadecimal a una celda de Word."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
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
    Genera un documento Word (.docx) con la tabla semanal de sustituciones
    siguiendo exactamente los campos y formato que usa Vero en el centro:
    - Quién falta
    - Hora
    - Clase
    - Asignatura
    - Quién sustituye
    - Qué deben hacer en su hora al que le toca
    """
    doc = docx.Document()

    # Configurar márgenes estrechos para que quepa bien la tabla
    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.6)
        section.right_margin = Inches(0.6)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

    # Título y encabezado oficial
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title_p.add_run("COLEGIO NTRA. SRA. DE LAS ESCUELAS PÍAS (ALUCHE)")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(15)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(30, 58, 138)  # Azul Escolapio

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(14)
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    rango_texto = f"Semana del {fecha_inicio} al {fecha_fin}" if fecha_inicio and fecha_fin else "Cuadrante Semanal de Sustituciones"
    run_sub = sub_p.add_run(f"CUADRANTE DE SUSTITUCIONES ESCOLARES — {rango_texto.upper()}\nCoordinación: Vero")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(11)
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    # Columnas de la tabla (las 6 solicitadas + Día/Fecha para organizar la semana)
    headers = [
        "Día / Fecha",
        "Hora",
        "Quién falta",
        "Clase",
        "Asignatura",
        "Quién sustituye",
        "Qué deben hacer en su hora"
    ]
    col_widths = [
        Inches(0.9),   # Día / Fecha
        Inches(1.0),   # Hora
        Inches(1.3),   # Quién falta
        Inches(0.8),   # Clase
        Inches(1.1),   # Asignatura
        Inches(1.3),   # Quién sustituye
        Inches(1.6),   # Qué deben hacer
    ]

    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Estilizar encabezado
    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(headers):
        cell = hdr_cells[i]
        cell.width = col_widths[i]
        set_cell_background(cell, "1E3A8A")  # Azul oscuro
        set_cell_margins(cell, top=140, bottom=140, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(h_text)
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)

    # Ordenar sustituciones por fecha, tramo
    ordenadas = sorted(sustituciones, key=lambda s: (s.fecha, s.periodo_id))

    if not ordenadas:
        row = table.add_row()
        cell = row.cells[0]
        # Merge de todas las celdas
        for c in row.cells[1:]:
            cell.merge(c)
        set_cell_margins(cell, top=200, bottom=200, left=150, right=150)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("No hay sustituciones registradas para este periodo.")
        run.font.name = "Calibri"
        run.font.italic = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(148, 163, 184)
    else:
        for idx, sub in enumerate(ordenadas):
            row = table.add_row()
            bg_color = "F8FAFC" if idx % 2 == 1 else "FFFFFF"

            # Formatear día en texto
            dia_str = sub.fecha
            try:
                dt = datetime.strptime(sub.fecha, "%Y-%m-%d")
                dia_str = f"{DIAS_SEMANA_ES[dt.weekday()][:3]}. {dt.day}/{dt.month}"
            except Exception:
                pass

            hora_corta = sub.periodo_nombre.replace(" (", "\n(").replace("ª Hora", "ªH")
            que_hacer = sub.que_hacer or sub.observaciones or "—"

            row_data = [
                dia_str,
                hora_corta,
                sub.profesor_ausente_nombre,
                sub.curso_grupo or sub.aula or "—",
                sub.materia or "—",
                sub.profesor_sustituto_nombre,
                que_hacer
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
                
                # Alineación
                if c_idx in [0, 1, 3]:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                run = p.add_run(val)
                run.font.name = "Calibri"
                run.font.size = Pt(9)
                if c_idx == 5:  # Profesor sustituto en negrita
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(30, 58, 138)
                elif c_idx == 6:  # Qué deben hacer
                    run.font.color.rgb = RGBColor(30, 41, 59)
                else:
                    run.font.color.rgb = RGBColor(51, 65, 85)

    # Pie de página / Nota
    nota_p = doc.add_paragraph()
    nota_p.paragraph_format.space_before = Pt(14)
    nota_p.paragraph_format.space_after = Pt(0)
    nota_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_nota = nota_p.add_run(f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')} · Sistema de Sustituciones Escuelas Pías Aluche")
    run_nota.font.name = "Calibri"
    run_nota.font.size = Pt(8)
    run_nota.font.italic = True
    run_nota.font.color.rgb = RGBColor(148, 163, 184)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
