"""
Motor inteligente de recomendación y asignación de sustituciones escolares.
Adaptado para Colegio Nuestra Señora de las Escuelas Pías (Aluche) - Gestión: Vero.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from models import (
    Teacher,
    TimeSlot,
    ScheduleItem,
    SubstitutionCandidate,
    SubstitutionRecord,
    ActivityType
)
from database import Database

class SubstitutionEngine:
    def __init__(self, db: Database):
        self.db = db

    def find_candidates(
        self,
        fecha_str: str,
        periodo_id: str,
        profesor_ausente_id: str,
        materia: Optional[str] = None,
        aula: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Encuentra y clasifica a todos los candidatos disponibles para cubrir una ausencia,
        siguiendo escrupulosamente los criterios del Colegio Escuelas Pías Aluche:
        1. Las horas para sustituir sólo son las de clase (las demás no se cubren).
        2. El orden de disponibilidad: 1º Guardia, 2º Reuniones, 3º Apoyos.
        3. Afinidad de etapa: Primaria sustituye a Primaria e Infantil a Infantil si es posible.
        4. Equidad acumulada: a igualdad de rango, menos sustituciones primero.
        """
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        dia_semana = fecha_dt.weekday()
        if dia_semana >= 5:
            raise ValueError("La fecha seleccionada corresponde a fin de semana (sin actividad escolar).")

        profesor_ausente = self.db.get_teacher(profesor_ausente_id)
        if not profesor_ausente:
            raise ValueError(f"No se encontró al profesor ausente con id '{profesor_ausente_id}'")

        slot = self.db.get_time_slot(periodo_id)
        if not slot:
            raise ValueError(f"No se encontró el tramo horario con id '{periodo_id}'")

        # 1. Comprobar qué actividad tenía el profesor ausente a esa hora
        horario_ausente = self.db.get_slot_activity_for_teacher(profesor_ausente_id, dia_semana, periodo_id)
        
        es_hora_lectiva = False
        materia_detectada = materia or ""
        curso_detectado = aula or ""
        tipo_actividad_ausente = "LIBRE"
        descripcion_ausente = "Hueco no lectivo"

        if horario_ausente:
            tipo_actividad_ausente = horario_ausente.tipo_actividad
            descripcion_ausente = horario_ausente.descripcion or horario_ausente.tipo_actividad
            if not materia_detectada and horario_ausente.materia:
                materia_detectada = horario_ausente.materia
            if not curso_detectado and (horario_ausente.curso_grupo or horario_ausente.aula):
                curso_detectado = horario_ausente.curso_grupo or horario_ausente.aula

            if tipo_actividad_ausente == ActivityType.LECTIVA:
                es_hora_lectiva = True
            else:
                es_hora_lectiva = False
        else:
            # Si no hay registro en ese tramo
            es_hora_lectiva = False

        # Sustituciones ya asignadas en esa fecha y tramo
        sustituciones_del_dia = [
            s for s in self.db.get_substitutions()
            if s.fecha == fecha_str and s.periodo_id == periodo_id and s.estado != "CANCELADA"
        ]
        profesores_ya_sustituyendo = {s.profesor_sustituto_id for s in sustituciones_del_dia}
        profesores_ya_ausentes = {s.profesor_ausente_id for s in sustituciones_del_dia}
        profesores_ya_ausentes.add(profesor_ausente_id)

        # Obtener todos los docentes activos del colegio
        todos_los_profesores = self.db.get_teachers(active_only=True)

        candidatos_evaluados: List[SubstitutionCandidate] = []
        no_disponibles: List[Dict[str, str]] = []

        etapa_ausente = (profesor_ausente.etapa or "Primaria").strip().lower()

        for docente in todos_los_profesores:
            # Descartar si es el ausente o ya está ausente hoy a esta hora
            if docente.id in profesores_ya_ausentes:
                continue

            # Descartar si ya tiene asignada otra sustitución en este mismo tramo
            if docente.id in profesores_ya_sustituyendo:
                no_disponibles.append({
                    "profesor_id": docente.id,
                    "profesor_nombre": docente.nombre,
                    "motivo": "Ya tiene asignada otra sustitución en esta misma sesión"
                })
                continue

            # Consultar actividad del docente en este día y tramo
            horario_slot = self.db.get_slot_activity_for_teacher(docente.id, dia_semana, periodo_id)

            if not horario_slot:
                tipo_actividad = ActivityType.REUNION
                detalle_actividad = "Hueco no lectivo libre"
            else:
                tipo_actividad = horario_slot.tipo_actividad
                detalle_actividad = horario_slot.materia or horario_slot.descripcion or tipo_actividad

            # Si el candidato tiene CLASE LECTIVA con alumnos, NO puede sustituir
            if tipo_actividad == ActivityType.LECTIVA:
                no_disponibles.append({
                    "profesor_id": docente.id,
                    "profesor_nombre": docente.nombre,
                    "motivo": f"Clase lectiva ({detalle_actividad})"
                })
                continue

            # Categorizar según el orden de prelación oficial de Escuelas Pías Aluche:
            # 1º Guardia, 2º Reuniones / No lectivas, 3º Apoyos
            tipo_act_upper = str(tipo_actividad).upper()
            detalle_lower = str(detalle_actividad).lower()

            if "GUARDIA" in tipo_act_upper or "guardia" in detalle_lower:
                categoria_nombre = "1º Guardia"
                base_score = 3000.0
                tipo_disp = "GUARDIA"
                motivo_tipo = "Hora de Guardia oficial"
            elif "APOYO" in tipo_act_upper or "apoyo" in detalle_lower:
                categoria_nombre = "3º Apoyo"
                base_score = 1000.0
                tipo_disp = "APOYO"
                motivo_tipo = f"Hora de Apoyo ({detalle_actividad})"
            else:
                # Reuniones, coordinación, proyectos, COCOPE, EDE, presencia o libre
                categoria_nombre = "2º Reunión / No lectiva"
                base_score = 2000.0
                tipo_disp = "REUNION"
                motivo_tipo = f"Reunión / Libre ({detalle_actividad})"

            # Afinidad de etapa: Primaria a Primaria, Infantil a Infantil
            etapa_docente = (docente.etapa or "Primaria").strip().lower()
            misma_etapa = (etapa_docente == etapa_ausente) or ("mixta" in etapa_docente)

            if misma_etapa:
                # Priorizar docentes de la misma etapa
                etapa_bonus = 3000.0
                motivo_etapa = f"Misma etapa ({docente.etapa})"
            else:
                etapa_bonus = 0.0
                motivo_etapa = f"Otra etapa ({docente.etapa})"

            # Equidad: restar penalización leve por cada sustitución acumulada para romper empates
            penalizacion_carga = docente.sustituciones_realizadas * 2.0

            puntuacion_total = base_score + etapa_bonus - penalizacion_carga

            # Construir motivos
            motivos = [
                f"{categoria_nombre} ({motivo_tipo})",
                motivo_etapa,
                f"{docente.sustituciones_realizadas} sustituciones previas"
            ]

            candidatos_evaluados.append(SubstitutionCandidate(
                profesor=docente,
                tipo_disponibilidad=tipo_disp,
                prioridad_categoria=categoria_nombre,
                puntuacion=puntuacion_total,
                motivo=" · ".join(motivos),
                es_recomendado=False,
                coincide_departamento=misma_etapa,
                coincide_etapa=misma_etapa
            ))

        # Ordenar candidatos de mayor a menor puntuación
        candidatos_evaluados.sort(key=lambda c: c.puntuacion, reverse=True)

        # El primero es el recomendado oficial
        if candidatos_evaluados:
            candidatos_evaluados[0].es_recomendado = True

        mensaje_criterio = ""
        if not es_hora_lectiva:
            mensaje_criterio = f"Aviso de criterio: El profesor ausente tiene '{descripcion_ausente}' en esta hora. Según la norma del centro, las horas que no son de clase regular con alumnos no se cubren."

        return {
            "fecha": fecha_str,
            "periodo": slot.to_dict(),
            "profesor_ausente": profesor_ausente.to_dict(),
            "es_hora_lectiva": es_hora_lectiva,
            "materia_detectada": materia_detectada,
            "curso_detectado": curso_detectado,
            "actividad_ausente": descripcion_ausente,
            "mensaje_criterio": mensaje_criterio,
            "total_candidatos": len(candidatos_evaluados),
            "recomendado": candidatos_evaluados[0].to_dict() if candidatos_evaluados else None,
            "candidatos": [c.to_dict() for c in candidatos_evaluados],
            "no_disponibles": no_disponibles
        }
