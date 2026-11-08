"""
Servidor Web Flask y API REST para el Sistema de Sustituciones Escolares.
Colegio Nuestra Señora de las Escuelas Pías (Aluche) - Coordinación: Vero.
"""

import os
import uuid
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
from models import Teacher, TimeSlot, ScheduleItem, SubstitutionRecord, ActivityType
from database import Database
from engine import SubstitutionEngine
from docx_service import generate_weekly_docx

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_AS_ASCII"] = False

db = Database()
if len(db.get_teachers()) == 0:
    try:
        from importar_escuelas_pias import importar_datos
        importar_datos()
    except Exception as e:
        print(f"Aviso al inicializar datos de Escuelas Pías: {e}")
engine = SubstitutionEngine(db)

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon.ico", mimetype="image/vnd.microsoft.icon")

@app.route("/")
def index():
    """Portal principal de gestión de sustituciones de Escuelas Pías Aluche para Vero."""
    return render_template("index.html")

@app.route("/api/initial-data", methods=["GET"])
def get_initial_data():
    """Devuelve los datos maestros para inicializar la interfaz rápidamente, filtrable por etapa."""
    etapa = request.args.get("etapa", "Todos")
    
    if etapa and etapa not in ["Todos", "General", ""]:
        teachers = db.get_teachers(etapa=etapa)
    else:
        teachers = db.get_teachers()
        
    slots = db.get_time_slots()
    all_subs = db.get_substitutions()
    
    # Estadísticas de equidad
    stats = []
    for t in db.get_teachers():
        stats.append({
            "id": t.id,
            "nombre": t.nombre,
            "departamento": t.departamento,
            "etapa": t.etapa,
            "sustituciones": t.sustituciones_realizadas
        })
    stats.sort(key=lambda x: x["sustituciones"], reverse=True)

    today_str = date.today().isoformat()

    return jsonify({
        "centro": "Colegio Nuestra Señora de las Escuelas Pías (Aluche)",
        "coordinadora": "Vero",
        "hoy": today_str,
        "profesores": [t.to_dict() for t in teachers],
        "todos_los_profesores": [t.to_dict() for t in db.get_teachers()],
        "tramos": [s.to_dict() for s in slots],
        "ultimas_sustituciones": [s.to_dict() for s in all_subs],
        "estadisticas": stats,
        "tipos_actividad": [e.value for e in ActivityType]
    })

@app.route("/api/profesores", methods=["GET"])
def get_profesores():
    etapa = request.args.get("etapa")
    return jsonify([t.to_dict() for t in db.get_teachers(etapa=etapa)])

@app.route("/api/tramos", methods=["GET"])
def get_tramos():
    return jsonify([s.to_dict() for s in db.get_time_slots()])

@app.route("/api/horarios", methods=["GET"])
def get_horarios():
    profesor_id = request.args.get("profesor_id")
    etapa = request.args.get("etapa")
    if profesor_id:
        items = db.get_schedule_for_teacher(profesor_id)
    else:
        items = db.get_schedules(etapa=etapa)
    return jsonify([item.to_dict() for item in items])

@app.route("/api/disponibilidad-tramo", methods=["GET"])
def get_disponibilidad_tramo():
    """Devuelve el mapa de disponibilidad de todo el claustro en un día y hora concretos."""
    dia_semana = int(request.args.get("dia_semana", 0))
    periodo_id = request.args.get("periodo_id", "1H")

    teachers = db.get_teachers(active_only=True)
    guardias = []
    reuniones = []
    apoyos = []
    en_clase = []

    for t in teachers:
        slot = db.get_slot_activity_for_teacher(t.id, dia_semana, periodo_id)
        info = {
            "id": t.id,
            "nombre": t.nombre,
            "etapa": t.etapa,
            "departamento": t.departamento,
            "sustituciones_realizadas": t.sustituciones_realizadas,
            "detalle": slot.descripcion if slot else "Hueco libre",
            "materia": slot.materia if slot else "",
            "aula": slot.aula if slot else ""
        }
        if not slot:
            reuniones.append(info)
        elif slot.tipo_actividad == ActivityType.LECTIVA:
            en_clase.append(info)
        elif slot.tipo_actividad == ActivityType.GUARDIA:
            guardias.append(info)
        elif slot.tipo_actividad == ActivityType.APOYO:
            apoyos.append(info)
        else:
            reuniones.append(info)

    return jsonify({
        "dia_semana": dia_semana,
        "periodo_id": periodo_id,
        "guardias": guardias,
        "reuniones": reuniones,
        "apoyos": apoyos,
        "en_clase": en_clase
    })

