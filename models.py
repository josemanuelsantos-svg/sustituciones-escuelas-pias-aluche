"""
Modelos de datos y estructuras para el Sistema de Sustituciones Escolares.
Colegio Nuestra Señora de las Escuelas Pías (Aluche) - Gestión: Vero.
"""

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time

class ActivityType(str, Enum):
    LECTIVA = "LECTIVA"                           # Clase regular con alumnos (sustituible si falta; no puede sustituir)
    GUARDIA = "GUARDIA"                           # Guardia oficial (1ª Prioridad para sustituir)
    GUARDIA_AULA = "GUARDIA_AULA"                 # Compatibilidad
    GUARDIA_RECREO = "GUARDIA_RECREO"             # Recreo
    REUNION = "REUNION"                           # Reuniones, coordinación, EDE, COCOPE, proyectos (2ª Prioridad)
    APOYO = "APOYO"                               # Horas de apoyo lectivo o compensatoria (3ª Prioridad)
    DISPONIBLE = "DISPONIBLE"                     # Hueco libre computable
    NO_DISPONIBLE = "NO_DISPONIBLE"               # No utilizable

class StageType(str, Enum):
    INFANTIL = "Infantil"
    PRIMARIA = "Primaria"
    GENERAL = "General"

@dataclass
class TimeSlot:
    id: str                                       # ej. "1H", "2H", "REC", "3H", "MED", "4H", "5H"
    nombre: str                                   # ej. "1ª Hora (09:05 - 10:05)"
    hora_inicio: str                              # ej. "09:05"
    hora_fin: str                                 # ej. "10:05"
    es_recreo: bool = False                       # True para Recreo y Comedor
    orden: int = 1
    etapa: str = "General"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Teacher:
    id: str                                       # ej. "sara_calvo_garcia"
    nombre: str                                   # ej. "Sara Calvo García"
    telefono: str = ""
    email: str = ""
    departamento: str = "Primaria"
    etapa: str = "Primaria"                       # "Primaria" o "Infantil"
    activo: bool = True
    sustituciones_realizadas: int = 0             # Contador acumulado para equidad

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ScheduleItem:
    profesor_id: str
    dia_semana: int                               # 0=Lunes .. 4=Viernes
    periodo_id: str                               # Relacionado con TimeSlot.id
    tipo_actividad: str                           # ActivityType (LECTIVA, GUARDIA, REUNION, APOYO)
    aula: Optional[str] = None                    # ej. "6º EP-C", "3 años-A"
    materia: Optional[str] = None                 # ej. "Matemáticas", "Lengua Castellana y Literatura"
    curso_grupo: Optional[str] = None             # ej. "6º EP-C"
    descripcion: Optional[str] = None             # ej. "Guardia", "COCOPE", "Apoyo Compensatoria"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SubstitutionCandidate:
    profesor: Teacher
    tipo_disponibilidad: str                      # GUARDIA, REUNION, APOYO
    prioridad_categoria: str                      # "1º Guardia", "2º Reunión/Libre", "3º Apoyo"
    puntuacion: float                             # Puntuación de prelación
    motivo: str                                   # Explicación clara
    es_recomendado: bool = False
    coincide_departamento: bool = False
    coincide_etapa: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['profesor'] = self.profesor.to_dict()
        return data

@dataclass
class SubstitutionRecord:
    id: str
    fecha: str                                    # YYYY-MM-DD
    dia_semana: int                               # 0 a 4
    periodo_id: str
    periodo_nombre: str
    profesor_ausente_id: str
    profesor_ausente_nombre: str
    profesor_sustituto_id: str
    profesor_sustituto_nombre: str
    profesor_sustituto_telefono: str = ""
    profesor_sustituto_email: str = ""
    aula: str = ""                                # Clase / Aula (ej. "6º EP-C")
    curso_grupo: str = ""                         # Clase / Grupo
    materia: str = ""                             # Asignatura (ej. "Matemáticas")
    observaciones: str = ""                       # Qué deben hacer en su hora
    que_hacer: str = ""                           # Qué deben hacer (alias directo)
    estado: str = "ASIGNADA"                      # ASIGNADA, CONFIRMADA, CANCELADA
    creado_en: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data.get("que_hacer"):
            data["que_hacer"] = data.get("observaciones", "")
        return data
