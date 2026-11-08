"""
Script de importación y migración de horarios oficiales para
Colegio Nuestra Señora de las Escuelas Pías (Aluche).
Gestión de Sustituciones - Vero.
"""

import os
import re
import json
import sqlite3
import unicodedata
import fitz  # PyMuPDF
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

PDF_PRIMARIA = "/Users/jose/.gemini/antigravity/brain/b91cef92-d8c3-4131-9efd-822788d59eee/.user_uploaded/media_1794118243755_1ccbf640.pdf"
PDF_INFANTIL = "/Users/jose/.gemini/antigravity/brain/b91cef92-d8c3-4131-9efd-822788d59eee/.user_uploaded/media_1794118243755_92d6cb3b.pdf"

SUBJECT_MAP = {
    "MAT": "Matemáticas",
    "LEN": "Lengua Castellana y Literatura",
    "ING": "Lengua extranjera: Inglés",
    "NAT": "Ciencias de la Naturaleza",
    "SOC": "Ciencias Sociales",
    "EFI": "Educación Física",
    "EPV": "Educación Plástica y visual",
    "REL": "Religión",
    "VAL": "Educación en Valores Cívicos y Éticos",
    "MYD": "Música y Danza",
    "ELE": "Español como Lengua Extranjera (Aula Enlace)",
    "CRR3": "Comunicación y Representación de la Realidad (3 años)",
    "CRR4": "Comunicación y Representación de la Realidad (4 años)",
    "CRR5": "Comunicación y Representación de la Realidad (5 años)",
    "DEE3": "Descubrimiento y Exploración del Entorno (3 años)",
    "DEE4": "Descubrimiento y Exploración del Entorno (4 años)",
    "DEE5": "Descubrimiento y Exploración del Entorno (5 años)",
    "CEA3": "Crecimiento en Armonía (3 años)",
    "CEA4": "Crecimiento en Armonía (4 años)",
    "CEA5": "Crecimiento en Armonía (5 años)",
    "ING3": "Inglés (3 años)",
    "ING4": "Inglés (4 años)",
    "ING5": "Inglés (5 años)",
    "REL3": "Religión (3 años)",
    "REL5": "Religión (5 años)"
}

TRAMOS_OFICIALES = [
    {
        "id": "1H",
        "nombre": "1ª Hora (09:05 - 10:05)",
        "hora_inicio": "09:05",
        "hora_fin": "10:05",
        "es_recreo": False,
        "orden": 1,
        "etapa": "General"
    },
    {
        "id": "2H",
        "nombre": "2ª Hora (10:05 - 11:05)",
        "hora_inicio": "10:05",
        "hora_fin": "11:05",
        "es_recreo": False,
        "orden": 2,
        "etapa": "General"
    },
    {
        "id": "REC",
        "nombre": "Recreo (11:05 - 11:35)",
        "hora_inicio": "11:05",
        "hora_fin": "11:35",
        "es_recreo": True,
        "orden": 3,
        "etapa": "General"
    },
    {
        "id": "3H",
        "nombre": "3ª Hora (11:35 - 12:35)",
        "hora_inicio": "11:35",
        "hora_fin": "12:35",
        "es_recreo": False,
        "orden": 4,
        "etapa": "General"
    },
    {
        "id": "MED",
        "nombre": "Comedor (12:35 - 14:30)",
        "hora_inicio": "12:35",
        "hora_fin": "14:30",
        "es_recreo": True,
        "orden": 5,
        "etapa": "General"
    },
    {
        "id": "4H",
        "nombre": "4ª Hora (14:30 - 15:30)",
        "hora_inicio": "14:30",
        "hora_fin": "15:30",
        "es_recreo": False,
        "orden": 6,
        "etapa": "General"
    },
    {
        "id": "5H",
        "nombre": "5ª Hora (15:30 - 16:30)",
        "hora_inicio": "15:30",
        "hora_fin": "16:30",
        "es_recreo": False,
        "orden": 7,
        "etapa": "General"
    }
]

def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")

def format_teacher_name(raw_name: str) -> str:
    raw_name = raw_name.strip()
    if "," in raw_name:
        parts = raw_name.split(",", 1)
        apellidos = parts[0].strip()
        nombre = parts[1].strip()
        return f"{nombre} {apellidos}"
    return raw_name