@app.route("/api/actividad-docente", methods=["GET"])
def get_actividad_docente():
    """Devuelve la clase/actividad programada para un docente en un día y tramo concreto."""
    profesor_id = request.args.get("profesor_id")
    periodo_id = request.args.get("periodo_id")
    fecha_str = request.args.get("fecha")
    dia_str = request.args.get("dia_semana")

    if not profesor_id or not periodo_id:
        return jsonify({"encontrado": False}), 400

    if fecha_str:
        try:
            dia_semana = datetime.strptime(fecha_str, "%Y-%m-%d").weekday()
        except Exception:
            dia_semana = 0
    elif dia_str is not None:
        dia_semana = int(dia_str)
    else:
        dia_semana = 0

    item = db.get_slot_activity_for_teacher(profesor_id, dia_semana, periodo_id)
    if item:
        es_clase = (item.tipo_actividad == ActivityType.LECTIVA)
        return jsonify({
            "encontrado": True,
            "aula": item.aula or "",
            "curso_grupo": item.curso_grupo or item.aula or "",
            "materia": item.materia or "",
            "tipo_actividad": item.tipo_actividad,
            "descripcion": item.descripcion or "",
            "es_clase": es_clase,
            "sustituible": es_clase
        })
    return jsonify({"encontrado": False, "es_clase": False, "sustituible": False})

