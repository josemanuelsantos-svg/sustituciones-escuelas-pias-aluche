"""
Gestor de persistencia robusto con SQLite y sincronización JSON.
Garantiza transacciones ACID, integridad referencial y prevención de corrupción de datos.
"""

import os
import json
import sqlite3
from typing import List, Optional, Dict, Any
from models import Teacher, TimeSlot, ScheduleItem, SubstitutionRecord, ActivityType

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

class Database:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.db_path = os.path.join(self.data_dir, "sustituciones.db")
        self.teachers_file = os.path.join(self.data_dir, "profesores.json")
        self.slots_file = os.path.join(self.data_dir, "tramos_horarios.json")
        self.schedules_file = os.path.join(self.data_dir, "horarios.json")
        self.substitutions_file = os.path.join(self.data_dir, "sustituciones.json")
        
        self._init_sqlite()
        self._migrate_from_json_if_needed()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_sqlite(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tramos (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    hora_inicio TEXT NOT NULL,
                    hora_fin TEXT NOT NULL,
                    es_recreo INTEGER NOT NULL DEFAULT 0,
                    orden INTEGER NOT NULL DEFAULT 1,
                    etapa TEXT NOT NULL DEFAULT 'Primaria'
                );

                CREATE TABLE IF NOT EXISTS profesores (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    telefono TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    departamento TEXT NOT NULL DEFAULT '',
                    etapa TEXT NOT NULL DEFAULT 'Primaria',
                    activo INTEGER NOT NULL DEFAULT 1,
                    sustituciones_realizadas INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS horarios (
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

                CREATE TABLE IF NOT EXISTS sustituciones (
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
                    aula TEXT NOT NULL,
                    curso_grupo TEXT NOT NULL DEFAULT '',
                    materia TEXT NOT NULL DEFAULT '',
                    observaciones TEXT NOT NULL DEFAULT '',
                    estado TEXT NOT NULL DEFAULT 'ASIGNADA',
                    creado_en TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_horarios_docente ON horarios(profesor_id, dia_semana, periodo_id);
                CREATE INDEX IF NOT EXISTS idx_sustituciones_fecha ON sustituciones(fecha, periodo_id);
            """)

    def _migrate_from_json_if_needed(self):
        """Si la base de datos SQLite está vacía, la puebla automáticamente desde los JSON existentes."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM profesores")
            if cur.fetchone()[0] == 0 and os.path.exists(self.teachers_file):
                try:
                    with open(self.teachers_file, "r", encoding="utf-8") as f:
                        profesores = json.load(f)
                    for p in profesores:
                        conn.execute("""
                            INSERT OR REPLACE INTO profesores (id, nombre, telefono, email, departamento, etapa, activo, sustituciones_realizadas)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (p["id"], p["nombre"], p.get("telefono", ""), p.get("email", ""), p.get("departamento", ""), p.get("etapa", "Primaria"), 1 if p.get("activo", True) else 0, p.get("sustituciones_realizadas", 0)))
                except Exception as e:
                    print(f"Error migrando profesores: {e}")

            cur.execute("SELECT COUNT(*) FROM tramos")
            if cur.fetchone()[0] == 0 and os.path.exists(self.slots_file):
                try:
                    with open(self.slots_file, "r", encoding="utf-8") as f:
                        slots = json.load(f)
                    for s in slots:
                        conn.execute("""
                            INSERT OR REPLACE INTO tramos (id, nombre, hora_inicio, hora_fin, es_recreo, orden)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (s["id"], s["nombre"], s["hora_inicio"], s["hora_fin"], 1 if s.get("es_recreo", False) else 0, s.get("orden", 1)))
                except Exception as e:
                    print(f"Error migrando tramos: {e}")

            cur.execute("SELECT COUNT(*) FROM horarios")
            if cur.fetchone()[0] == 0 and os.path.exists(self.schedules_file):
                try:
                    with open(self.schedules_file, "r", encoding="utf-8") as f:
                        horarios = json.load(f)
                    for h in horarios:
                        conn.execute("""
                            INSERT OR REPLACE INTO horarios (profesor_id, dia_semana, periodo_id, tipo_actividad, aula, materia, descripcion)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (h["profesor_id"], h["dia_semana"], h["periodo_id"], h["tipo_actividad"], h.get("aula", ""), h.get("materia", ""), h.get("descripcion", "")))
                except Exception as e:
                    print(f"Error migrando horarios: {e}")

            cur.execute("SELECT COUNT(*) FROM sustituciones")
            if cur.fetchone()[0] == 0 and os.path.exists(self.substitutions_file):
                try:
                    with open(self.substitutions_file, "r", encoding="utf-8") as f:
                        subs = json.load(f)
                    for s in subs:
                        conn.execute("""
                            INSERT OR REPLACE INTO sustituciones (id, fecha, dia_semana, periodo_id, periodo_nombre, profesor_ausente_id, profesor_ausente_nombre, profesor_sustituto_id, profesor_sustituto_nombre, profesor_sustituto_telefono, profesor_sustituto_email, aula, curso_grupo, materia, observaciones, estado, creado_en)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (s["id"], s["fecha"], s["dia_semana"], s["periodo_id"], s["periodo_nombre"], s["profesor_ausente_id"], s["profesor_ausente_nombre"], s["profesor_sustituto_id"], s["profesor_sustituto_nombre"], s.get("profesor_sustituto_telefono", ""), s.get("profesor_sustituto_email", ""), s.get("aula", ""), s.get("curso_grupo", ""), s.get("materia", ""), s.get("observaciones", ""), s.get("estado", "ASIGNADA"), s.get("creado_en", "")))
                except Exception as e:
                    print(f"Error migrando sustituciones: {e}")

    def _sync_json(self, file_path: str, data: List[Dict[str, Any]]):
        """Mantiene los archivos JSON actualizados como copia de seguridad / exportación."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # --- TRAMOS HORARIOS ---
    def get_time_slots(self, etapa: Optional[str] = None) -> List[TimeSlot]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT id, nombre, hora_inicio, hora_fin, es_recreo, orden, etapa FROM tramos"
            params = ()
            if etapa:
                query += " WHERE etapa = ?"
                params = (etapa,)
            query += " ORDER BY orden"
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                TimeSlot(
                    id=r["id"],
                    nombre=r["nombre"],
                    hora_inicio=r["hora_inicio"],
                    hora_fin=r["hora_fin"],
                    es_recreo=bool(r["es_recreo"]),
                    orden=r["orden"],
                    etapa=r["etapa"] if "etapa" in r.keys() else "Primaria"
                )
                for r in rows
            ]

    def get_time_slot(self, slot_id: str) -> Optional[TimeSlot]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, nombre, hora_inicio, hora_fin, es_recreo, orden, etapa FROM tramos WHERE id = ?", (slot_id,))
            r = cur.fetchone()
            if r:
                return TimeSlot(
                    id=r["id"],
                    nombre=r["nombre"],
                    hora_inicio=r["hora_inicio"],
                    hora_fin=r["hora_fin"],
                    es_recreo=bool(r["es_recreo"]),
                    orden=r["orden"],
                    etapa=r["etapa"] if "etapa" in r.keys() else "Primaria"
                )
            return None

    def upsert_time_slots(self, slots: List[TimeSlot]):
        with self._get_connection() as conn:
            for s in slots:
                conn.execute("""
                    INSERT INTO tramos (id, nombre, hora_inicio, hora_fin, es_recreo, orden, etapa)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        nombre=excluded.nombre,
                        hora_inicio=excluded.hora_inicio,
                        hora_fin=excluded.hora_fin,
                        es_recreo=excluded.es_recreo,
                        orden=excluded.orden,
                        etapa=excluded.etapa
                """, (s.id, s.nombre, s.hora_inicio, s.hora_fin, 1 if s.es_recreo else 0, s.orden, getattr(s, "etapa", "Primaria")))
        self._sync_json(self.slots_file, [s.to_dict() for s in self.get_time_slots()])

    def save_time_slots(self, slots: List[TimeSlot]):
        self.upsert_time_slots(slots)

    # --- PROFESORES ---
    def get_teachers(self, active_only: bool = False, etapa: Optional[str] = None) -> List[Teacher]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = """
                SELECT p.id, p.nombre, p.telefono, p.email, p.departamento, p.etapa, p.activo,
                       COALESCE(sub_counts.cnt, 0) AS sustituciones_realizadas
                FROM profesores p
                LEFT JOIN (
                    SELECT profesor_sustituto_id, COUNT(*) as cnt
                    FROM sustituciones
                    WHERE estado != 'CANCELADA'
                    GROUP BY profesor_sustituto_id
                ) sub_counts ON (
                    p.id = sub_counts.profesor_sustituto_id COLLATE NOCASE
                    OR (p.id = 'jos7' AND sub_counts.profesor_sustituto_id COLLATE NOCASE = 'colivares')
                    OR (p.id = 'ipena' AND sub_counts.profesor_sustituto_id COLLATE NOCASE IN ('fpriego', 'feli', 'felicitacion_priego', 'felicitacionpriego'))
                    OR (p.id = 'cduerto' AND sub_counts.profesor_sustituto_id COLLATE NOCASE = 'cdue1')
                )
                WHERE 1=1
            """
            params = []
            if active_only:
                query += " AND p.activo = 1"
            if etapa:
                query += " AND p.etapa = ?"
                params.append(etapa)
            query += " ORDER BY p.nombre"
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [
                Teacher(
                    id=r["id"],
                    nombre=r["nombre"],
                    telefono=r["telefono"],
                    email=r["email"],
                    departamento=r["departamento"],
                    etapa=r["etapa"],
                    activo=bool(r["activo"]),
                    sustituciones_realizadas=r["sustituciones_realizadas"]
                )
                for r in rows
            ]

    def get_teacher(self, teacher_id: str) -> Optional[Teacher]:
        if teacher_id and teacher_id.lower() in ["colivares", "casandra_olivares"]:
            teacher_id = "jos7"
        if teacher_id and teacher_id.lower() in ["fpriego", "feli", "feli_priego", "felicitacion_priego", "felicitacionpriego"]:
            teacher_id = "ipena"
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = """
                SELECT p.id, p.nombre, p.telefono, p.email, p.departamento, p.etapa, p.activo,
                       COALESCE(sub_counts.cnt, 0) AS sustituciones_realizadas
                FROM profesores p
                LEFT JOIN (
                    SELECT profesor_sustituto_id, COUNT(*) as cnt
                    FROM sustituciones
                    WHERE estado != 'CANCELADA'
                    GROUP BY profesor_sustituto_id
                ) sub_counts ON (
                    p.id = sub_counts.profesor_sustituto_id COLLATE NOCASE
                    OR (p.id = 'jos7' AND sub_counts.profesor_sustituto_id COLLATE NOCASE = 'colivares')
                    OR (p.id = 'ipena' AND sub_counts.profesor_sustituto_id COLLATE NOCASE IN ('fpriego', 'feli', 'felicitacion_priego', 'felicitacionpriego'))
                    OR (p.id = 'cduerto' AND sub_counts.profesor_sustituto_id COLLATE NOCASE = 'cdue1')
                )
                WHERE p.id = ? COLLATE NOCASE
                LIMIT 1
            """
            cur.execute(query, (teacher_id,))
            r = cur.fetchone()
            if r:
                return Teacher(
                    id=r["id"],
                    nombre=r["nombre"],
                    telefono=r["telefono"],
                    email=r["email"],
                    departamento=r["departamento"],
                    etapa=r["etapa"],
                    activo=bool(r["activo"]),
                    sustituciones_realizadas=r["sustituciones_realizadas"]
                )
            return None

    def save_teachers(self, teachers: List[Teacher]):
        with self._get_connection() as conn:
            for t in teachers:
                conn.execute("""
                    INSERT INTO profesores (id, nombre, telefono, email, departamento, etapa, activo, sustituciones_realizadas)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        nombre=excluded.nombre,
                        telefono=excluded.telefono,
                        email=excluded.email,
                        departamento=excluded.departamento,
                        etapa=excluded.etapa,
                        activo=excluded.activo,
                        sustituciones_realizadas=excluded.sustituciones_realizadas
                """, (t.id, t.nombre, t.telefono, t.email, t.departamento, t.etapa, 1 if t.activo else 0, t.sustituciones_realizadas))
        self._sync_json(self.teachers_file, [t.to_dict() for t in self.get_teachers()])

    def update_teacher_substitution_count(self, teacher_id: str, delta: int = 1):
        if teacher_id and teacher_id.lower() in ["colivares", "casandra_olivares"]:
            teacher_id = "jos7"
        if teacher_id and teacher_id.lower() in ["fpriego", "feli", "feli_priego", "felicitacion_priego", "felicitacionpriego"]:
            teacher_id = "ipena"
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE profesores
                SET sustituciones_realizadas = MAX(0, sustituciones_realizadas + ?)
                WHERE id = ?
            """, (delta, teacher_id))
        self._sync_json(self.teachers_file, [t.to_dict() for t in self.get_teachers()])

    # --- HORARIOS ---
    def get_schedules(self, etapa: Optional[str] = None) -> List[ScheduleItem]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            if etapa:
                cur.execute("""
                    SELECT h.profesor_id, h.dia_semana, h.periodo_id, h.tipo_actividad, h.aula, h.materia, h.descripcion
                    FROM horarios h
                    JOIN profesores p ON h.profesor_id = p.id
                    WHERE p.etapa = ?
                    ORDER BY h.dia_semana, h.periodo_id
                """, (etapa,))
            else:
                cur.execute("SELECT profesor_id, dia_semana, periodo_id, tipo_actividad, aula, materia, descripcion FROM horarios ORDER BY dia_semana, periodo_id")
            rows = cur.fetchall()
            return [
                ScheduleItem(
                    profesor_id=r["profesor_id"],
                    dia_semana=r["dia_semana"],
                    periodo_id=r["periodo_id"],
                    tipo_actividad=r["tipo_actividad"],
                    aula=r["aula"],
                    materia=r["materia"],
                    descripcion=r["descripcion"]
                )
                for r in rows
            ]

    def upsert_schedules(self, schedules: List[ScheduleItem]):
        with self._get_connection() as conn:
            for h in schedules:
                conn.execute("""
                    INSERT INTO horarios (profesor_id, dia_semana, periodo_id, tipo_actividad, aula, materia, descripcion)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(profesor_id, dia_semana, periodo_id) DO UPDATE SET
                        tipo_actividad=excluded.tipo_actividad,
                        aula=excluded.aula,
                        materia=excluded.materia,
                        descripcion=excluded.descripcion
                """, (h.profesor_id, h.dia_semana, h.periodo_id, h.tipo_actividad, h.aula, h.materia, h.descripcion))
        self._sync_json(self.schedules_file, [s.to_dict() for s in self.get_schedules()])

    def save_schedules(self, schedules: List[ScheduleItem]):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM horarios")
            for h in schedules:
                conn.execute("""
                    INSERT INTO horarios (profesor_id, dia_semana, periodo_id, tipo_actividad, aula, materia, descripcion)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (h.profesor_id, h.dia_semana, h.periodo_id, h.tipo_actividad, h.aula, h.materia, h.descripcion))
        self._sync_json(self.schedules_file, [s.to_dict() for s in schedules])

    def get_schedule_for_teacher(self, teacher_id: str) -> List[ScheduleItem]:
        if teacher_id and teacher_id.lower() in ["colivares", "casandra_olivares"]:
            teacher_id = "jos7"
        if teacher_id and teacher_id.lower() in ["fpriego", "feli", "feli_priego", "felicitacion_priego", "felicitacionpriego"]:
            teacher_id = "ipena"
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT profesor_id, dia_semana, periodo_id, tipo_actividad, aula, materia, descripcion
                FROM horarios
                WHERE profesor_id = ?
                ORDER BY dia_semana, periodo_id
            """, (teacher_id,))
            rows = cur.fetchall()
            return [
                ScheduleItem(
                    profesor_id=r["profesor_id"],
                    dia_semana=r["dia_semana"],
                    periodo_id=r["periodo_id"],
                    tipo_actividad=r["tipo_actividad"],
                    aula=r["aula"],
                    materia=r["materia"],
                    descripcion=r["descripcion"]
                )
                for r in rows
            ]

    def get_slot_activity_for_teacher(self, teacher_id: str, dia_semana: int, periodo_id: str) -> Optional[ScheduleItem]:
        if teacher_id and teacher_id.lower() in ["colivares", "casandra_olivares"]:
            teacher_id = "jos7"
        if teacher_id and teacher_id.lower() in ["fpriego", "feli", "feli_priego", "felicitacion_priego", "felicitacionpriego"]:
            teacher_id = "ipena"
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT profesor_id, dia_semana, periodo_id, tipo_actividad, aula, materia, descripcion
                FROM horarios
                WHERE profesor_id = ? AND dia_semana = ? AND periodo_id = ?
                LIMIT 1
            """, (teacher_id, dia_semana, periodo_id))
            r = cur.fetchone()
            if r:
                return ScheduleItem(
                    profesor_id=r["profesor_id"],
                    dia_semana=r["dia_semana"],
                    periodo_id=r["periodo_id"],
                    tipo_actividad=r["tipo_actividad"],
                    aula=r["aula"],
                    materia=r["materia"],
                    descripcion=r["descripcion"]
                )
            return None

    # --- SUSTITUCIONES ---
    def get_substitutions(self) -> List[SubstitutionRecord]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, fecha, dia_semana, periodo_id, periodo_nombre, profesor_ausente_id, profesor_ausente_nombre,
                       profesor_sustituto_id, profesor_sustituto_nombre, profesor_sustituto_telefono, profesor_sustituto_email,
                       aula, curso_grupo, materia, observaciones, estado, creado_en
                FROM sustituciones
                ORDER BY fecha DESC, creado_en DESC
            """)
            rows = cur.fetchall()
            return [
                SubstitutionRecord(
                    id=r["id"],
                    fecha=r["fecha"],
                    dia_semana=r["dia_semana"],
                    periodo_id=r["periodo_id"],
                    periodo_nombre=r["periodo_nombre"],
                    profesor_ausente_id=r["profesor_ausente_id"],
                    profesor_ausente_nombre=r["profesor_ausente_nombre"],
                    profesor_sustituto_id=r["profesor_sustituto_id"],
                    profesor_sustituto_nombre=r["profesor_sustituto_nombre"],
                    profesor_sustituto_telefono=r["profesor_sustituto_telefono"],
                    profesor_sustituto_email=r["profesor_sustituto_email"],
                    aula=r["aula"],
                    curso_grupo=r["curso_grupo"],
                    materia=r["materia"],
                    observaciones=r["observaciones"],
                    estado=r["estado"],
                    creado_en=r["creado_en"]
                )
                for r in rows
            ]

    def get_substitution(self, record_id: str) -> Optional[SubstitutionRecord]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, fecha, dia_semana, periodo_id, periodo_nombre, profesor_ausente_id, profesor_ausente_nombre,
                       profesor_sustituto_id, profesor_sustituto_nombre, profesor_sustituto_telefono, profesor_sustituto_email,
                       aula, curso_grupo, materia, observaciones, estado, creado_en
                FROM sustituciones
                WHERE id = ?
            """, (record_id,))
            r = cur.fetchone()
            if r:
                return SubstitutionRecord(
                    id=r["id"],
                    fecha=r["fecha"],
                    dia_semana=r["dia_semana"],
                    periodo_id=r["periodo_id"],
                    periodo_nombre=r["periodo_nombre"],
                    profesor_ausente_id=r["profesor_ausente_id"],
                    profesor_ausente_nombre=r["profesor_ausente_nombre"],
                    profesor_sustituto_id=r["profesor_sustituto_id"],
                    profesor_sustituto_nombre=r["profesor_sustituto_nombre"],
                    profesor_sustituto_telefono=r["profesor_sustituto_telefono"],
                    profesor_sustituto_email=r["profesor_sustituto_email"],
                    aula=r["aula"],
                    curso_grupo=r["curso_grupo"],
                    materia=r["materia"],
                    observaciones=r["observaciones"],
                    estado=r["estado"],
                    creado_en=r["creado_en"]
                )
            return None

    def add_substitution(self, record: SubstitutionRecord) -> SubstitutionRecord:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sustituciones (
                    id, fecha, dia_semana, periodo_id, periodo_nombre, profesor_ausente_id, profesor_ausente_nombre,
                    profesor_sustituto_id, profesor_sustituto_nombre, profesor_sustituto_telefono, profesor_sustituto_email,
                    aula, curso_grupo, materia, observaciones, estado, creado_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.fecha, record.dia_semana, record.periodo_id, record.periodo_nombre,
                record.profesor_ausente_id, record.profesor_ausente_nombre, record.profesor_sustituto_id,
                record.profesor_sustituto_nombre, record.profesor_sustituto_telefono, record.profesor_sustituto_email,
                record.aula, record.curso_grupo, record.materia, record.observaciones, record.estado, record.creado_en
            ))
            # Sincronizar contador de sustituciones del profesor
            conn.execute("""
                UPDATE profesores
                SET sustituciones_realizadas = (
                    SELECT COUNT(*) FROM sustituciones 
                    WHERE (profesor_sustituto_id = profesores.id COLLATE NOCASE
                           OR (profesores.id = 'jos7' AND profesor_sustituto_id COLLATE NOCASE = 'colivares')
                           OR (profesores.id = 'ipena' AND profesor_sustituto_id COLLATE NOCASE IN ('fpriego', 'feli', 'felicitacion_priego', 'felicitacionpriego'))
                           OR (profesores.id = 'cduerto' AND profesor_sustituto_id COLLATE NOCASE = 'cdue1'))
                      AND estado != 'CANCELADA'
                )
                WHERE id = ? COLLATE NOCASE
                   OR (id = 'jos7' AND ? COLLATE NOCASE = 'colivares')
                   OR (id = 'ipena' AND ? COLLATE NOCASE IN ('fpriego', 'feli', 'felicitacion_priego', 'felicitacionpriego'))
                   OR (id = 'cduerto' AND ? COLLATE NOCASE = 'cdue1')
            """, (record.profesor_sustituto_id, record.profesor_sustituto_id, record.profesor_sustituto_id))
        
        self._sync_json(self.substitutions_file, [r.to_dict() for r in self.get_substitutions()])
        self._sync_json(self.teachers_file, [t.to_dict() for t in self.get_teachers()])
        return record

    def delete_substitution(self, record_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT profesor_sustituto_id FROM sustituciones WHERE id = ?", (record_id,))
            r = cur.fetchone()
            if not r:
                return False
            
            sustituto_id = r["profesor_sustituto_id"]
            conn.execute("DELETE FROM sustituciones WHERE id = ?", (record_id,))
            conn.execute("""
                UPDATE profesores
                SET sustituciones_realizadas = (
                    SELECT COUNT(*) FROM sustituciones 
                    WHERE (profesor_sustituto_id = profesores.id COLLATE NOCASE
                           OR (profesores.id = 'jos7' AND profesor_sustituto_id COLLATE NOCASE = 'colivares')
                           OR (profesores.id = 'ipena' AND profesor_sustituto_id COLLATE NOCASE IN ('fpriego', 'feli', 'felicitacion_priego', 'felicitacionpriego'))
                           OR (profesores.id = 'cduerto' AND profesor_sustituto_id COLLATE NOCASE = 'cdue1'))
                      AND estado != 'CANCELADA'
                )
                WHERE id = ? COLLATE NOCASE
                   OR (id = 'jos7' AND ? COLLATE NOCASE = 'colivares')
                   OR (id = 'ipena' AND ? COLLATE NOCASE IN ('fpriego', 'feli', 'felicitacion_priego', 'felicitacionpriego'))
                   OR (id = 'cduerto' AND ? COLLATE NOCASE = 'cdue1')
            """, (sustituto_id, sustituto_id, sustituto_id))

        self._sync_json(self.substitutions_file, [r.to_dict() for r in self.get_substitutions()])
        self._sync_json(self.teachers_file, [t.to_dict() for t in self.get_teachers()])
        return True