def generate_teacher_id(raw_name: str) -> str:
    cleaned = strip_accents(raw_name).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return cleaned

def parse_pdf_schedules(pdf_path: str, default_etapa: str) -> Dict[str, Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    teachers = {}
    
    slot_mapping = {
        "De 09:05 a 10:05": "1H",
        "De 10:05 a 11:05": "2H",
        "De 11:35 a 12:35": "3H",
        "De 14:30 a 15:30": "4H",
        "De 15:30 a 16:30": "5H"
    }
    
    for page in doc:
        text = page.get_text()
        m = re.search(r"HORARIO DE(?: LA PROFESORA|L PROFESOR)\s*\n\s*([^\n]+)", text)
        if not m:
            continue
        raw_name = m.group(1).strip()
        t_id = generate_teacher_id(raw_name)
        display_name = format_teacher_name(raw_name)
        
        tables = page.find_tables().tables
        if not tables:
            continue
        table_data = tables[0].extract()
        
        schedule_items = []
        for row in table_data[1:]:
            slot_raw = row[0].strip() if row and row[0] else ""
            if slot_raw not in slot_mapping:
                continue
            periodo_id = slot_mapping[slot_raw]
            
            for day_idx in range(5):  # 0=Lunes .. 4=Viernes
                cell = row[day_idx + 1].strip() if len(row) > day_idx + 1 and row[day_idx + 1] else ""
                
                materia = ""
                curso_grupo = ""
                descripcion = ""
                
                if not cell:
                    tipo_actividad = "REUNION"
                    descripcion = "Hueco no lectivo libre"
                elif ":" in cell:
                    parts = cell.split(":", 1)
                    code = parts[0].strip()
                    curso_grupo = parts[1].strip()
                    materia = SUBJECT_MAP.get(code, code)
                    tipo_actividad = "LECTIVA"
                    descripcion = f"{materia} ({curso_grupo})"
                else:
                    norm = cell.lower()
                    if "guardia" in norm:
                        tipo_actividad = "GUARDIA"
                        descripcion = "Guardia"
                    elif "apoyo" in norm:
                        tipo_actividad = "APOYO"
                        descripcion = cell
                    else:
                        tipo_actividad = "REUNION"
                        descripcion = cell
                
                schedule_items.append({
                    "profesor_id": t_id,
                    "dia_semana": day_idx,
                    "periodo_id": periodo_id,
                    "tipo_actividad": tipo_actividad,
                    "aula": curso_grupo if curso_grupo else "",
                    "materia": materia,
                    "curso_grupo": curso_grupo,
                    "descripcion": descripcion
                })
        
        teachers[t_id] = {
            "id": t_id,
            "raw_name": raw_name,
            "nombre": display_name,
            "telefono": "",
            "email": f"{t_id}@escolapiosaluche.com",
            "departamento": default_etapa,
            "etapa": default_etapa,
            "activo": True,
            "sustituciones_realizadas": 0,
            "schedule": schedule_items
        }
    return teachers

def migrate():
    print("Iniciando extracción de Escuelas Pías Aluche...")
    pri = parse_pdf_schedules(PDF_PRIMARIA, "Primaria")
    inf = parse_pdf_schedules(PDF_INFANTIL, "Infantil")
    
    # Docentes combinados
    all_teachers = {}
    for tid, tdata in inf.items():
        all_teachers[tid] = tdata
    
    for tid, tdata in pri.items():
        if tid in all_teachers:
            # Aparece en ambos: por ejemplo María Hernández o Ignacio Luengo
            all_teachers[tid]["etapa"] = "Primaria"
            all_teachers[tid]["departamento"] = "Primaria / Infantil"
            # Unificar horarios si hiciera falta (son idénticos según comprobación previa)
        else:
            all_teachers[tid] = tdata
            
    print(f"Total profesores extraídos: {len(all_teachers)}")
    
    # Exportar JSONs limpios a data/
    teachers_export = []
    horarios_export = []
    
    for tid, t in sorted(all_teachers.items(), key=lambda x: x[1]["nombre"]):
        teachers_export.append({
            "id": t["id"],
            "nombre": t["nombre"],
            "telefono": t["telefono"],
            "email": t["email"],
            "departamento": t["departamento"],
            "etapa": t["etapa"],
            "activo": t["activo"],
            "sustituciones_realizadas": 0
        })
        for s in t["schedule"]:
            horarios_export.append({
                "profesor_id": s["profesor_id"],
                "dia_semana": s["dia_semana"],
                "periodo_id": s["periodo_id"],
                "tipo_actividad": s["tipo_actividad"],
                "aula": s["aula"],
                "materia": s["materia"],
                "descripcion": s["descripcion"]
            })
            
    # Guardar tramos
    with open(os.path.join(DATA_DIR, "tramos_horarios.json"), "w", encoding="utf-8") as f:
        json.dump(TRAMOS_OFICIALES, f, ensure_ascii=False, indent=2)
        
    # Guardar profesores
    with open(os.path.join(DATA_DIR, "profesores.json"), "w", encoding="utf-8") as f:
        json.dump(teachers_export, f, ensure_ascii=False, indent=2)
        
    # Guardar horarios
    with open(os.path.join(DATA_DIR, "horarios.json"), "w", encoding="utf-8") as f:
        json.dump(horarios_export, f, ensure_ascii=False, indent=2)

    # Actualizar base de datos SQLite directamente
    db_path = os.path.join(DATA_DIR, "sustituciones.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE tramos (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            es_recreo INTEGER NOT NULL DEFAULT 0,
            orden INTEGER NOT NULL DEFAULT 1,
            etapa TEXT NOT NULL DEFAULT 'General'
        );

        CREATE TABLE profesores (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            departamento TEXT NOT NULL DEFAULT '',
            etapa TEXT NOT NULL DEFAULT 'Primaria',
            activo INTEGER NOT NULL DEFAULT 1,
            sustituciones_realizadas INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profesor_id TEXT NOT NULL,
            dia_semana INTEGER NOT NULL,
            periodo_id TEXT NOT NULL,
            tipo_actividad TEXT NOT NULL,
            aula TEXT,
            materia TEXT,
            descripcion TEXT,
            UNIQUE(profesor_id, dia_semana, periodo_id)
        );

        CREATE TABLE sustituciones (
            id TEXT PRIMARY KEY,
            fecha TEXT NOT NULL,
            dia_semana INTEGER NOT NULL,
            periodo_id TEXT NOT NULL,
            periodo_nombre TEXT NOT NULL,
            profesor_ausente_id TEXT NOT NULL,
            profesor_ausente_nombre TEXT NOT NULL,
            profesor_sustituto_id TEXT NOT NULL,
            profesor_sustituto_nombre TEXT NOT NULL,
            profesor_sustituto_telefono TEXT NOT NULL DEFAULT '',
            profesor_sustituto_email TEXT NOT NULL DEFAULT '',
            aula TEXT NOT NULL DEFAULT '',
            curso_grupo TEXT NOT NULL DEFAULT '',
            materia TEXT NOT NULL DEFAULT '',
            observaciones TEXT NOT NULL DEFAULT '',
            estado TEXT NOT NULL DEFAULT 'ASIGNADA',
            creado_en TEXT NOT NULL
        );

        CREATE INDEX idx_horarios_docente ON horarios(profesor_id, dia_semana, periodo_id);
        CREATE INDEX idx_sustituciones_fecha ON sustituciones(fecha, periodo_id);
    """)

    # Insertar tramos
    for t in TRAMOS_OFICIALES:
        cur.execute("""
            INSERT INTO tramos (id, nombre, hora_inicio, hora_fin, es_recreo, orden, etapa)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (t["id"], t["nombre"], t["hora_inicio"], t["hora_fin"], 1 if t["es_recreo"] else 0, t["orden"], t["etapa"]))

    # Insertar profesores
    for p in teachers_export:
        cur.execute("""
            INSERT INTO profesores (id, nombre, telefono, email, departamento, etapa, activo, sustituciones_realizadas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (p["id"], p["nombre"], p["telefono"], p["email"], p["departamento"], p["etapa"], p["activo"], 0))

    # Insertar horarios
    for h in horarios_export:
        cur.execute("""
            INSERT INTO horarios (profesor_id, dia_semana, periodo_id, tipo_actividad, aula, materia, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (h["profesor_id"], h["dia_semana"], h["periodo_id"], h["tipo_actividad"], h["aula"], h["materia"], h["descripcion"]))

    conn.commit()
    conn.close()
    print("✅ Migración completada con éxito. Base de datos SQLite y archivos JSON generados para Escuelas Pías Aluche.")

if __name__ == "__main__":
    migrate()