@app.route("/api/buscar-sustitutos", methods=["POST"])
def search_substitutes():
    """Busca y clasifica los candidatos disponibles para cubrir una ausencia específica."""
    data = request.json or {}
    fecha = data.get("fecha")
    periodo_id = data.get("periodo_id")
    profesor_ausente_id = data.get("profesor_ausente_id")
    materia = data.get("materia")
    aula = data.get("aula")

    if not fecha or not periodo_id or not profesor_ausente_id:
        return jsonify({"error": "fecha, periodo_id y profesor_ausente_id son obligatorios"}), 400

    try:
        resultado = engine.find_candidates(
            fecha_str=fecha,
            periodo_id=periodo_id,
            profesor_ausente_id=profesor_ausente_id,
            materia=materia,
            aula=aula
        )
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/buscar-sustitutos-multiple", methods=["POST"])
def search_substitutes_multiple():
    """
    Evalúa múltiples tramos horarios de un día para un profesor ausente,
    aplicando la regla de que solo se cubren horas de clase (no guardias ni reuniones).
    """
    data = request.json or {}
    fecha = data.get("fecha")
    periodos = data.get("periodos", [])
    profesor_ausente_id = data.get("profesor_ausente_id")
    overrides = data.get("overrides", {})

    if not fecha or not periodos or not profesor_ausente_id:
        return jsonify({"error": "fecha, periodos y profesor_ausente_id son obligatorios"}), 400

    ausente = db.get_teacher(profesor_ausente_id)
    if not ausente:
        return jsonify({"error": "Profesor ausente no encontrado"}), 404

    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Formato de fecha inválido (debe ser YYYY-MM-DD)"}), 400

    dia_semana = fecha_dt.weekday()
    if dia_semana >= 5:
        return jsonify({"error": "El día seleccionado es fin de semana (sin actividad escolar)."}), 400

    slots_all = db.get_time_slots()
    slots_map = {s.id: s for s in slots_all}
    orden_ids = [s.id for s in slots_all]

    periodos_ordenados = sorted(
        list(dict.fromkeys(periodos)),
        key=lambda x: orden_ids.index(x) if x in orden_ids else 999
    )

    sust_dia = [
        s for s in db.get_substitutions()
        if s.fecha == fecha and s.estado != "CANCELADA"
    ]

    tramos_evaluados = []
    virtual_loads = {}
    for pid in periodos_ordenados:
        slot = slots_map.get(pid)
        if not slot or slot.es_recreo:
            continue

        item = db.get_slot_activity_for_teacher(profesor_ausente_id, dia_semana, pid)
        ov = overrides.get(pid, {})

        tiene_clase = bool(item and item.tipo_actividad == ActivityType.LECTIVA)
        aula_auto = (item.aula or "") if tiene_clase else ""
        grupo_auto = (item.curso_grupo or item.aula or "") if tiene_clase else ""
        materia_auto = (item.materia or "") if tiene_clase else ""

        aula_final = ov.get("aula") if ov.get("aula") is not None else aula_auto
        grupo_final = ov.get("curso_grupo") if ov.get("curso_grupo") is not None else grupo_auto
        materia_final = ov.get("materia") if ov.get("materia") is not None else materia_auto

        ya_asignada = next(
            (s.to_dict() for s in sust_dia if s.periodo_id == pid and s.profesor_ausente_id == profesor_ausente_id),
            None
        )

        evaluacion = engine.find_candidates(
            fecha_str=fecha,
            periodo_id=pid,
            profesor_ausente_id=profesor_ausente_id,
            materia=materia_final,
            aula=aula_final,
            extra_loads=virtual_loads
        )

        rec = evaluacion.get("recomendado")
        if tiene_clase and not ya_asignada and rec:
            rec_id = rec["profesor"]["id"]
            virtual_loads[rec_id] = virtual_loads.get(rec_id, 0) + 1

        tramos_evaluados.append({
            "periodo_id": pid,
            "periodo_nombre": slot.nombre,
            "hora_inicio": slot.hora_inicio,
            "hora_fin": slot.hora_fin,
            "tiene_clase_lectiva": tiene_clase,
            "tipo_actividad_ausente": item.tipo_actividad if item else "LIBRE",
            "descripcion_ausente": item.descripcion if item else "Hueco libre",
            "aula": aula_final,
            "curso_grupo": grupo_final,
            "materia": materia_final,
            "ya_asignada": ya_asignada,
            "mensaje_criterio": evaluacion.get("mensaje_criterio", ""),
            "recomendado": evaluacion.get("recomendado"),
            "candidatos": evaluacion.get("candidatos", []),
            "no_disponibles": evaluacion.get("no_disponibles", [])
        })

    return jsonify({
        "fecha": fecha,
        "dia_semana": dia_semana,
        "profesor_ausente": ausente.to_dict(),
        "tramos_evaluados": tramos_evaluados
    })

