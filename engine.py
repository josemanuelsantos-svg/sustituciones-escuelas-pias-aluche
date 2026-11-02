"""
Motor inteligente de recomendación y asignación de sustituciones escolares.
"""

from typing import List, Dict, Any, Optional, Tuple
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
        ordenados según criterios pedagógicos, de guardia y equidad de carga.
        """
        # Determinar día de la semana (0=Lunes, 4=Viernes)
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        dia_semana = fecha_dt.weekday()
        if dia_semana >= 5:
            raise ValueError("La fecha seleccionada corresponde a fin de semana (sin actividad lectiva).")

        profesor_ausente = self.db.get_teacher(profesor_ausente_id)
        if not profesor_ausente:
            raise ValueError(f"No se encontró al profesor ausente con id '{profesor_ausente_id}'")

        slot = self.db.get_time_slot(periodo_id)
        if not slot:
            raise ValueError(f"No se encontró el tramo horario con id '{periodo_id}'")

        # Obtener todas las sustituciones existentes para esa fecha y hora
        sustituciones_del_dia = [
            s for s in self.db.get_substitutions()
            if s.fecha == fecha_str and s.periodo_id == periodo_id and s.estado != "CANCELADA"
        ]
        profesores_ya_sustituyendo = {s.profesor_sustituto_id for s in sustituciones_del_dia}
        profesores_ya_ausentes = {s.profesor_ausente_id for s in sustituciones_del_dia}
        profesores_ya_ausentes.add(profesor_ausente_id)

        # Filtrar candidatos según la etapa educativa (Infantil o Primaria)
        es_infantil = bool(profesor_ausente and profesor_ausente.etapa and profesor_ausente.etapa.lower() == "infantil")

        if es_infantil:
            infantil_profesores = self.db.get_teachers(active_only=True, etapa="Infantil")
            # En Infantil, como último recurso (4º nivel) pueden sustituir Dani Asenjo o María Vázquez
            extra_ids = ["dasenjo", "mvazquez"]
            extra_profesores = [t for t in self.db.get_teachers(active_only=True) if t.id.lower() in extra_ids]
            seen_ids = {t.id for t in infantil_profesores}
            todos_los_profesores = list(infantil_profesores) + [t for t in extra_profesores if t.id not in seen_ids]
        else:
            todos_los_profesores = self.db.get_teachers(active_only=True, etapa="Primaria")

        candidatos_evaluados: List[SubstitutionCandidate] = []
        no_disponibles: List[Dict[str, str]] = []

        for docente in todos_los_profesores:
            # 1. No puede sustituirse a sí mismo ni a quien ya esté ausente
            if docente.id in profesores_ya_ausentes:
                continue

            # 2. No puede tener ya otra sustitución en ese tramo
            if docente.id in profesores_ya_sustituyendo:
                no_disponibles.append({
                    "profesor_id": docente.id,
                    "profesor_nombre": docente.nombre,
                    "motivo": "Ya tiene asignada otra sustitución en este mismo tramo horario"
                })
                continue

            # 3. Consultar su horario en ese día y período
            horario_slot = self.db.get_slot_activity_for_teacher(docente.id, dia_semana, periodo_id)

            if not horario_slot:
                # Si no tiene clase registrada en este tramo, significa que tiene un HUECO LIBRE.
                # Según la norma del centro: "el sustituto siempre debe ser una persona que tuviera alguna hora libre... que tenían algún hueco"
                tipo_actividad = ActivityType.DISPONIBLE
                detalle_actividad = "Hueco libre en su horario"
                es_hueco_libre = True
            else:
                tipo_actividad = horario_slot.tipo_actividad
                detalle_actividad = horario_slot.materia or horario_slot.descripcion or tipo_actividad
                es_hueco_libre = False

            # 4. Filtrar según tipo de actividad: debe tener hora libre / hueco (sin clase lectiva)
            if tipo_actividad == ActivityType.LECTIVA:
                no_disponibles.append({
                    "profesor_id": docente.id,
                    "profesor_nombre": docente.nombre,
                    "motivo": f"Clase lectiva ({detalle_actividad})"
                })
                continue
            
            if tipo_actividad == ActivityType.NO_DISPONIBLE:
                no_disponibles.append({
                    "profesor_id": docente.id,
                    "profesor_nombre": docente.nombre,
                    "motivo": f"No disponible para sustituir ({detalle_actividad})"
                })
                continue

            if tipo_actividad == ActivityType.GUARDIA_RECREO and not slot.es_recreo:
                no_disponibles.append({
                    "profesor_id": docente.id,
                    "profesor_nombre": docente.nombre,
                    "motivo": "Guardia de recreo en hora lectiva ordinaria"
                })
                continue

            # 5. Si pasa el filtro, es un candidato elegible con hora libre / hueco.
            puntuacion = 0.0
            motivos = []
            pid = docente.id.lower()

            if es_infantil:
                # ============================================================
                # APLICACIÓN INTERNA DEL ORDEN OFICIAL (INFANTIL)
                # 1º Cristina Duerto o Paula Lozano
                # 2º Cualquier profesora de Infantil con hueco
                # 3º Susana López y Elena Díaz
                # 4º Por último, Dani Asenjo o María Vázquez
                # ============================================================
                if pid in ["cdue1", "cduerto"]:
                    puntuacion = 1000.0
                    motivos.append("Docente disponible")
                elif pid in ["m111", "plozano"]:
                    puntuacion = 999.0
                    motivos.append("Docente disponible")
                elif pid in ["sus8", "e587"]:
                    puntuacion = 500.0
                    motivos.append("Docente disponible")
                elif pid in ["dasenjo", "mvazquez"]:
                    puntuacion = 200.0
                    motivos.append("Docente de apoyo disponible")
                else:
                    puntuacion = 800.0
                    motivos.append("Docente disponible")
                
                # Desempate equitativo por carga acumulada
                puntuacion -= (docente.sustituciones_realizadas * 2.0)
            else:
                # ============================================================
                # APLICACIÓN INTERNA DEL ORDEN OFICIAL (PRIMARIA)
                # 1º Casandra Olivares (primera línea) y Feli Priego
                # 2º Carmen, Pilar F., Pilar P., Cristina D., Paula G.
                # 3º Bea y Rubén
                # 4º Jose Antonio
                # 5º Belén
                # 6º Dani y María
                # ============================================================
                if pid in ["jos7", "colivares"]:
                    puntuacion = 1000.0
                    motivos.append("Docente disponible")
                elif pid in ["ipena", "fpriego", "feli", "felicitacion_priego", "felicitacionpriego"]:
                    puntuacion = 999.0
                    motivos.append("Docente disponible")
                elif pid == "m654":
                    puntuacion = 900.0
                    motivos.append("Docente disponible")
                elif pid == "p740":
                    puntuacion = 850.0
                    motivos.append("Docente disponible")
                elif pid == "mar1":
                    puntuacion = 800.0
                    motivos.append("Docente disponible")
                elif pid == "cduerto":
                    puntuacion = 750.0
                    motivos.append("Docente disponible")
                elif pid == "pgonzalez":
                    puntuacion = 700.0
                    motivos.append("Docente disponible")
                elif pid in ["bleo0", "r299"]:
                    puntuacion = 500.0
                    motivos.append("Docente disponible")
                elif pid in ["j414"]:
                    puntuacion = 300.0
                    motivos.append("Docente disponible")
                elif pid == "m851":
                    puntuacion = 200.0
                    motivos.append("Docente disponible")
                elif pid in ["dasenjo", "mvazquez"]:
                    puntuacion = 100.0
                    motivos.append("Docente de apoyo disponible")
                else:
                    puntuacion = 600.0
                    motivos.append("Docente disponible")

            # Detalle del tipo de disponibilidad
            if es_hueco_libre:
                motivos.append("Hueco libre en horario")
            elif tipo_actividad == ActivityType.GUARDIA_AULA:
                motivos.append("En Guardia de Aula")
            elif tipo_actividad == ActivityType.DISPONIBLE:
                motivos.append("Horario de Apoyo / Libre")

            # Afinidad de departamento
            coincide_depto = False
            if docente.departamento and profesor_ausente.departamento and \
               docente.departamento.strip().lower() == profesor_ausente.departamento.strip().lower():
                puntuacion += 15.0
                coincide_depto = True
                motivos.append(f"Mismo depto ({docente.departamento})")

            # Afinidad de etapa educativa
            coincide_etapa = False
            if docente.etapa and profesor_ausente.etapa and \
               docente.etapa.strip().lower() == profesor_ausente.etapa.strip().lower():
                puntuacion += 10.0
                coincide_etapa = True
                motivos.append(f"Misma etapa ({docente.etapa})")

            # Información de carga (no afecta al orden de prelación diario estricto)
            if docente.sustituciones_realizadas == 0:
                motivos.append("0 sustituciones acumuladas")
            else:
                motivos.append(f"{docente.sustituciones_realizadas} sustitución(es) acumuladas")

            motivo_completo = " · ".join(motivos)

            candidatos_evaluados.append(SubstitutionCandidate(
                profesor=docente,
                tipo_disponibilidad=tipo_actividad,
                puntuacion=puntuacion,
                motivo=motivo_completo,
                es_recomendado=False,
                coincide_departamento=coincide_depto,
                coincide_etapa=coincide_etapa
            ))

        # Ordenar candidatos de mayor a menor puntuación
        candidatos_evaluados.sort(key=lambda c: c.puntuacion, reverse=True)

        # Marcar el mejor candidato como recomendado
        if candidatos_evaluados:
            candidatos_evaluados[0].es_recomendado = True

        return {
            "fecha": fecha_str,
            "periodo": slot.to_dict(),
            "profesor_ausente": profesor_ausente.to_dict(),
            "total_candidatos": len(candidatos_evaluados),
            "recomendado": candidatos_evaluados[0].to_dict() if candidatos_evaluados else None,
            "candidatos": [c.to_dict() for c in candidatos_evaluados],
            "no_disponibles": no_disponibles
        }
