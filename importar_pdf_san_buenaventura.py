"""
Script para importar grupos, tramos horarios y clases lectivas de San Buenaventura
desde el PDF subido por el usuario.
"""

import os
import re
import json
import fitz # PyMuPDF
from typing import Dict, List, Any
from models import TimeSlot, Teacher, ScheduleItem, ActivityType
from database import Database

PDF_PATH = "/Users/jose/.gemini/antigravity/brain/4d64205d-411d-4e74-a7da-331f7fe59b94/.user_uploaded/media_1789553887743.pdf"

# Definición de tramos horarios oficiales del colegio según el PDF
TRAMOS_OFICIALES = [
    TimeSlot(id="1H", nombre="1ª Hora", hora_inicio="09:00", hora_fin="09:45", es_recreo=False, orden=1),
    TimeSlot(id="2H", nombre="2ª Hora", hora_inicio="09:45", hora_fin="10:30", es_recreo=False, orden=2),
    TimeSlot(id="REC", nombre="Recreo", hora_inicio="10:30", hora_fin="11:00", es_recreo=True, orden=3),
    TimeSlot(id="3H", nombre="3ª Hora", hora_inicio="11:00", hora_fin="12:00", es_recreo=False, orden=4),
    TimeSlot(id="4H", nombre="4ª Hora", hora_inicio="12:00", hora_fin="13:00", es_recreo=False, orden=5),
]