@app.route("/api/buscar-sustitutos-rango", methods=["POST"])
def search_substitutes_range():
    """
    Busca y clasifica sustitutos para un profesor ausente a lo largo de un rango de fechas
    (bajas médicas, permisos, excursiones), aplicando rotación equitativa intradía e interdías.
    """
    data = request.json or {}
    fecha_inicio_str = data.get("fecha_inicio")
    fecha_fin_str = data.get("fecha_fin")
    profesor_ausente_id = data.get("profesor_ausente_id")
    periodos_lectivos = data.get("periodos", ["1H", "2H", "3H", "4H", "5H"])

    if not fecha_inicio_str or not fecha_fin_str or not profesor_ausente_id:
        return jsonify({"error": "Faltan datos obligatorios (fecha_inicio, fecha_fin, profesor_ausente_id)."}), 400

    try:
        f_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        f_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"error": "Formato de fechas inválido (debe ser YYYY-MM-DD)."}), 400

    if f_inicio > f_fin:
        return jsonify({"error": "La fecha de inicio debe ser anterior o igual a la fecha de fin."}), 400

    # Límite de seguridad: máximo 45 días
    if (f_fin - f_inicio).days > 45:
        return jsonify({"error": "El rango no puede exceder de 45 días naturales."}), 400

    ausente = db.get_teacher(profesor_ausente_id)
    if not ausente:
        return jsonify({"error": "Profesor ausente no encontrado."}), 404

    dias_evaluados = []
    virtual_loads = {}  # Mantiene la rotación acumulada a lo largo de toda la baja
    curr = f_inicio
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    while curr <= f_fin:
        if curr.weekday() < 5:  # Solo días lectivos (Lunes a Viernes)
            dia_str = curr.isoformat()
            dia_semana = curr.weekday()
            
            # Buscar sustituciones ya existentes para este día y ausente
            subs_dia = [
                s for s in db.get_substitutions()
                if s.fecha == dia_str and s.profesor_ausente_id == profesor_ausente_id and s.estado != "CANCELADA"
            ]
            ya_asignadas_map = {s.periodo_id: s.to_dict() for s in subs_dia}

            tramos_del_dia = []
            for pid in periodos_lectivos:
                slot = db.get_time_slot(pid)
                if not slot:
                    continue

                item = db.get_slot_activity_for_teacher(profesor_ausente_id, dia_semana, pid)
                tiene_clase = (item is not None and item.tipo_actividad == ActivityType.LECTIVA)
                ya_asignada = ya_asignadas_map.get(pid)

                materia_final = item.materia if item else ""
                aula_final = item.aula or item.curso_grupo if item else ""
                grupo_final = item.curso_grupo or item.aula if item else ""

                evaluacion = engine.find_candidates(
                    fecha_str=dia_str,
                    periodo_id=pid,
                    profesor_ausente_id=profesor_ausente_id,
                    materia=materia_final,
                    aula=aula_final,
                    extra_loads=virtual_loads
                )

                rec = evaluacion.get("recomendado")
                if tiene_clase and not ya_asignada and rec:
                    rec_id = rec["profesor"]["id"]
                    virtual_loads[rec_id] = virtual_loads.get(rec_id, 0) + 1

                tramos_del_dia.append({
                    "periodo_id": pid,
                    "periodo_nombre": slot.nombre,
                    "hora_inicio": slot.hora_inicio,
                    "hora_fin": slot.hora_fin,
                    "tiene_clase_lectiva": tiene_clase,
                    "tipo_actividad_ausente": item.tipo_actividad if item else "LIBRE",
                    "descripcion_ausente": item.descripcion if item else "Hueco libre",
                    "aula": aula_final,
                    "curso_grupo": grupo_final,
                    "materia": materia_final,
                    "ya_asignada": ya_asignada,
                    "mensaje_criterio": evaluacion.get("mensaje_criterio", ""),
                    "recomendado": evaluacion.get("recomendado"),
                    "candidatos": evaluacion.get("candidatos", []),
                    "no_disponibles": evaluacion.get("no_disponibles", [])
                })

            total_lectivas = sum(1 for t in tramos_del_dia if t["tiene_clase_lectiva"])
            dias_evaluados.append({
                "fecha": dia_str,
                "dia_semana": dia_semana,
                "dia_nombre": dias_nombres[dia_semana],
                "total_horas_lectivas": total_lectivas,
                "tramos_evaluados": tramos_del_dia
            })

        curr += timedelta(days=1)

    return jsonify({
        "fecha_inicio": fecha_inicio_str,
        "fecha_fin": fecha_fin_str,
        "total_dias_lectivos": len(dias_evaluados),
        "profesor_ausente": ausente.to_dict(),
        "dias": dias_evaluados
    })

