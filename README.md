# Sistema de Sustituciones Escolares — Escuelas Pías Aluche

Aplicación web diseñada específicamente para **Vero** y el **Colegio Nuestra Señora de las Escuelas Pías (Aluche)** para la gestión ágil, equitativa e inteligente de sustituciones de profesores en Educación Infantil y Primaria, sincronizada con su **Documento Compartido semanal en Word / Drive**.

---

## 🎯 Criterios y Reglas de Sustitución del Centro

1. **Horas que se cubren**:
   * **Solo se sustituyen las horas de clase regular con alumnos**.
   * Si el profesor ausente tiene asignada guardia, reunión o apoyo, **no se cubre**.
2. **Orden estricto de prelación del sustituto**:
   * **1º Guardia**: Profesores con guardia oficial en esa sesión.
   * **2º Reuniones**: Profesores con reuniones, coordinación, COCOPE, EDE, proyectos, presencia o huecos no lectivos.
   * **3º Apoyos**: Profesores con horas de apoyo lectivo o compensatoria.
3. **Afinidad de etapa**:
   * Primaria sustituye a Primaria e Infantil a Infantil si es posible. Si no hay docentes disponibles en la misma etapa, se recurre a la otra etapa.
4. **Criterio de equidad**:
   * A igualdad de categoría de disponibilidad, el sistema prioriza a quien lleve **menos sustituciones acumuladas** en el historial.

---

## 📋 Columnas del Documento Compartido (Word)

La aplicación genera y exporta exactamente la tabla semanal con las 6 columnas del centro:
1. **Día / Fecha**
2. **Hora** (ej. `09:05 - 10:05`, `10:05 - 11:05`, `11:35 - 12:35`, `14:30 - 15:30`, `15:30 - 16:30`)
3. **Quién falta** (Profesor ausente)
4. **Clase** (Curso y grupo: `6º EP-C`, `3 años-A`, etc.)
5. **Asignatura** (Materia oficial)
6. **Quién sustituye** (Docente seleccionado)
7. **Qué deben hacer en su hora al que le toca** (Tarea/observaciones para el aula)

---

## 🚀 Puesta en Marcha Local

```bash
# 1. Instalar dependencias si fuera necesario
pip install -r requirements.txt

# 2. Iniciar el servidor
python3 app.py
```

Abre en tu navegador: [http://127.0.0.1:5055](http://127.0.0.1:5055)

---

## 📥 Exportación y Copiado Rápido

* **Descargar Word (.docx)**: Un botón directo en la cabecera del cuadrante para descargar el archivo Word oficial semanal con la tabla formateada y editable.
* **Copiar para Word / Drive**: Un botón que copia la tabla en formato HTML enriquecido al portapapeles. Al hacer `Ctrl+V` (o `Cmd+V`) en Word o Google Docs, se pega directamente con los estilos, encabezados y colores del centro.
