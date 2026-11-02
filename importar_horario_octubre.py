"""
Script para importar el horario oficial de Octubre (jornada ordinaria completa mañana y tarde)
desde el PDF oficial de 39 páginas de San Buenaventura.
"""

import os
import re
import json
import fitz # PyMuPDF
from models import TimeSlot, ScheduleItem, ActivityType
from database import Database

PDF_PATH = "/Users/jose/.gemini/antigravity/brain/4d64205d-411d-4e74-a7da-331f7fe59b94/.user_uploaded/media_1790798838971.pdf"

# 1. Definición oficial de los tramos horarios de Octubre
TRAMOS_OCTUBRE = [
    TimeSlot(id="1H", nombre="1ª Hora", hora_inicio="09:00", hora_fin="09:45", es_recreo=False, orden=1),
    TimeSlot(id="2H", nombre="2ª Hora", hora_inicio="09:45", hora_fin="10:30", es_recreo=False, orden=2),
    TimeSlot(id="REC", nombre="Recreo", hora_inicio="10:30", hora_fin="11:00", es_recreo=True, orden=3),
    TimeSlot(id="3H", nombre="3ª Hora", hora_inicio="11:00", hora_fin="11:45", es_recreo=False, orden=4),
    TimeSlot(id="4H", nombre="4ª Hora", hora_inicio="11:45", hora_fin="12:30", es_recreo=False, orden=5),
    TimeSlot(id="5H", nombre="5ª Hora (Tarde)", hora_inicio="14:15", hora_fin="15:15", es_recreo=False, orden=6),
    TimeSlot(id="6H", nombre="6ª Hora (Tarde)", hora_inicio="15:15", hora_fin="16:15", es_recreo=False, orden=7),
]

# 2. Diccionario de materias completo
MATERIAS_DICT = {
    "CING": "Speaking (Conversación en Inglés)",
    "EFI1": "Educación Física",
    "EFI2": "Educación Física",
    "EFI3": "Educación Física",
    "LEN1": "Lengua Castellana y Literatura",
    "LEN2": "Lengua Castellana y Literatura",
    "LEN3": "Lengua Castellana y Literatura",
    "MAT":  "Matemáticas",
    "MAT1": "Matemáticas",
    "MAT2": "Matemáticas",
    "MAT3": "Matemáticas",
    "MUS":  "Música y danza",
    "NAT1": "Ciencias de la Naturaleza",
    "NAT2": "Ciencias de la Naturaleza",
    "NAT3": "Ciencias de la Naturaleza",
    "PLA":  "Educación Plastica y Visual",
    "PRO1": "Programación y robótica",
    "PRO2": "Programación y robótica",
    "PRO3": "Programación y robótica",
    "REL1": "Religión",
    "REL2": "Religión",
    "REL3": "Religión",
    "SOC1": "Ciencias Sociales",
    "SOC2": "Ciencias Sociales",
    "SOC3": "Ciencias Sociales",
    "VAL3": "Educación en Valores Cívicos y Éticos"
}

TIME_MAP = {
    "09:00": "1H",
    "09:45": "2H",
    "10:30": "REC",
    "11:00": "3H",
    "11:45": "4H",
    "14:15": "5H",
    "15:15": "6H"
}