@app.route("/api/asignar-sustituciones-rango", methods=["POST"])
def assign_substitutions_range():
    """Asigna todas las sustituciones de un rango de fechas (baja/excursión) de una sola vez."""
    data = request.json or {}
    profesor_ausente_id = data.get("profesor_ausente_id")
    dias_asignaciones = data.get("dias_asignaciones", [])
    que_hacer_global = data.get("que_hacer", "")

    if not profesor_ausente_id or not dias_asignaciones:
        return jsonify({"error": "Faltan datos obligatorios para la asignación por rango."}), 400

    total_asignadas = 0
    errores = []

    for dia_obj in dias_asignaciones:
        fecha = dia_obj.get("fecha")
        asignaciones = dia_obj.get("asignaciones", [])
        if not fecha or not asignaciones:
            continue

        for item in asignaciones:
            periodo_id = item.get("periodo_id")
            profesor_sustituto_id = item.get("profesor_sustituto_id")
            if not periodo_id or not profesor_sustituto_id:
                continue

            aula = item.get("aula") or item.get("curso_grupo") or ""
            curso_grupo = item.get("curso_grupo") or item.get("aula") or ""
            materia = item.get("materia") or ""
            qh = item.get("que_hacer") if item.get("que_hacer") is not None else que_hacer_global

            try:
                _crear_registro_sustitucion(
                    fecha=fecha,
                    periodo_id=periodo_id,
                    profesor_ausente_id=profesor_ausente_id,
                    profesor_sustituto_id=profesor_sustituto_id,
                    aula=aula,
                    curso_grupo=curso_grupo,
                    materia=materia,
                    que_hacer=qh
                )
                total_asignadas += 1
            except ValueError as e:
                errores.append({"fecha": fecha, "periodo_id": periodo_id, "error": str(e)})

    return jsonify({
        "success": True,
        "total_asignadas": total_asignadas,
        "errores": errores
    })

def _crear_registro_sustitucion(fecha, periodo_id, profesor_ausente_id, profesor_sustituto_id, aula, curso_grupo, materia, que_hacer):
    """Crea y persiste un registro de sustitución con el campo 'Qué deben hacer en su hora'."""
    ausente = db.get_teacher(profesor_ausente_id)
    sustituto = db.get_teacher(profesor_sustituto_id)
    slot = db.get_time_slot(periodo_id)

    if not ausente or not sustituto or not slot:
        raise ValueError("Entidades no encontradas en el sistema")

    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    except Exception:
        raise ValueError("Formato de fecha inválido (debe ser YYYY-MM-DD)")

    if fecha_dt.weekday() >= 5:
        raise ValueError("No se pueden registrar sustituciones en fin de semana.")

    # Comprobar si el sustituto ya tiene otra sustitución activa en ese mismo tramo
    sustituciones_existentes = [
        s for s in db.get_substitutions()
        if s.fecha == fecha and s.periodo_id == periodo_id and s.estado != "CANCELADA"
    ]
    for s in sustituciones_existentes:
        if s.profesor_sustituto_id == sustituto.id:
            raise ValueError(f"{sustituto.nombre} ya tiene asignada otra sustitución en {slot.nombre}.")
        if s.profesor_ausente_id == sustituto.id:
            raise ValueError(f"{sustituto.nombre} figura como ausente en {slot.nombre}.")

    # Comprobar si el sustituto tiene clase lectiva
    actividad = db.get_slot_activity_for_teacher(sustituto.id, fecha_dt.weekday(), periodo_id)
    if actividad and actividad.tipo_actividad == ActivityType.LECTIVA:
        raise ValueError(f"{sustituto.nombre} tiene clase lectiva en {slot.nombre} ({actividad.materia or actividad.aula}).")

    record_id = f"sub-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4]}"

    record = SubstitutionRecord(
        id=record_id,
        fecha=fecha,
        dia_semana=fecha_dt.weekday(),
        periodo_id=slot.id,
        periodo_nombre=slot.nombre,
        profesor_ausente_id=ausente.id,
        profesor_ausente_nombre=ausente.nombre,
        profesor_sustituto_id=sustituto.id,
        profesor_sustituto_nombre=sustituto.nombre,
        profesor_sustituto_telefono=sustituto.telefono,
        profesor_sustituto_email=sustituto.email,
        aula=aula or curso_grupo or "",
        curso_grupo=curso_grupo or aula or "",
        materia=materia or "",
        observaciones=que_hacer or "",
        que_hacer=que_hacer or "",
        estado="ASIGNADA"
    )

    db.add_substitution(record)

    return {
        "record": record.to_dict(),
        "hora_inicio": slot.hora_inicio,
        "hora_fin": slot.hora_fin
    }