# Diccionario de materias completo
MATERIAS_NOMBRES = {
    "CING": "Speaking (Conversación en Inglés)",
    "EFI1": "Educación Física",
    "EFI2": "Educación Física",
    "EFI3": "Educación Física",
    "LEN1": "Lengua Castellana y Literatura",
    "LEN2": "Lengua Castellana y Literatura",
    "LEN3": "Lengua Castellana y Literatura",
    "MAT": "Matemáticas",
    "MAT1": "Matemáticas",
    "MAT2": "Matemáticas",
    "MAT3": "Matemáticas",
    "MUS": "Música y danza",
    "NAT1": "Ciencias de la Naturaleza",
    "NAT2": "Ciencias de la Naturaleza",
    "NAT3": "Ciencias de la Naturaleza",
    "PLA": "Educación Plástica y Visual",
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

# 21 Profesores de Primaria extraídos del PDF
PROFESORES_INFO = {
    "AFER0": {"nombre": "Álvaro Fernández Hervás", "depto": "Tutoría / General", "etapa": "Primaria"},
    "AORT0": {"nombre": "Álvaro Paris Ortega Bonilla", "depto": "Tutoría / General", "etapa": "Primaria"},
    "BLEO0": {"nombre": "Beatriz de León Ruiz", "depto": "Tutoría / General", "etapa": "Primaria"},
    "D558":  {"nombre": "David Sagaseta Jiménez", "depto": "Educación Física", "etapa": "Primaria"},
    "FRA0":  {"nombre": "Francisco Javier Félix Fernández", "depto": "Religión", "etapa": "Primaria"},
    "IHID0": {"nombre": "Isabel Hidalgo Castañeda", "depto": "Tutoría / General", "etapa": "Primaria"},
    "IPENA": {"nombre": "Feli Priego", "depto": "Horario de Apoyo", "etapa": "Primaria"},
    "FPRIEGO": {"nombre": "Feli Priego", "depto": "Horario de Apoyo", "etapa": "Primaria"},
    "J326":  {"nombre": "Julia Rodríguez Gutiérrez", "depto": "Tutoría / General", "etapa": "Primaria"},
    "J414":  {"nombre": "Jose Antonio Utrillas Sánchez", "depto": "Tutoría / General", "etapa": "Primaria"},
    "J784":  {"nombre": "Juan Antonio Alfonso Pizarro", "depto": "Educación Física / General", "etapa": "Primaria"},
    "JOS7":  {"nombre": "Casandra Olivares", "depto": "Tutoría / General", "etapa": "Primaria"},
    "L681":  {"nombre": "Lorena Moreno Barrigas", "depto": "Tutoría / General", "etapa": "Primaria"},
    "M654":  {"nombre": "Mª Carmen Ibáñez Abad", "depto": "Inglés", "etapa": "Primaria"},
    "M851":  {"nombre": "Mª Belén Hernando Martín", "depto": "Tutoría / General", "etapa": "Primaria"},
    "MAR1":  {"nombre": "María Pilar Pérez Fernández", "depto": "Tutoría / Robótica", "etapa": "Primaria"},
    "N656":  {"nombre": "Nuria Jarillo García", "depto": "Inglés", "etapa": "Primaria"},
    "OMOL0": {"nombre": "Óscar Manuel Molina Márquez", "depto": "Tutoría / General", "etapa": "Primaria"},
    "P740":  {"nombre": "Pilar Fuentes Saavedra", "depto": "Música", "etapa": "Primaria"},
    "PED4":  {"nombre": "Pedro Zapata Paredes", "depto": "Tutoría / General", "etapa": "Primaria"},
    "PGOM0": {"nombre": "Paula Gomez Buil", "depto": "Tutoría / General", "etapa": "Primaria"},
    "PVEG0": {"nombre": "Pedro Vega Verdeja", "depto": "Tutoría / General", "etapa": "Primaria"},
    "R299":  {"nombre": "Rubén Recio Molina", "depto": "Tutoría / Robótica", "etapa": "Primaria"},
}

def clean_teacher_id(code: str) -> str:
    return code.lower()

def ejecutar_extraccion():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"No se encontró el PDF en {PDF_PATH}")

    doc = fitz.open(PDF_PATH)
    print(f"Abriendo PDF: {len(doc)} páginas encontradas.")

    # 1. Crear objetos de profesores
    teachers_list: List[Teacher] = []
    for code, info in sorted(PROFESORES_INFO.items()):
        t_id = clean_teacher_id(code)
        teachers_list.append(Teacher(
            id=t_id,
            nombre=info["nombre"],
            telefono="",   # Se completará con teléfonos reales si se desea
            email=f"{t_id}@sanbuenaventura.es",
            departamento=info["depto"],
            etapa=info["etapa"],
            activo=True,
            sustituciones_realizadas=0
        ))

    # 2. Extraer horarios de clase (Páginas 1 a 18: 18 grupos de 1º a 6º EP)
    horarios_list: List[ScheduleItem] = []
    grupos_encontrados = []

    for i in range(18):
        page = doc[i]
        text = page.get_text()
        group_m = re.search(r'([1-6]º\s*EP-[ABC])', text)
        if not group_m:
            continue
        grupo = group_m.group(1).replace(" ", "")
        grupos_encontrados.append(grupo)

        tables = page.find_tables()
        for tab in tables:
            extracted = tab.extract()
            # Mapeo de filas del PDF a tramos
            # Fila 1: 09:00 - 09:45 (1H)
            # Fila 2: 09:45 - 10:30 (2H)
            # Fila 4: 11:00 - 12:00 (3H)
            # Fila 5: 12:00 - 13:00 (4H)
            slot_rows = [(1, "1H"), (2, "2H"), (4, "3H"), (5, "4H")]

            for r_idx, slot_id in slot_rows:
                if r_idx >= len(extracted):
                    continue
                row = extracted[r_idx]
                # Columnas 1 a 5 corresponden a Lunes (0) a Viernes (4)
                for col_idx in range(1, 6):
                    dia_semana = col_idx - 1
                    cell_val = row[col_idx].strip()
                    parts = re.split(r'\s*-\s*', cell_val)
                    if len(parts) == 2:
                        subj_code, prof_code = parts[0].strip(), parts[1].strip()
                        materia_nombre = MATERIAS_NOMBRES.get(subj_code, subj_code)
                        t_id = clean_teacher_id(prof_code)

                        horarios_list.append(ScheduleItem(
                            profesor_id=t_id,
                            dia_semana=dia_semana,
                            periodo_id=slot_id,
                            tipo_actividad=ActivityType.LECTIVA,
                            aula=grupo,
                            materia=f"{materia_nombre} ({subj_code})",
                            descripcion=f"Clase de {materia_nombre} en {grupo}"
                        ))

    print(f"Extracción completada:")
    print(f"- Profesores: {len(teachers_list)}")
    print(f"- Tramos horarios: {len(TRAMOS_OFICIALES)}")
    print(f"- Grupos procesados ({len(grupos_encontrados)}): {', '.join(grupos_encontrados)}")
    print(f"- Total de sesiones lectivas registradas: {len(horarios_list)}")

    # Guardar en base de datos
    db = Database()
    db.save_time_slots(TRAMOS_OFICIALES)
    db.save_teachers(teachers_list)
    db.save_schedules(horarios_list)
    print("✓ Base de datos actualizada con éxito.")

if __name__ == "__main__":
    ejecutar_extraccion()