TEACHER_NAME_MAP = {
    "ÁLVARO FERNÁNDEZ HERVÁS": "afer0",
    "ÁLVARO PARIS ORTEGA BONILLA": "aort0",
    "BEATRIZ DE LEÓN RUIZ": "bleo0",
    "DAVID SAGASETA JIMÉNEZ": "d558",
    "FRANCISCO JAVIER FÉLIX FERNÁNDEZ": "fra0",
    "ISABEL HIDALGO CASTAÑEDA": "ihid0",
    "ISABEL PEÑA ESCUDERO": "ipena",
    "FELI PRIEGO": "ipena",
    "FELI PRIEGO PERETE": "ipena",
    "FELICITACIÓN PRIEGO": "ipena",
    "FELICITACION PRIEGO": "ipena",
    "JOSE ANTONIO UTRILLAS SÁNCHEZ": "j414",
    "JOSÉ MANUEL SANTOS ALEJANO": "jos7",
    "CASANDRA OLIVARES": "jos7",
    "JUAN ANTONIO ALFONSO PIZARRO": "j784",
    "JULIA RODRÍGUEZ GUTIÉRREZ": "j326",
    "LORENA MORENO BARRIGAS": "l681",
    "Mª BELÉN HERNANDO MARTÍN": "m851",
    "Mª CARMEN IBÁÑEZ ABAD": "m654",
    "MARÍA PILAR PÉREZ FERNÁNDEZ": "mar1",
    "NURIA JARILLO GARCÍA": "n656",
    "ÓSCAR MANUEL MOLINA MÁRQUEZ": "omol0",
    "PAULA GOMEZ BUIL": "pgom0",
    "PEDRO VEGA VERDEJA": "pveg0",
    "PEDRO ZAPATA PAREDES": "ped4",
    "PILAR FUENTES SAAVEDRA": "p740",
    "RUBÉN RECIO MOLINA": "r299"
}

def get_slot_id(time_str: str):
    for k, v in TIME_MAP.items():
        if k in time_str:
            return v
    return None

def ejecutar_importacion():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"No se encuentra el archivo PDF en {PDF_PATH}")

    doc = fitz.open(PDF_PATH)
    print(f"Abierto PDF de {len(doc)} páginas...")

    db = Database()

    # 1. Guardar los nuevos tramos horarios de Octubre
    db.save_time_slots(TRAMOS_OCTUBRE)
    print(f"✅ Tramos horarios de Octubre actualizados ({len(TRAMOS_OCTUBRE)} tramos: 1H a 6H + Recreo).")

    schedules: List[ScheduleItem] = []

    # 2. Extraer clases de los 18 grupos (Páginas 1 a 18)
    for p_idx in range(18):
        page = doc[p_idx]
        text = page.get_text("text")
        m_grp = re.search(r'([1-6]º\s*EP-[ABC])', text)
        group_name = m_grp.group(1).replace(" ", "") if m_grp else f"Grupo_{p_idx+1}"

        tabs = page.find_tables().tables
        if not tabs:
            continue

        rows = tabs[0].extract()
        for row in rows[1:]:
            time_header = row[0].replace("\n", " ")
            slot_id = get_slot_id(time_header)
            if not slot_id or slot_id == "REC":
                continue

            for dia_idx, cell in enumerate(row[1:]):  # 0=Lunes, 4=Viernes
                c_text = (cell or "").strip()
                if not c_text or c_text.lower() == "comedor":
                    continue

                parts = c_text.split("-")
                if len(parts) == 2:
                    mat_code = parts[0].strip()
                    prof_code = parts[1].strip().lower()
                    materia_nombre = MATERIAS_DICT.get(mat_code, mat_code)

                    schedules.append(ScheduleItem(
                        profesor_id=prof_code,
                        dia_semana=dia_idx,
                        periodo_id=slot_id,
                        tipo_actividad=ActivityType.LECTIVA,
                        aula=group_name,
                        materia=materia_nombre,
                        descripcion=f"{materia_nombre} en {group_name}"
                    ))

    print(f"✅ Extraídas {len(schedules)} clases lectivas de grupos.")
    print(f"📊 Total clases lectivas en horario de Octubre: {len(schedules)}")

    # 3. Guardar en SQLite y JSON (solo clases lectivas, a la espera del cuadrante de sustituciones)
    db.save_schedules(schedules)
    print("🚀 Horario de clases lectivas de Octubre guardado con éxito en SQLite y JSON.")

if __name__ == "__main__":
    ejecutar_importacion()