@app.route("/api/asignar-sustitucion", methods=["POST"])
def assign_substitution():
    """Asigna una sustitución individual con el campo 'Qué deben hacer en su hora'."""
    data = request.json or {}
    fecha = data.get("fecha")
    periodo_id = data.get("periodo_id")
    profesor_ausente_id = data.get("profesor_ausente_id")
    profesor_sustituto_id = data.get("profesor_sustituto_id")
    aula = data.get("aula", "")
    curso_grupo = data.get("curso_grupo", "")
    materia = data.get("materia", "")
    que_hacer = data.get("que_hacer") or data.get("observaciones", "")

    if not all([fecha, periodo_id, profesor_ausente_id, profesor_sustituto_id]):
        return jsonify({"error": "Faltan campos obligatorios para la asignación"}), 400

    try:
        res = _crear_registro_sustitucion(
            fecha=fecha,
            periodo_id=periodo_id,
            profesor_ausente_id=profesor_ausente_id,
            profesor_sustituto_id=profesor_sustituto_id,
            aula=aula,
            curso_grupo=curso_grupo,
            materia=materia,
            que_hacer=que_hacer
        )
        res["success"] = True
        return jsonify(res)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/asignar-sustituciones-multiple", methods=["POST"])
def assign_substitutions_multiple():
    """Asigna múltiples sustituciones a la vez."""
    data = request.json or {}
    fecha = data.get("fecha")
    profesor_ausente_id = data.get("profesor_ausente_id")
    que_hacer_global = data.get("que_hacer") or data.get("observaciones", "")
    asignaciones = data.get("asignaciones", [])

    if not fecha or not profesor_ausente_id or not asignaciones:
        return jsonify({"error": "Faltan datos obligatorios para asignar sustituciones."}), 400

    asignadas = []
    errores = []

    for item in asignaciones:
        periodo_id = item.get("periodo_id")
        profesor_sustituto_id = item.get("profesor_sustituto_id")
        if not periodo_id or not profesor_sustituto_id:
            continue

        aula = item.get("aula") or item.get("curso_grupo") or ""
        curso_grupo = item.get("curso_grupo") or item.get("aula") or ""
        materia = item.get("materia") or ""
        qh = item.get("que_hacer") if item.get("que_hacer") is not None else que_hacer_global

        try:
            creada = _crear_registro_sustitucion(
                fecha=fecha,
                periodo_id=periodo_id,
                profesor_ausente_id=profesor_ausente_id,
                profesor_sustituto_id=profesor_sustituto_id,
                aula=aula,
                curso_grupo=curso_grupo,
                materia=materia,
                que_hacer=qh
            )
            asignadas.append(creada)
        except ValueError as e:
            errores.append({"periodo_id": periodo_id, "error": str(e)})

    if not asignadas and errores:
        return jsonify({"error": errores[0]["error"], "errores": errores}), 400

    return jsonify({
        "success": True,
        "asignadas": asignadas,
        "errores": errores
    })

@app.route("/api/estadisticas-equidad", methods=["GET"])
def get_equity_statistics():
    """Devuelve estadísticas analíticas avanzadas de equidad y distribución de sustituciones."""
    trimestre = request.args.get("trimestre", "todo")
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    
    # Determinar rango según trimestre escolar (curso actual)
    año_actual = date.today().year
    # Si estamos a finales de año (ej. 2026), el curso es 2026/2027
    año_inicio_curso = año_actual if date.today().month >= 9 else año_actual - 1
    año_fin_curso = año_inicio_curso + 1

    if not fecha_inicio or not fecha_fin:
        if trimestre == "1":
            fecha_inicio = f"{año_inicio_curso}-09-01"
            fecha_fin = f"{año_inicio_curso}-12-31"
            nombre_periodo = f"1er Trimestre ({año_inicio_curso})"
        elif trimestre == "2":
            fecha_inicio = f"{año_fin_curso}-01-01"
            fecha_fin = f"{año_fin_curso}-03-31"
            nombre_periodo = f"2º Trimestre ({año_fin_curso})"
        elif trimestre == "3":
            fecha_inicio = f"{año_fin_curso}-04-01"
            fecha_fin = f"{año_fin_curso}-06-30"
            nombre_periodo = f"3er Trimestre ({año_fin_curso})"
        else:
            fecha_inicio = f"{año_inicio_curso}-09-01"
            fecha_fin = f"{año_fin_curso}-06-30"
            nombre_periodo = f"Todo el Curso {año_inicio_curso}/{año_fin_curso}"
    else:
        nombre_periodo = f"Del {fecha_inicio} al {fecha_fin}"

    subs = db.get_substitutions()
    subs_periodo = [
        s for s in subs
        if s.estado != "CANCELADA" and (not fecha_inicio or s.fecha >= fecha_inicio) and (not fecha_fin or s.fecha <= fecha_fin)
    ]

    all_teachers = db.get_teachers()
    stats_por_profesor = {}
    for t in all_teachers:
        stats_por_profesor[t.id] = {
            "id": t.id,
            "nombre": t.nombre,
            "etapa": t.etapa,
            "departamento": t.departamento,
            "total_periodo": 0,
            "guardias": 0,
            "reuniones": 0,
            "apoyos": 0,
            "sustituciones_historicas": t.sustituciones_realizadas
        }

    total_guardias = 0
    total_reuniones = 0
    total_apoyos = 0
    por_etapa = {"Primaria": 0, "Infantil": 0}
    por_dia_semana = {"Lunes": 0, "Martes": 0, "Miércoles": 0, "Jueves": 0, "Viernes": 0}
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    por_tramo = {"1H": 0, "2H": 0, "3H": 0, "4H": 0, "5H": 0}

    for s in subs_periodo:
        sust_id = s.profesor_sustituto_id
        if sust_id not in stats_por_profesor:
            # En caso de id con mayúsculas/minúsculas
            for tid in stats_por_profesor:
                if tid.lower() == sust_id.lower():
                    sust_id = tid
                    break

        # Identificar actividad original del sustituto a esa hora
        slot_act = db.get_slot_activity_for_teacher(sust_id, s.dia_semana, s.periodo_id)
        tipo = "REUNION"
        if slot_act:
            if slot_act.tipo_actividad == ActivityType.GUARDIA:
                tipo = "GUARDIA"
            elif slot_act.tipo_actividad == ActivityType.APOYO:
                tipo = "APOYO"
            else:
                tipo = "REUNION"

        if tipo == "GUARDIA":
            total_guardias += 1
        elif tipo == "APOYO":
            total_apoyos += 1
        else:
            total_reuniones += 1

        if sust_id in stats_por_profesor:
            stats_por_profesor[sust_id]["total_periodo"] += 1
            if tipo == "GUARDIA":
                stats_por_profesor[sust_id]["guardias"] += 1
            elif tipo == "APOYO":
                stats_por_profesor[sust_id]["apoyos"] += 1
            else:
                stats_por_profesor[sust_id]["reuniones"] += 1

        # Etapa del ausente
        ausente = db.get_teacher(s.profesor_ausente_id)
        if ausente:
            etapa_aus = ausente.etapa if ausente.etapa in por_etapa else "Primaria"
            por_etapa[etapa_aus] = por_etapa.get(etapa_aus, 0) + 1

        if 0 <= s.dia_semana < 5:
            d_nom = dias_nombres[s.dia_semana]
            por_dia_semana[d_nom] = por_dia_semana.get(d_nom, 0) + 1

        if s.periodo_id in por_tramo:
            por_tramo[s.periodo_id] += 1

    ranking = list(stats_por_profesor.values())
    ranking.sort(key=lambda x: (x["total_periodo"], x["sustituciones_historicas"]), reverse=True)

    # Cálculo del índice de equidad (0-100%): basado en la desviación estándar de cargas
    total_subs = len(subs_periodo)
    if total_subs > 0 and len(ranking) > 0:
        cargas = [p["total_periodo"] for p in ranking]
        media = sum(cargas) / len(cargas)
        varianza = sum((c - media) ** 2 for c in cargas) / len(cargas)
        desv = varianza ** 0.5
        # Cuanto menor sea la desviación respecto a la media, mayor es la equidad
        indice_equidad = max(60, min(100, round(100 - (desv * 8))))
    else:
        indice_equidad = 100

    pct_guardias = round((total_guardias / total_subs) * 100) if total_subs > 0 else 0
    pct_reuniones = round((total_reuniones / total_subs) * 100) if total_subs > 0 else 0
    pct_apoyos = round((total_apoyos / total_subs) * 100) if total_subs > 0 else 0

    return jsonify({
        "periodo_nombre": nombre_periodo,
        "trimestre": trimestre,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "kpi": {
            "total_sustituciones": total_subs,
            "total_guardias": total_guardias,
            "total_reuniones": total_reuniones,
            "total_apoyos": total_apoyos,
            "porcentaje_guardias": pct_guardias,
            "porcentaje_reuniones": pct_reuniones,
            "porcentaje_apoyos": pct_apoyos,
            "indice_equidad": indice_equidad
        },
        "ranking_profesores": ranking,
        "por_etapa": por_etapa,
        "por_dia_semana": por_dia_semana,
        "por_tramo": por_tramo
    })

@app.route("/api/sustituciones", methods=["GET"])
def list_substitutions():
    """Lista las sustituciones, opcionalmente filtradas por semana o fecha."""
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    fecha = request.args.get("fecha")
    
    subs = db.get_substitutions()
    
    if fecha:
        subs = [s for s in subs if s.fecha == fecha]
    elif fecha_inicio and fecha_fin:
        subs = [s for s in subs if fecha_inicio <= s.fecha <= fecha_fin]
        
    return jsonify([s.to_dict() for s in subs])

@app.route("/api/sustituciones/<record_id>/tarea", methods=["POST"])
def update_substitution_task(record_id):
    """Actualiza la tarea ('Qué deben hacer en su hora') de una sustitución existente."""
    data = request.json or {}
    que_hacer = data.get("que_hacer") or data.get("observaciones", "")
    success = db.update_substitution_task(record_id, que_hacer)
    if success:
        return jsonify({"success": True, "que_hacer": que_hacer})
    return jsonify({"error": "Sustitución no encontrada"}), 404

@app.route("/api/sustituciones/<record_id>", methods=["DELETE"])
def delete_substitution(record_id):
    success = db.delete_substitution(record_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Sustitución no encontrada"}), 404

@app.route("/api/export-docx", methods=["GET"])
def export_docx():
    """Genera y descarga el documento oficial editable de Word (.docx) para la semana seleccionada."""
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")

    subs = db.get_substitutions()
    if fecha_inicio and fecha_fin:
        subs_filtradas = [s for s in subs if fecha_inicio <= s.fecha <= fecha_fin and s.estado != "CANCELADA"]
    else:
        # Por defecto, semana actual
        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        viernes = lunes + timedelta(days=4)
        fecha_inicio = lunes.isoformat()
        fecha_fin = viernes.isoformat()
        subs_filtradas = [s for s in subs if fecha_inicio <= s.fecha <= fecha_fin and s.estado != "CANCELADA"]

    bio = generate_weekly_docx(subs_filtradas, fecha_inicio, fecha_fin)
    filename = f"Sustituciones_Escuelas_Pias_{fecha_inicio}_al_{fecha_fin}.docx"

    return send_file(
        bio,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5055))
    print(f"Iniciando Sistema de Sustituciones Escuelas Pías Aluche (Vero) en http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
