/**
 * Lógica de cliente para el Sistema de Sustituciones Escolares · Colegio San Buenaventura
 */

// Asegurar etapa activa de forma robusta según la URL o contexto
if (!window.ETAPA_ACTIVA) {
  if (typeof window !== "undefined" && window.location && window.location.pathname.includes("/infantil")) {
    window.ETAPA_ACTIVA = "Infantil";
  } else {
    window.ETAPA_ACTIVA = "Primaria";
  }
}

// Estado global de la aplicación
let appState = {
  profesores: [],
  tramos: [],
  horarios: [],
  sustituciones: [],
  estadisticas: [],
  tramosSeleccionados: [], // Lista de periodo_id seleccionados (ej. ["1H", "2H"])
  ultimoResultadoBusqueda: null,
  ultimoResultadoMultiple: null,
  seleccionesMultiples: {}, // { periodo_id: { activo, profesor_sustituto_id, aula, curso_grupo, materia } }
  ultimaSustitucionAsignada: null
};

const DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

const NOMBRES_MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
];

// Orden oficial de prioridad por etapa educativa (para ordenación interna)
const ORDEN_PRIORIDAD_PRIMARIA = {
  "jos7":      { orden: 1, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "colivares": { orden: 1, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "ipena":     { orden: 2, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "fpriego":   { orden: 2, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "feli":      { orden: 2, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "m654":      { orden: 3, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "p740":      { orden: 4, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "mar1":      { orden: 5, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "cduerto":   { orden: 6, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "pgonzalez": { orden: 7, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "bleo0":     { orden: 8, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "r299":      { orden: 9, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "j414":      { orden: 10, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "•" },
  "m851":      { orden: 11, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "•" },
  "dasenjo":   { orden: 12, nivel: "Disponible", badge: "bg-slate-100 text-slate-500 border-slate-200", icon: "•" },
  "mvazquez":  { orden: 13, nivel: "Disponible", badge: "bg-slate-100 text-slate-500 border-slate-200", icon: "•" }
};

const ORDEN_PRIORIDAD_INFANTIL = {
  // Orden oficial interno
  "CDUE1":    { orden: 1, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "M111":     { orden: 2, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "ACAL0":    { orden: 3, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "APER0":    { orden: 4, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "GDEL0":    { orden: 5, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "M251":     { orden: 6, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "MESP0":    { orden: 7, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "M133":     { orden: 8, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "N637":     { orden: 9, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "SUS8":     { orden: 10, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "E587":     { orden: 11, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-200 font-medium", icon: "✓" },
  "dasenjo":  { orden: 12, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-300 font-medium", icon: "•" },
  "mvazquez": { orden: 13, nivel: "Disponible", badge: "bg-slate-100 text-slate-700 border-slate-300 font-medium", icon: "•" }
};

function getPrioridadDocente(profId) {
  const map = (window.ETAPA_ACTIVA === "Infantil") ? ORDEN_PRIORIDAD_INFANTIL : ORDEN_PRIORIDAD_PRIMARIA;
  return map[profId] || { orden: 99, nivel: "Disp.", badge: "bg-slate-100 text-slate-700 border-slate-200", icon: "•" };
}

// Proxy transparente para que todo el código existente funcione con la etapa activa
const ORDEN_PRIORIDAD = new Proxy({}, {
  get: (target, prop) => getPrioridadDocente(prop)
});

let calVisual = {
  ano: new Date().getFullYear(),
  mes: new Date().getMonth(),
  anoSel: new Date().getFullYear(),
  mesSel: new Date().getMonth(),
  diaSel: new Date().getDate()
};

document.addEventListener("DOMContentLoaded", () => {
  iniciarRelojEscolar();
  inicializarFecha();
  cargarDatosIniciales();
  configurarListeners();
});

// ===============================================
// SISTEMA DE NOTIFICACIONES TOAST Y UTILIDADES
// ===============================================

function showToast(mensaje, tipo = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  let colores = "bg-slate-900 text-white border-emerald-500";
  let icono = '<i class="ph-fill ph-check-circle text-emerald-400 text-xl shrink-0"></i>';

  if (tipo === "warning") {
    colores = "bg-slate-900 text-white border-amber-400";
    icono = '<i class="ph-fill ph-warning-circle text-amber-400 text-xl shrink-0"></i>';
  } else if (tipo === "error") {
    colores = "bg-rose-950 text-white border-rose-500";
    icono = '<i class="ph-fill ph-x-circle text-rose-400 text-xl shrink-0"></i>';
  } else if (tipo === "info") {
    colores = "bg-indigo-950 text-white border-indigo-400";
    icono = '<i class="ph-fill ph-info text-indigo-400 text-xl shrink-0"></i>';
  }

  toast.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-2xl shadow-2xl border-l-4 ${colores} text-xs font-semibold animate-fade-in transition-all duration-300`;
  toast.innerHTML = `
    ${icono}
    <div class="flex-1 leading-snug">${mensaje}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    setTimeout(() => toast.remove(), 300);
  }, 3800);
}

function obtenerIniciales(nombre) {
  if (!nombre) return "CSB";
  const limpias = nombre.replace(/Mª|María/gi, "M").trim().split(/\s+/);
  if (limpias.length === 1) return limpias[0].substring(0, 2).toUpperCase();
  return (limpias[0][0] + limpias[1][0]).toUpperCase();
}

function iniciarRelojEscolar() {
  const actualizar = () => {
    const el = document.getElementById("reloj-escolar");
    if (!el) return;
    const ahora = new Date();
    const hh = String(ahora.getHours()).padStart(2, "0");
    const mm = String(ahora.getMinutes()).padStart(2, "0");
    const minTotal = ahora.getHours() * 60 + ahora.getMinutes();

    let tramoActual = "Fuera de horario lectivo";
    const esInfantil = (window.ETAPA_ACTIVA === "Infantil");

    if (esInfantil) {
      if (minTotal >= 525 && minTotal < 570) tramoActual = "En 1ª Hora Infantil (08:45-09:30)";
      else if (minTotal >= 570 && minTotal < 600) tramoActual = "En 2ª Hora Infantil (09:30-10:00)";
      else if (minTotal >= 600 && minTotal < 630) tramoActual = "En Recreo Infantil (10:00-10:30)";
      else if (minTotal >= 630 && minTotal < 675) tramoActual = "En 3ª Hora Infantil (10:30-11:15)";
      else if (minTotal >= 675 && minTotal < 735) tramoActual = "En 4ª Hora Infantil (11:15-12:15)";
      else if (minTotal >= 735 && minTotal < 840) tramoActual = "Comedor Infantil (12:15-14:00)";
      else if (minTotal >= 840 && minTotal < 900) tramoActual = "En 5ª Hora Infantil (14:00-15:00)";
      else if (minTotal >= 900 && minTotal < 960) tramoActual = "En 6ª Hora Infantil (15:00-16:00)";
    } else {
      if (minTotal >= 540 && minTotal < 585) tramoActual = "En 1ª Hora (09:00-09:45)";
      else if (minTotal >= 585 && minTotal < 630) tramoActual = "En 2ª Hora (09:45-10:30)";
      else if (minTotal >= 630 && minTotal < 660) tramoActual = "En Recreo (10:30-11:00)";
      else if (minTotal >= 660 && minTotal < 705) tramoActual = "En 3ª Hora (11:00-11:45)";
      else if (minTotal >= 705 && minTotal < 750) tramoActual = "En 4ª Hora (11:45-12:30)";
      else if (minTotal >= 750 && minTotal < 855) tramoActual = "Comedor / Mediodía";
      else if (minTotal >= 855 && minTotal < 915) tramoActual = "En 5ª Hora (14:15-15:15)";
      else if (minTotal >= 915 && minTotal < 975) tramoActual = "En 6ª Hora (15:15-16:15)";
    }

    el.innerHTML = `<i class="ph-fill ph-clock"></i> <span>${hh}:${mm} · ${tramoActual}</span>`;
  };
  actualizar();
  setInterval(actualizar, 15000);
}

// ===============================================
// NAVEGACIÓN POR PESTAÑAS
// ===============================================

function switchTab(tabId) {
  const esInfantil = (window.ETAPA_ACTIVA === "Infantil");
  const inactiveTextCls = esInfantil ? "text-emerald-100" : "text-blue-100";
  const inactiveMobCls = esInfantil ? "text-emerald-100/80" : "text-blue-200/80";

  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.remove("bg-white", "text-slate-900", "shadow-md", "font-bold");
    btn.classList.add(inactiveTextCls, "font-semibold");
  });
  document.querySelectorAll(".mob-tab-btn").forEach(btn => {
    btn.classList.remove("bg-white", "text-slate-950", "font-extrabold", "shadow-sm");
    btn.classList.add(inactiveMobCls, "font-semibold");
  });

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);
  const targetMobBtn = document.getElementById(`mob-tab-btn-${tabId}`);

  if (targetTab) targetTab.classList.remove("hidden");
  if (targetBtn) {
    targetBtn.classList.add("bg-white", "text-slate-900", "shadow-md", "font-bold");
    targetBtn.classList.remove(inactiveTextCls, "font-semibold", "text-blue-100", "text-emerald-100");
  }
  if (targetMobBtn) {
    targetMobBtn.classList.add("bg-white", "text-slate-950", "font-extrabold", "shadow-sm");
    targetMobBtn.classList.remove(inactiveMobCls, "font-semibold", "text-blue-200/80", "text-emerald-100/80");
  }

  if (window.innerWidth < 768) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (tabId === "horarios") {
    cargarHorariosSemana();
  } else if (tabId === "historial") {
    renderEstadisticas();
    renderHistorial();
  }
}

function scrollToPanelMobile(panelEl) {
  if (!panelEl) return;
  if (window.innerWidth < 1024) {
    setTimeout(() => {
      panelEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
  }
}

// ===============================================
// GESTIÓN DE FECHAS Y CALENDARIO MENSUAL
// ===============================================

function inicializarFecha() {
  const hoy = new Date();
  let fechaDefecto = new Date(hoy);
  if (hoy.getDay() === 0) fechaDefecto.setDate(hoy.getDate() + 1); // Domingo -> Lunes
  if (hoy.getDay() === 6) fechaDefecto.setDate(hoy.getDate() + 2); // Sábado -> Lunes

  calVisual.ano = fechaDefecto.getFullYear();
  calVisual.mes = fechaDefecto.getMonth();
  calVisual.anoSel = fechaDefecto.getFullYear();
  calVisual.mesSel = fechaDefecto.getMonth();
  calVisual.diaSel = fechaDefecto.getDate();

  setInputValueFromDate(fechaDefecto);
  renderCalendarioMensual();
}

function setFechaRelativa(offsetDias) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDias);
  if (d.getDay() === 0) d.setDate(d.getDate() + 1);
  if (d.getDay() === 6) d.setDate(d.getDate() + 2);

  calVisual.ano = d.getFullYear();
  calVisual.mes = d.getMonth();
  calVisual.anoSel = d.getFullYear();
  calVisual.mesSel = d.getMonth();
  calVisual.diaSel = d.getDate();
  setInputValueFromDate(d);
  renderCalendarioMensual();
}

function cambiarMes(delta) {
  calVisual.mes += delta;
  if (calVisual.mes < 0) {
    calVisual.mes = 11;
    calVisual.ano--;
  } else if (calVisual.mes > 11) {
    calVisual.mes = 0;
    calVisual.ano++;
  }
  renderCalendarioMensual();
}

function seleccionarDiaCalendario(y, m, d) {
  calVisual.anoSel = y;
  calVisual.mesSel = m;
  calVisual.diaSel = d;
  calVisual.ano = y;
  calVisual.mes = m;

  const dateObj = new Date(y, m, d);
  setInputValueFromDate(dateObj);
  renderCalendarioMensual();
}

function renderCalendarioMensual() {
  const mesLabel = document.getElementById("cal-mes-ano");
  const grid = document.getElementById("cal-dias-grid");
  const resumenLabel = document.getElementById("cal-fecha-seleccionada");

  if (!grid || !mesLabel) return;

  mesLabel.textContent = `${NOMBRES_MESES[calVisual.mes]} ${calVisual.ano}`;
  grid.innerHTML = "";

  const hoy = new Date();
  const hoyY = hoy.getFullYear();
  const hoyM = hoy.getMonth();
  const hoyD = hoy.getDate();

  // Mapa de fechas que tienen sustituciones para pintar indicador visual
  const fechasConSustitucion = new Set((appState.sustituciones || []).map(s => s.fecha));

  const primerDiaSemana = (new Date(calVisual.ano, calVisual.mes, 1).getDay() + 6) % 7;
  const totalDiasMes = new Date(calVisual.ano, calVisual.mes + 1, 0).getDate();
  const totalDiasMesAnt = new Date(calVisual.ano, calVisual.mes, 0).getDate();

  // Días del mes anterior
  for (let i = primerDiaSemana - 1; i >= 0; i--) {
    const diaNum = totalDiasMesAnt - i;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "py-1.5 rounded-xl text-slate-300 hover:text-slate-500 text-[11px] transition";
    btn.textContent = diaNum;
    const prevM = calVisual.mes === 0 ? 11 : calVisual.mes - 1;
    const prevY = calVisual.mes === 0 ? calVisual.ano - 1 : calVisual.ano;
    btn.onclick = () => seleccionarDiaCalendario(prevY, prevM, diaNum);
    grid.appendChild(btn);
  }

  // Días del mes actual
  for (let d = 1; d <= totalDiasMes; d++) {
    const btn = document.createElement("button");
    btn.type = "button";
    const diaSemana = (new Date(calVisual.ano, calVisual.mes, d).getDay() + 6) % 7;
    const esFinDeSemana = diaSemana >= 5;

    const fechaStr = `${calVisual.ano}-${String(calVisual.mes + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const tieneSust = fechasConSustitucion.has(fechaStr);

    const esSeleccionado = (calVisual.ano === calVisual.anoSel && 
                            calVisual.mes === calVisual.mesSel && 
                            d === calVisual.diaSel);
    const esHoy = (calVisual.ano === hoyY && calVisual.mes === hoyM && d === hoyD);

    let classes = "relative py-1.5 rounded-xl text-xs font-bold transition flex flex-col items-center justify-center cursor-pointer ";

    if (esSeleccionado) {
      classes += "bg-gradient-to-br from-[#132a56] to-indigo-600 text-white shadow-md scale-105 z-10 ";
    } else if (esHoy) {
      classes += "border border-indigo-400 text-indigo-700 bg-indigo-50/70 hover:bg-indigo-100 ";
    } else if (esFinDeSemana) {
      classes += "text-slate-300 hover:bg-slate-100 font-medium ";
    } else {
      classes += "text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 ";
    }

    btn.className = classes;
    btn.innerHTML = `
      <span>${d}</span>
      ${tieneSust ? `<span class="w-1 h-1 rounded-full ${esSeleccionado ? 'bg-amber-300' : 'bg-emerald-500'} mt-0.5"></span>` : ''}
    `;
    btn.onclick = () => seleccionarDiaCalendario(calVisual.ano, calVisual.mes, d);
    grid.appendChild(btn);
  }

  // Días del mes siguiente
  const celdasUsadas = primerDiaSemana + totalDiasMes;
  const celdasRestantes = (7 - (celdasUsadas % 7)) % 7;
  for (let d = 1; d <= celdasRestantes; d++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "py-1.5 rounded-xl text-slate-300 hover:text-slate-500 text-[11px] transition";
    btn.textContent = d;
    const nextM = calVisual.mes === 11 ? 0 : calVisual.mes + 1;
    const nextY = calVisual.mes === 11 ? calVisual.ano + 1 : calVisual.ano;
    btn.onclick = () => seleccionarDiaCalendario(nextY, nextM, d);
    grid.appendChild(btn);
  }

  if (resumenLabel) {
    const fechaSelStr = `${calVisual.anoSel}-${String(calVisual.mesSel + 1).padStart(2, '0')}-${String(calVisual.diaSel).padStart(2, '0')}`;
    resumenLabel.textContent = formatFechaEsp(fechaSelStr);
  }
}

function setInputValueFromDate(d) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const input = document.getElementById("input-fecha");
  if (input) {
    input.value = `${yyyy}-${mm}-${dd}`;
    actualizarEtiquetaDiaSemana();
    consultarActividadProgramada();
    actualizarSustitucionesDelDia();
  }
}

function actualizarEtiquetaDiaSemana() {
  const inputFecha = document.getElementById("input-fecha");
  const labelDia = document.getElementById("label-dia-semana");
  if (!inputFecha || !labelDia || !inputFecha.value) return;

  const partes = inputFecha.value.split("-");
  if (partes.length !== 3) return;

  const y = parseInt(partes[0], 10);
  const m = parseInt(partes[1], 10) - 1;
  const d = parseInt(partes[2], 10);
  const fechaObj = new Date(y, m, d);

  const jsDay = fechaObj.getDay();
  const diaSemanaIndex = (jsDay + 6) % 7;
  const nombreDia = DIAS_SEMANA[diaSemanaIndex] || "";
  
  if (diaSemanaIndex >= 5) {
    labelDia.textContent = `⚠️ ${nombreDia} (No lectivo)`;
    labelDia.className = "text-xs font-bold text-amber-800 bg-amber-100 px-3 py-1 rounded-full border border-amber-300";
  } else {
    labelDia.textContent = `📅 ${nombreDia}`;
    labelDia.className = "text-xs font-bold text-indigo-700 bg-indigo-50 px-3 py-1 rounded-full border border-indigo-200";
  }
}

function formatFechaEsp(fechaStr) {
  if (!fechaStr) return "";
  const partes = fechaStr.split("-");
  if (partes.length !== 3) return fechaStr;
  const y = parseInt(partes[0], 10);
  const m = parseInt(partes[1], 10) - 1;
  const d = parseInt(partes[2], 10);
  const fechaObj = new Date(y, m, d);
  const jsDay = fechaObj.getDay();
  const diaSemanaIndex = (jsDay + 6) % 7;
  const diaNombre = DIAS_SEMANA[diaSemanaIndex] || "";
  return `${diaNombre} ${partes[2]}/${partes[1]}/${partes[0]}`;
}

function sincronizarFechaDesdeInput() {
  const inputFecha = document.getElementById("input-fecha");
  if (!inputFecha || !inputFecha.value) return;

  const partes = inputFecha.value.split("-");
  if (partes.length !== 3) return;

  const y = parseInt(partes[0], 10);
  const m = parseInt(partes[1], 10) - 1;
  const d = parseInt(partes[2], 10);

  calVisual.anoSel = y;
  calVisual.mesSel = m;
  calVisual.diaSel = d;
  calVisual.ano = y;
  calVisual.mes = m;

  renderCalendarioMensual();
  actualizarEtiquetaDiaSemana();
  consultarActividadProgramada();
  actualizarSustitucionesDelDia();
}

function limpiarCamposActividad() {
  const inAula = document.getElementById("input-aula");
  const inGrupo = document.getElementById("input-grupo");
  const inMat = document.getElementById("input-materia");
  const badge = document.getElementById("badge-clase-detectada");
  if (inAula) inAula.value = "";
  if (inGrupo) inGrupo.value = "";
  if (inMat) inMat.value = "";
  if (badge) badge.classList.add("hidden");
}

function configurarListeners() {
  const inputFecha = document.getElementById("input-fecha");
  inputFecha.addEventListener("change", sincronizarFechaDesdeInput);
  inputFecha.addEventListener("input", sincronizarFechaDesdeInput);

  const selectTramo = document.getElementById("select-tramo");
  if (selectTramo) {
    selectTramo.addEventListener("change", (e) => {
      if (e.target.value) {
        appState.tramosSeleccionados = [e.target.value];
      } else {
        appState.tramosSeleccionados = [];
      }
      actualizarPillsTramo();
      consultarActividadProgramada();
    });
  }
  document.getElementById("select-profesor-ausente").addEventListener("change", consultarActividadProgramada);
}

function ordenarTramosCronologicamente(listaIds) {
  const ordenOficial = [
    "1H", "2H", "REC", "3H", "4H", "5H", "6H",
    "INF_1H", "INF_2H", "INF_REC", "INF_3H", "INF_4H", "INF_COM", "INF_5H", "INF_6H"
  ];
  return [...new Set(listaIds)].sort((a, b) => {
    const ia = ordenOficial.indexOf(a);
    const ib = ordenOficial.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}

function seleccionarTramoRapido(tramoId) {
  const idx = appState.tramosSeleccionados.indexOf(tramoId);
  if (idx >= 0) {
    appState.tramosSeleccionados.splice(idx, 1);
  } else {
    appState.tramosSeleccionados.push(tramoId);
  }
  appState.tramosSeleccionados = ordenarTramosCronologicamente(appState.tramosSeleccionados);

  const select = document.getElementById("select-tramo");
  if (select) {
    select.value = appState.tramosSeleccionados[0] || "";
  }
  actualizarPillsTramo();
  consultarActividadProgramada();
}

function seleccionarPresetTramos(preset) {
  const esInfantil = (window.ETAPA_ACTIVA === "Infantil");
  const h1 = esInfantil ? "INF_1H" : "1H";
  const h2 = esInfantil ? "INF_2H" : "2H";
  const h3 = esInfantil ? "INF_3H" : "3H";
  const h4 = esInfantil ? "INF_4H" : "4H";
  const h5 = esInfantil ? "INF_5H" : "5H";
  const h6 = esInfantil ? "INF_6H" : "6H";

  if (preset === "DIA_COMPLETO") {
    appState.tramosSeleccionados = [h1, h2, h3, h4, h5, h6];
  } else if (preset === "MANANA") {
    appState.tramosSeleccionados = [h1, h2, h3, h4];
  } else if (preset === "TARDE") {
    appState.tramosSeleccionados = [h5, h6];
  } else {
    appState.tramosSeleccionados = [];
  }

  const select = document.getElementById("select-tramo");
  if (select) {
    select.value = appState.tramosSeleccionados[0] || "";
  }
  actualizarPillsTramo();
  consultarActividadProgramada();
}

function actualizarPillsTramo() {
  const seleccionados = new Set(appState.tramosSeleccionados || []);
  const esInfantil = (window.ETAPA_ACTIVA === "Infantil");

  document.querySelectorAll(".pill-tramo-btn").forEach(btn => {
    const tid = btn.dataset.tramo;
    const tramoObj = (appState.tramos || []).find(t => t.id === tid);
    const horaIni = tramoObj ? tramoObj.hora_inicio : "";
    const label = tid.replace("INF_", "");

    if (seleccionados.has(tid)) {
      const activeCls = esInfantil
        ? "pill-tramo-btn relative py-2 px-1.5 rounded-xl border-2 border-emerald-500 bg-gradient-to-br from-[#064e3b] to-emerald-600 text-white font-extrabold text-center shadow-md transition scale-[1.02] cursor-pointer"
        : "pill-tramo-btn relative py-2 px-1.5 rounded-xl border-2 border-indigo-600 bg-gradient-to-br from-[#132a56] to-indigo-600 text-white font-extrabold text-center shadow-md transition scale-[1.02] cursor-pointer";
      btn.className = activeCls;
      btn.innerHTML = `
        <span class="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-emerald-400 text-slate-950 flex items-center justify-center text-[9px] font-black shadow-2xs">✓</span>
        <div class="text-xs font-extrabold">${label}</div>
        <div class="text-[9px] text-emerald-100 font-medium">${horaIni}</div>
      `;
    } else {
      btn.className = "pill-tramo-btn relative py-2 px-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-emerald-50/50 hover:border-emerald-200 text-slate-700 font-bold text-center transition cursor-pointer";
      btn.innerHTML = `
        <div class="text-xs font-extrabold">${label}</div>
        <div class="text-[9px] opacity-75 font-medium">${horaIni}</div>
      `;
    }
  });

  // Actualizar badge de resumen y texto del botón de búsqueda
  const badgeHoras = document.getElementById("badge-horas-seleccionadas");
  const btnTexto = document.getElementById("btn-buscar-texto");
  const boxSesionUnica = document.getElementById("box-datos-sesion-unica");
  const n = appState.tramosSeleccionados.length;

  if (badgeHoras) {
    if (n === 0) {
      badgeHoras.textContent = "Ninguna seleccionada";
      badgeHoras.className = "text-[10px] font-bold text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full border border-slate-200";
    } else if (n === 6) {
      badgeHoras.textContent = "☀️ Día Completo (6 horas)";
      badgeHoras.className = "text-[10px] font-extrabold text-amber-900 bg-amber-100 px-2.5 py-0.5 rounded-full border border-amber-300";
    } else if (n === 1) {
      badgeHoras.textContent = `1 hora (${appState.tramosSeleccionados[0]})`;
      badgeHoras.className = "text-[10px] font-extrabold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200";
    } else {
      badgeHoras.textContent = `${n} horas (${appState.tramosSeleccionados.join(", ")})`;
      badgeHoras.className = "text-[10px] font-extrabold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200";
    }
  }

  if (btnTexto) {
    if (n > 1) {
      btnTexto.textContent = n === 6 ? "Buscar Sustitutos para el Día Completo" : `Buscar Sustitutos para ${n} Horas`;
    } else {
      btnTexto.textContent = "Buscar Sustituto Idóneo";
    }
  }

  if (boxSesionUnica) {
    if (n > 1) {
      boxSesionUnica.classList.add("hidden");
    } else {
      boxSesionUnica.classList.remove("hidden");
    }
  }
}

async function consultarActividadProgramada() {
  const fecha = document.getElementById("input-fecha").value;
  const profesor_id = document.getElementById("select-profesor-ausente").value;
  const badge = document.getElementById("badge-clase-detectada");
  const periodos = appState.tramosSeleccionados || [];

  if (!fecha || periodos.length === 0 || !profesor_id) {
    limpiarCamposActividad();
    return;
  }

  // CASO 1: Un solo tramo seleccionado
  if (periodos.length === 1) {
    const periodo_id = periodos[0];
    try {
      const res = await fetch(`/api/actividad-docente?profesor_id=${profesor_id}&periodo_id=${periodo_id}&fecha=${fecha}`);
      const data = await res.json();
      if (data && data.encontrado && data.tipo_actividad === "LECTIVA") {
        document.getElementById("input-aula").value = data.aula || "";
        document.getElementById("input-grupo").value = data.curso_grupo || (data.aula && data.aula.includes("EP") ? data.aula : "");
        document.getElementById("input-materia").value = data.materia || "";

        if (badge) {
          badge.className = "mt-2 p-2.5 rounded-xl border border-indigo-200 bg-indigo-50/80 text-indigo-950 text-xs flex items-center justify-between animate-fade-in";
          badge.innerHTML = `
            <div class="flex items-center gap-2">
              <i class="ph-fill ph-chalkboard-teacher text-indigo-600 text-base"></i>
              <span>Clase detectada (${periodo_id}): <strong>${data.materia}</strong></span>
            </div>
            <span class="px-2 py-0.5 rounded-md bg-indigo-600 text-white font-extrabold text-[11px]">${data.aula || data.curso_grupo}</span>
          `;
        }
      } else {
        limpiarCamposActividad();
        if (badge) {
          badge.className = "mt-2 p-2.5 rounded-xl border border-amber-200 bg-amber-50 text-amber-900 text-xs flex items-center gap-2 animate-fade-in";
          badge.innerHTML = `
            <i class="ph-fill ph-info text-amber-600 text-base shrink-0"></i>
            <span>Este docente <strong>no tiene clase lectiva asignada</strong> en ${periodo_id}. Puedes rellenar el aula manualmente si es necesario.</span>
          `;
        }
      }
    } catch (e) {
      console.error("Error al consultar actividad programada:", e);
    }
    return;
  }

  // CASO 2: Varios tramos o Día Completo seleccionados
  try {
    const res = await fetch("/api/actividad-docente-multiple", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profesor_id, fecha, periodos })
    });
    const data = await res.json();
    const acts = data.actividades || [];
    const lectivasCount = acts.filter(a => a.tiene_clase_lectiva).length;

    if (badge) {
      badge.className = "mt-2 p-3 rounded-2xl border border-indigo-200 bg-indigo-50/60 text-slate-800 text-xs space-y-2 animate-fade-in";
      let rowsHtml = acts.map(a => {
        if (a.tiene_clase_lectiva) {
          return `
            <div class="flex items-center justify-between bg-white px-2.5 py-1.5 rounded-xl border border-indigo-100 shadow-2xs">
              <div class="flex items-center gap-2">
                <span class="px-1.5 py-0.5 rounded bg-[#132a56] text-white font-extrabold text-[10px]">${a.periodo_id}</span>
                <span class="font-bold text-slate-800">${a.materia}</span>
              </div>
              <span class="px-2 py-0.5 rounded-md bg-indigo-100 text-indigo-800 font-extrabold text-[10px]">${a.aula}</span>
            </div>
          `;
        } else {
          return `
            <div class="flex items-center justify-between bg-white/60 px-2.5 py-1 rounded-xl border border-slate-200/70 text-slate-400">
              <div class="flex items-center gap-2">
                <span class="px-1.5 py-0.5 rounded bg-slate-200 text-slate-600 font-bold text-[10px]">${a.periodo_id}</span>
                <span class="italic text-[11px]">Sin clase lectiva (hora libre)</span>
              </div>
              <span class="text-[10px] font-semibold">No requiere</span>
            </div>
          `;
        }
      }).join("");

      badge.innerHTML = `
        <div class="flex items-center justify-between text-[11px] font-extrabold text-indigo-950 pb-1 border-b border-indigo-200/60">
          <span class="flex items-center gap-1.5"><i class="ph-fill ph-calendar-check text-indigo-600"></i> Horario detectado en los ${acts.length} tramos</span>
          <span class="px-2 py-0.5 rounded-full bg-indigo-600 text-white text-[10px]">${lectivasCount} clase(s) a cubrir</span>
        </div>
        <div class="space-y-1 max-h-48 overflow-y-auto pr-0.5">${rowsHtml}</div>
      `;
    }
  } catch (e) {
    console.error("Error al consultar actividades múltiples:", e);
  }
}

// ===============================================
// CARGA INICIAL DE DATOS
// ===============================================

async function cargarDatosIniciales() {
  try {
    const etapaParam = window.ETAPA_ACTIVA ? `?etapa=${encodeURIComponent(window.ETAPA_ACTIVA)}` : "";
    const res = await fetch(`/api/initial-data${etapaParam}`);
    const data = await res.json();

    appState.profesores = data.profesores || [];
    appState.tramos = data.tramos || [];
    appState.sustituciones = data.ultimas_sustituciones || [];
    appState.estadisticas = data.estadisticas || [];

    // Cargar también horarios en memoria para la pestaña de cuadrante
    fetch(`/api/horarios${etapaParam}`)
      .then(r => r.json())
      .then(h => { appState.horarios = h || []; });

    poblarSelects();
    renderEstadisticas();
    await renderHistorial();
    actualizarKPIs();
    actualizarSustitucionesDelDia();
    renderCalendarioMensual();
  } catch (err) {
    console.error("Error al cargar datos maestros:", err);
  }
}

function actualizarKPIs() {
  const etapaActual = window.ETAPA_ACTIVA || "Primaria";
  const kpiProf = document.getElementById("kpi-total-profesores");
  const kpiTotal = document.getElementById("kpi-sustituciones-total");
  const profsEtapa = (appState.profesores || []).filter(p => !p.etapa || p.etapa === etapaActual);
  if (kpiProf) kpiProf.textContent = profsEtapa.length;
  if (kpiTotal) kpiTotal.textContent = (appState.sustituciones || []).filter(s => s.estado !== "CANCELADA").length;
}

function actualizarSustitucionesDelDia() {
  const fechaActual = document.getElementById("input-fecha")?.value;
  const kpiFecha = document.getElementById("kpi-sustituciones-fecha");
  const panelDia = document.getElementById("panel-sustituciones-dia");
  const countDia = document.getElementById("count-sust-dia");
  const listaDia = document.getElementById("lista-sustituciones-dia");

  const delDia = (appState.sustituciones || []).filter(s => s.fecha === fechaActual);
  if (kpiFecha) kpiFecha.textContent = delDia.length;

  if (!panelDia || !listaDia) return;

  if (delDia.length === 0) {
    panelDia.classList.add("hidden");
    return;
  }

  panelDia.classList.remove("hidden");
  if (countDia) countDia.textContent = delDia.length;
  listaDia.innerHTML = "";

  delDia.forEach(s => {
    const div = document.createElement("div");
    div.className = "flex flex-wrap items-center justify-between gap-2 p-3 rounded-2xl bg-slate-50 border border-slate-200/80 text-xs";
    div.innerHTML = `
      <div class="flex items-center gap-2.5">
        <span class="px-2.5 py-1 rounded-lg bg-[#132a56] text-white font-extrabold text-[11px]">${s.periodo_id}</span>
        <div>
          <div class="font-bold text-slate-900">
            <span class="text-emerald-700">${s.profesor_sustituto_nombre}</span>
            <span class="text-slate-400 font-normal mx-1">sustituye a</span>
            <span class="text-rose-700">${s.profesor_ausente_nombre}</span>
          </div>
          <div class="text-[11px] text-slate-500">${s.aula} · ${s.materia || 'Sin materia'}</div>
        </div>
      </div>
      <div class="flex items-center gap-1.5">
        ${s.calendar_url ? `<a href="${s.calendar_url}" target="_blank" title="Añadir a Google Calendar (+ aviso email)" class="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-600 text-blue-600 hover:text-white transition"><i class="ph-bold ph-calendar-plus text-sm"></i></a>` : ''}
        ${s.email_url ? `<a href="${s.email_url}" title="Enviar correo individual" class="p-1.5 rounded-lg bg-violet-50 hover:bg-violet-600 text-violet-600 hover:text-white transition"><i class="ph-bold ph-envelope-simple text-sm"></i></a>` : ''}
        ${s.whatsapp_url ? `<a href="${s.whatsapp_url}" target="_blank" title="Enviar WhatsApp" class="p-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-600 text-emerald-600 hover:text-white transition"><i class="ph-bold ph-whatsapp-logo text-sm"></i></a>` : ''}
        <button onclick="eliminarSustitucion('${s.id}')" title="Anular sustitución" class="p-1.5 rounded-lg bg-rose-50 hover:bg-rose-600 text-rose-600 hover:text-white transition cursor-pointer"><i class="ph-bold ph-trash text-sm"></i></button>
      </div>
    `;
    listaDia.appendChild(div);
  });
}

function copiarParteDelDia() {
  const fechaActual = document.getElementById("input-fecha")?.value;
  const etapaActual = window.ETAPA_ACTIVA || "Primaria";
  const delDia = (appState.sustituciones || [])
    .filter(s => s.fecha === fechaActual && s.estado !== "CANCELADA");

  if (delDia.length === 0) {
    showToast("No hay sustituciones registradas en esta fecha para copiar.", "warning");
    return;
  }

  // Ordenar cronológicamente según los tramos de la etapa
  const ordenTramos = (appState.tramos || []).map(t => t.id);
  const ordenadas = [...delDia].sort((a, b) => {
    const ia = ordenTramos.indexOf(a.periodo_id);
    const ib = ordenTramos.indexOf(b.periodo_id);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });

  const fechaTexto = formatFechaEsp(fechaActual);
  const lineas = [
    `📋 *PARTE DE SUSTITUCIONES · ${etapaActual.toUpperCase()}*`,
    `📅 *Fecha:* ${fechaTexto}`,
    `────────────────────`
  ];

  ordenadas.forEach(s => {
    const tramoObj = (appState.tramos || []).find(t => t.id === s.periodo_id);
    const horarioStr = tramoObj
      ? `${tramoObj.nombre.split(' (')[0]} (${tramoObj.hora_inicio}-${tramoObj.hora_fin})`
      : (s.periodo_nombre || s.periodo_id);
    const aulaMateria = [s.aula, s.materia].filter(Boolean).join(" · ");

    lineas.push(`🕒 *${horarioStr}*`);
    lineas.push(`   ✅ *Sustituye:* ${s.profesor_sustituto_nombre}`);
    lineas.push(`   👤 *Ausente:* ${s.profesor_ausente_nombre}`);
    if (aulaMateria) {
      lineas.push(`   🏫 *Aula/Materia:* ${aulaMateria}`);
    }
    if (s.observaciones) {
      lineas.push(`   📝 *Nota:* ${s.observaciones}`);
    }
    lineas.push("");
  });

  lineas.push(`_Colegio San Buenaventura_`);
  const textoFinal = lineas.join("\n");

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(textoFinal).then(() => {
      showToast("📋 ¡Parte del día copiado! Ya puedes pegarlo en WhatsApp.", "success");
    }).catch(() => {
      copiarTextoFallback(textoFinal);
    });
  } else {
    copiarTextoFallback(textoFinal);
  }
}

function copiarTextoFallback(texto) {
  const ta = document.createElement("textarea");
  ta.value = texto;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
  showToast("📋 ¡Parte del día copiado! Ya puedes pegarlo en WhatsApp.", "success");
}

function poblarSelects() {
  const etapaActual = window.ETAPA_ACTIVA || "Primaria";

  // 1. Select y Pills de tramos (filtrados estrictamente por etapa)
  const selectTramo = document.getElementById("select-tramo");
  const pillsContainer = document.getElementById("pills-tramos");

  if (selectTramo) {
    selectTramo.innerHTML = '<option value="">-- Selecciona hora / tramo --</option>';
  }
  if (pillsContainer) {
    pillsContainer.innerHTML = "";
  }

  const tramosFiltrados = (appState.tramos || []).filter(t => !t.etapa || t.etapa === etapaActual);

  tramosFiltrados.forEach(t => {
    if (selectTramo) {
      const option = document.createElement("option");
      option.value = t.id;
      option.textContent = `${t.nombre} (${t.hora_inicio} - ${t.hora_fin})${t.es_recreo ? ' [Recreo]' : ''}`;
      selectTramo.appendChild(option);
    }

    // Crear botón multi-selección para las horas lectivas (1H a 6H)
    if (pillsContainer && !t.es_recreo) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.tramo = t.id;
      btn.className = "pill-tramo-btn relative py-2 px-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-indigo-50 hover:border-indigo-200 text-slate-700 font-bold text-center transition cursor-pointer";
      btn.onclick = () => seleccionarTramoRapido(t.id);
      const label = t.id.replace("INF_", "");
      btn.innerHTML = `
        <div class="text-xs font-extrabold">${label}</div>
        <div class="text-[9px] opacity-75 font-medium">${t.hora_inicio}</div>
      `;
      pillsContainer.appendChild(btn);
    }
  });

  actualizarPillsTramo();

  // 2. Select de profesores ausentes
  const selectAusente = document.getElementById("select-profesor-ausente");
  const currentAusenteVal = selectAusente ? selectAusente.value : "";
  if (selectAusente) {
    selectAusente.innerHTML = '<option value="">-- Selecciona profesor ausente --</option>';
  }
  
  // 3. Select de filtro de profesor en cuadrante
  const selectFiltro = document.getElementById("select-filtro-profesor");
  if (selectFiltro) {
    selectFiltro.innerHTML = '<option value="todos">-- Vista Global del Claustro --</option>';
  }

  const profsFiltrados = (appState.profesores || []).filter(p => !p.etapa || p.etapa === etapaActual);
  const profsOrdenados = [...profsFiltrados].sort((a, b) => a.nombre.localeCompare(b.nombre));

  profsOrdenados.forEach(p => {
    if (selectAusente) {
      const optAusente = document.createElement("option");
      optAusente.value = p.id;
      optAusente.textContent = `${p.nombre}`;
      selectAusente.appendChild(optAusente);
    }

    if (selectFiltro) {
      const optFiltro = document.createElement("option");
      optFiltro.value = p.id;
      optFiltro.textContent = `${p.nombre}`;
      selectFiltro.appendChild(optFiltro);
    }
  });

  if (selectAusente && currentAusenteVal) {
    selectAusente.value = currentAusenteVal;
  }
}

// ===============================================
// BÚSQUEDA Y EVALUACIÓN DE CANDIDATOS (1 O VARIOS TRAMOS)
// ===============================================

async function buscarSustitutos() {
  const fecha = document.getElementById("input-fecha").value;
  const profesor_ausente_id = document.getElementById("select-profesor-ausente").value;
  const periodos = appState.tramosSeleccionados || [];

  if (!fecha || periodos.length === 0 || !profesor_ausente_id) {
    showToast("Selecciona la fecha, al menos una hora (o Día Completo) y el profesor ausente.", "warning");
    return;
  }

  // Comprobar si es fin de semana
  const partesF = fecha.split("-");
  if (partesF.length === 3) {
    const dObj = new Date(parseInt(partesF[0], 10), parseInt(partesF[1], 10) - 1, parseInt(partesF[2], 10));
    const diaSem = (dObj.getDay() + 6) % 7;
    if (diaSem >= 5) {
      showToast("El día seleccionado es fin de semana. Elige un día de lunes a viernes.", "warning");
      return;
    }
  }

  const btnBuscar = document.getElementById("btn-buscar");
  if (btnBuscar) {
    btnBuscar.disabled = true;
    btnBuscar.classList.add("opacity-75", "cursor-not-allowed");
  }

  document.getElementById("panel-inicial").classList.add("hidden");
  document.getElementById("panel-confirmacion").classList.add("hidden");
  document.getElementById("panel-resultados").classList.add("hidden");
  document.getElementById("panel-resultados-multiple").classList.add("hidden");
  document.getElementById("panel-cargando").classList.remove("hidden");

  // MODO 1 TRAMO
  if (periodos.length === 1) {
    const periodo_id = periodos[0];
    const aula = document.getElementById("input-aula").value;
    const materia = document.getElementById("input-materia").value;

    try {
      const res = await fetch("/api/buscar-sustitutos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fecha,
          periodo_id,
          profesor_ausente_id,
          materia,
          aula
        })
      });

      const data = await res.json();
      document.getElementById("panel-cargando").classList.add("hidden");

      if (data.error) {
        showToast(data.error, "error");
        document.getElementById("panel-inicial").classList.remove("hidden");
        return;
      }

      appState.ultimoResultadoBusqueda = data;
      renderResultadosBusqueda(data);

    } catch (err) {
      document.getElementById("panel-cargando").classList.add("hidden");
      showToast("Error de conexión al buscar sustitutos", "error");
      console.error(err);
    } finally {
      if (btnBuscar) {
        btnBuscar.disabled = false;
        btnBuscar.classList.remove("opacity-75", "cursor-not-allowed");
      }
    }
    return;
  }

  // MODO MULTI-HORA O DÍA COMPLETO
  try {
    const res = await fetch("/api/buscar-sustitutos-multiple", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fecha,
        periodos,
        profesor_ausente_id
      })
    });

    const data = await res.json();
    document.getElementById("panel-cargando").classList.add("hidden");

    if (data.error) {
      showToast(data.error, "error");
      document.getElementById("panel-inicial").classList.remove("hidden");
      return;
    }

    appState.ultimoResultadoMultiple = data;
    renderResultadosMultiples(data);

  } catch (err) {
    document.getElementById("panel-cargando").classList.add("hidden");
    showToast("Error de conexión al evaluar múltiples tramos", "error");
    console.error(err);
  } finally {
    if (btnBuscar) {
      btnBuscar.disabled = false;
      btnBuscar.classList.remove("opacity-75", "cursor-not-allowed");
    }
  }
}

function renderResultadosBusqueda(data) {
  const panelResultados = document.getElementById("panel-resultados");
  panelResultados.classList.remove("hidden");
  scrollToPanelMobile(panelResultados);

  const rec = data.recomendado;

  if (!rec) {
    document.getElementById("card-recomendado").classList.add("hidden");
    document.getElementById("lista-alternativas").innerHTML = `
      <div class="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-amber-900 text-xs font-semibold flex items-center gap-2">
        <i class="ph-fill ph-warning text-lg text-amber-600"></i>
        <span>No hay docentes libres disponibles en este tramo horario.</span>
      </div>
    `;
    renderNoDisponibles(data.no_disponibles);
    return;
  }

  // Tarjeta recomendada principal
  document.getElementById("card-recomendado").classList.remove("hidden");
  document.getElementById("rec-nombre").textContent = rec.profesor.nombre;
  const avatarEl = document.getElementById("rec-avatar");
  if (avatarEl) avatarEl.textContent = obtenerIniciales(rec.profesor.nombre);

  document.getElementById("rec-depto").querySelector(".val").textContent = rec.profesor.departamento || "Primaria";
  document.getElementById("rec-etapa").querySelector(".val").textContent = rec.profesor.etapa || "Primaria";
  document.getElementById("rec-telefono").querySelector(".val").textContent = rec.profesor.email || "Sin correo";
  document.getElementById("rec-motivo").textContent = rec.motivo;
  
  document.getElementById("rec-puntuacion").textContent = "Opción idónea";
  document.getElementById("rec-disponibilidad").textContent = "🟢 Disponible en este tramo";

  // Alternativas
  const alternativas = (data.candidatos || []).slice(1);
  document.getElementById("count-alternativas").textContent = alternativas.length;
  
  const listaAlt = document.getElementById("lista-alternativas");
  listaAlt.innerHTML = "";

  if (alternativas.length === 0) {
    listaAlt.innerHTML = `<p class="text-xs text-slate-400 italic py-2">No hay más profesores disponibles en este tramo.</p>`;
  } else {
    alternativas.forEach((c, idx) => {
      const rankNum = idx + 2;
      const iniciales = obtenerIniciales(c.profesor.nombre);

      const card = document.createElement("div");
      card.className = "flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-2xl border border-slate-200/90 hover:border-indigo-300 hover:bg-indigo-50/30 transition group";

      card.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-slate-100 group-hover:bg-indigo-100 text-slate-700 group-hover:text-indigo-800 font-extrabold text-xs flex items-center justify-center shrink-0 transition">
            ${iniciales}
          </div>
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-[11px] font-black text-slate-400">#${rankNum}</span>
              <span class="font-extrabold text-slate-900 text-sm">${c.profesor.nombre}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-md border bg-slate-100 text-slate-700 border-slate-200 font-semibold">Disponible</span>
            </div>
            <div class="text-[11px] text-slate-500 mt-0.5 flex flex-wrap items-center gap-2">
              <span>${c.motivo}</span>
              ${c.profesor.email ? `<span class="text-slate-300">•</span><span class="text-indigo-600/80">${c.profesor.email}</span>` : ''}
            </div>
          </div>
        </div>
        <button onclick="asignarCandidato('${c.profesor.id}', this)" class="py-2 px-4 bg-white hover:bg-indigo-600 text-indigo-700 hover:text-white font-bold text-xs rounded-xl transition border border-indigo-200 hover:border-indigo-600 shadow-2xs shrink-0 cursor-pointer">
          Asignar
        </button>
      `;
      listaAlt.appendChild(card);
    });
  }

  renderNoDisponibles(data.no_disponibles);
}

function renderNoDisponibles(noDisponibles = []) {
  document.getElementById("count-nodisponibles").textContent = noDisponibles.length;
  const listaND = document.getElementById("lista-nodisponibles");
  listaND.innerHTML = "";

  noDisponibles.forEach(nd => {
    const item = document.createElement("div");
    item.className = "py-2 flex items-center justify-between text-xs";
    const esClase = nd.motivo && nd.motivo.toLowerCase().includes("clase");
    item.innerHTML = `
      <span class="font-semibold text-slate-700">${nd.profesor_nombre}</span>
      <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold ${esClase ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-500'}">${nd.motivo}</span>
    `;
    listaND.appendChild(item);
  });
}

// ===============================================
// RENDERIZADO Y GESTIÓN MULTI-HORA / DÍA COMPLETO
// ===============================================

function renderResultadosMultiples(data) {
  const panelMulti = document.getElementById("panel-resultados-multiple");
  const listaContainer = document.getElementById("lista-tramos-multiple");
  if (!panelMulti || !listaContainer) return;

  panelMulti.classList.remove("hidden");
  scrollToPanelMobile(panelMulti);
  document.getElementById("multi-nombre-ausente").textContent = data.profesor_ausente?.nombre || "";
  document.getElementById("multi-resumen-fecha").textContent = `📅 ${formatFechaEsp(data.fecha)}`;

  appState.seleccionesMultiples = {};
  listaContainer.innerHTML = "";

  const tramos = data.tramos_evaluados || [];

  tramos.forEach(t => {
    const pid = t.periodo_id;
    const rec = t.recomendado;
    const yaAsignada = t.ya_asignada;
    const activarPorDefecto = Boolean(t.tiene_clase_lectiva && !yaAsignada && rec);

    appState.seleccionesMultiples[pid] = {
      activo: activarPorDefecto,
      profesor_sustituto_id: rec ? rec.profesor.id : "",
      aula: t.aula || "",
      curso_grupo: t.curso_grupo || t.aula || "",
      materia: t.materia || ""
    };

    const card = document.createElement("div");
    card.id = `multi-card-${pid}`;
    card.className = `rounded-3xl border transition-all p-5 shadow-xs ${
      yaAsignada
        ? "bg-emerald-50/40 border-emerald-300"
        : activarPorDefecto
        ? "bg-white border-indigo-200/90 ring-1 ring-indigo-500/10"
        : "bg-slate-50/80 border-slate-200/80 opacity-85"
    }`;

    // Construir selector de candidatos (pills interactivos + desplegable)
    let candidatosHtml = "";
    if (yaAsignada) {
      candidatosHtml = `
        <div class="mt-3 p-3 rounded-2xl bg-emerald-100/70 border border-emerald-300 text-emerald-950 text-xs flex items-center justify-between">
          <div class="flex items-center gap-2">
            <i class="ph-fill ph-check-circle text-emerald-600 text-base"></i>
            <span>Ya cubierta en esta fecha por <strong>${yaAsignada.profesor_sustituto_nombre}</strong> (${yaAsignada.aula})</span>
          </div>
          <span class="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-emerald-600 text-white">Asignada</span>
        </div>
      `;
    } else if (!t.candidatos || t.candidatos.length === 0) {
      candidatosHtml = `
        <div class="mt-3 p-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold">
          ⚠️ No hay ningún profesor disponible en esta hora.
        </div>
      `;
    } else {
      const pillsCandidatos = t.candidatos.map((c, idx) => {
        const esRec = idx === 0;
        const pInfo = ORDEN_PRIORIDAD[c.profesor.id] || { nivel: "Disp.", badge: "bg-slate-100 text-slate-700 border-slate-200" };
        const seleccionado = c.profesor.id === (rec ? rec.profesor.id : "");

        return `
          <button
            type="button"
            onclick="seleccionarCandidatoTramoMultiple('${pid}', '${c.profesor.id}')"
            id="pill-cand-${pid}-${c.profesor.id}"
            data-tramo="${pid}"
            data-prof="${c.profesor.id}"
            class="cand-multi-btn text-left p-2.5 rounded-2xl border transition flex items-center justify-between gap-2 cursor-pointer ${
              seleccionado
                ? "border-2 border-indigo-600 bg-indigo-50/90 shadow-xs"
                : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-slate-50"
            }"
          >
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-8 h-8 rounded-xl ${
                esRec ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-700"
              } font-black text-[11px] flex items-center justify-center shrink-0">
                ${esRec ? "✓" : "#" + (idx + 1)}
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="font-extrabold text-xs text-slate-900 truncate">${c.profesor.nombre}</span>
                  <span class="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 shrink-0 font-medium">Disponible</span>
                </div>
                <div class="text-[10px] text-slate-500 truncate">${c.profesor.email || c.motivo}</div>
              </div>
            </div>
            <div class="cand-check-icon shrink-0 ${seleccionado ? "text-indigo-600" : "text-slate-300"}">
              <i class="ph-fill ph-check-circle text-lg"></i>
            </div>
          </button>
        `;
      }).join("");

      candidatosHtml = `
        <div class="mt-3.5 pt-3 border-t border-slate-100">
          <div class="flex items-center justify-between mb-2">
            <span class="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <i class="ph-fill ph-users-three text-indigo-600"></i>
              Docentes adecuados disponibles en ${t.periodo_nombre} (${t.candidatos.length}):
            </span>
            <span class="text-[10px] text-indigo-600 font-semibold">Pulsa otro docente si deseas cambiarlo</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
            ${pillsCandidatos}
          </div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <!-- Checkbox + Info de Hora y Clase -->
        <label class="flex items-start sm:items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            id="check-tramo-${pid}"
            ${activarPorDefecto ? "checked" : ""}
            ${yaAsignada || !rec ? "disabled" : ""}
            onchange="toggleIncluirTramoMultiple('${pid}', this.checked)"
            class="mt-1 sm:mt-0 w-5 h-5 rounded-lg text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer"
          >
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-3 py-1 rounded-xl bg-[#132a56] text-white font-extrabold text-xs shadow-2xs">
              ${t.periodo_nombre} (${t.hora_inicio} - ${t.hora_fin})
            </span>
            ${
              t.tiene_clase_lectiva
                ? `<span class="px-2.5 py-1 rounded-xl bg-indigo-100 text-indigo-900 font-extrabold text-xs border border-indigo-200 flex items-center gap-1">
                     <i class="ph-fill ph-chalkboard-teacher text-indigo-600"></i>
                     ${t.aula} · ${t.materia}
                   </span>`
                : `<span class="px-2.5 py-1 rounded-xl bg-amber-50 text-amber-800 font-semibold text-xs border border-amber-200">
                     Hora sin clase lectiva en horario (marca la casilla si deseas cubrirla)
                   </span>`
            }
          </div>
        </label>

        <!-- Campos editables rápidos de Aula y Materia para esa hora -->
        <div class="flex items-center gap-1.5">
          <input
            type="text"
            value="${t.aula || ''}"
            placeholder="Aula (ej. 5ºEP-A)"
            oninput="actualizarDatoTramoMultiple('${pid}', 'aula', this.value)"
            class="w-28 px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
            title="Aula de esta hora"
          >
          <input
            type="text"
            value="${t.materia || ''}"
            placeholder="Materia"
            oninput="actualizarDatoTramoMultiple('${pid}', 'materia', this.value)"
            class="w-32 px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:bg-white focus:ring-2 focus:ring-indigo-500"
            title="Materia de esta hora"
          >
        </div>
      </div>

      ${candidatosHtml}
    `;

    listaContainer.appendChild(card);
  });

  actualizarContadorConfirmarMultiple();
}

function toggleIncluirTramoMultiple(periodoId, checked) {
  if (!appState.seleccionesMultiples[periodoId]) return;
  appState.seleccionesMultiples[periodoId].activo = checked;

  const card = document.getElementById(`multi-card-${periodoId}`);
  if (card) {
    if (checked) {
      card.classList.remove("bg-slate-50/80", "opacity-85");
      card.classList.add("bg-white", "border-indigo-200/90");
    } else {
      card.classList.add("bg-slate-50/80", "opacity-85");
      card.classList.remove("bg-white", "border-indigo-200/90");
    }
  }
  actualizarContadorConfirmarMultiple();
}

function actualizarDatoTramoMultiple(periodoId, campo, valor) {
  if (!appState.seleccionesMultiples[periodoId]) return;
  appState.seleccionesMultiples[periodoId][campo] = valor;
  if (campo === "aula") {
    appState.seleccionesMultiples[periodoId].curso_grupo = valor;
  }
}

function seleccionarCandidatoTramoMultiple(periodoId, profesorSustitutoId) {
  if (!appState.seleccionesMultiples[periodoId]) return;
  appState.seleccionesMultiples[periodoId].profesor_sustituto_id = profesorSustitutoId;
  appState.seleccionesMultiples[periodoId].activo = true;

  const chk = document.getElementById(`check-tramo-${periodoId}`);
  if (chk && !chk.disabled) {
    chk.checked = true;
    toggleIncluirTramoMultiple(periodoId, true);
  }

  document.querySelectorAll(`.cand-multi-btn[data-tramo="${periodoId}"]`).forEach(btn => {
    const esEste = btn.dataset.prof === profesorSustitutoId;
    const iconDiv = btn.querySelector(".cand-check-icon");
    if (esEste) {
      btn.className = "cand-multi-btn text-left p-2.5 rounded-2xl border-2 border-indigo-600 bg-indigo-50/90 shadow-xs transition flex items-center justify-between gap-2 cursor-pointer";
      if (iconDiv) iconDiv.className = "cand-check-icon shrink-0 text-indigo-600";
    } else {
      btn.className = "cand-multi-btn text-left p-2.5 rounded-2xl border border-slate-200 bg-white hover:border-indigo-300 hover:bg-slate-50 transition flex items-center justify-between gap-2 cursor-pointer";
      if (iconDiv) iconDiv.className = "cand-check-icon shrink-0 text-slate-300";
    }
  });

  actualizarContadorConfirmarMultiple();
}

function actualizarContadorConfirmarMultiple() {
  const lbl = document.getElementById("lbl-btn-confirmar-todas");
  const activas = Object.values(appState.seleccionesMultiples || {}).filter(x => x.activo && x.profesor_sustituto_id);
  if (lbl) {
    lbl.textContent = `Confirmar y Asignar (${activas.length} ${activas.length === 1 ? "hora" : "horas"})`;
  }
}

async function confirmarSustitucionesMultiples() {
  const dataMulti = appState.ultimoResultadoMultiple;
  if (!dataMulti) return;

  const fecha = dataMulti.fecha;
  const profesor_ausente_id = dataMulti.profesor_ausente.id;
  const observaciones = document.getElementById("input-observaciones").value;

  const asignaciones = [];
  Object.entries(appState.seleccionesMultiples || {}).forEach(([periodo_id, sel]) => {
    if (sel.activo && sel.profesor_sustituto_id) {
      asignaciones.push({
        periodo_id,
        profesor_sustituto_id: sel.profesor_sustituto_id,
        aula: sel.aula || "Aula asignada",
        curso_grupo: sel.curso_grupo || sel.aula || "",
        materia: sel.materia || "",
        observaciones
      });
    }
  });

  if (asignaciones.length === 0) {
    showToast("Marca al menos una hora con sustituto seleccionado para confirmar.", "warning");
    return;
  }

  const btnTop = document.getElementById("btn-confirmar-todas-top");
  if (btnTop) {
    btnTop.disabled = true;
    btnTop.classList.add("opacity-70", "cursor-not-allowed");
  }

  try {
    const res = await fetch("/api/asignar-sustituciones-multiple", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fecha,
        profesor_ausente_id,
        observaciones,
        asignaciones
      })
    });

    const resultado = await res.json();
    if (resultado.error && (!resultado.asignadas || resultado.asignadas.length === 0)) {
      showToast(resultado.error, "error");
      return;
    }

    const creadas = resultado.asignadas || [];
    const errores = resultado.errores || [];

    if (errores.length > 0) {
      showToast(`Se asignaron ${creadas.length} horas. Hubo ${errores.length} aviso(s): ${errores[0].error}`, "warning");
    } else {
      showToast(`¡${creadas.length} sustituciones registradas correctamente!`, "success");
    }

    mostrarConfirmacionMultiple(creadas, dataMulti.profesor_ausente, fecha);
    await cargarDatosIniciales();

  } catch (err) {
    showToast("Error de red al confirmar las sustituciones.", "error");
    console.error(err);
  } finally {
    if (btnTop) {
      btnTop.disabled = false;
      btnTop.classList.remove("opacity-70", "cursor-not-allowed");
    }
  }
}

function mostrarConfirmacionMultiple(asignadas, profesorAusente, fecha) {
  document.getElementById("panel-resultados").classList.add("hidden");
  document.getElementById("panel-resultados-multiple").classList.add("hidden");

  const confPanel = document.getElementById("panel-confirmacion");
  confPanel.classList.remove("hidden");
  scrollToPanelMobile(confPanel);

  document.getElementById("conf-modo-unico").classList.add("hidden");
  const modoMulti = document.getElementById("conf-modo-multiple");
  modoMulti.classList.remove("hidden");

  document.getElementById("conf-badge-superior").textContent = `${asignadas.length} Horas Registradas`;
  document.getElementById("conf-titulo").textContent = `¡${asignadas.length} Sustituciones Asignadas!`;
  document.getElementById("conf-resumen").textContent =
    `Ausencia de ${profesorAusente.nombre} el ${formatFechaEsp(fecha)}. Envía el correo individual y marca en Calendar cada hora a continuación:`;

  const lista = document.getElementById("lista-confirmacion-multiple");
  lista.innerHTML = "";

  asignadas.forEach((item, idx) => {
    const r = item.record;
    const card = document.createElement("div");
    card.className = "p-4 rounded-2xl border border-slate-200 bg-slate-50/70 hover:bg-white transition shadow-2xs space-y-3";

    card.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2.5">
          <span class="px-2.5 py-1 rounded-xl bg-[#132a56] text-white font-extrabold text-xs">
            ${r.periodo_nombre} (${item.hora_inicio || ''}-${item.hora_fin || ''})
          </span>
          <div>
            <div class="text-sm font-extrabold text-slate-900 flex items-center gap-1.5">
              <i class="ph-fill ph-user-check text-emerald-600"></i>
              <span>${r.profesor_sustituto_nombre}</span>
            </div>
            <div class="text-[11px] text-slate-500">
              Aula <strong>${r.aula}</strong> ${r.materia ? '· ' + r.materia : ''}
              ${r.profesor_sustituto_email ? `· <span class="text-indigo-600 font-semibold">${r.profesor_sustituto_email}</span>` : ''}
            </div>
          </div>
        </div>
        <span id="status-pill-${idx}" class="text-[10px] font-bold text-slate-500 bg-white px-2.5 py-1 rounded-lg border border-slate-200">
          Pendiente de notificar
        </span>
      </div>

      <!-- Botones individuales para este profesor sustituto y esta hora -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <a
          href="${item.calendar_url}"
          target="_blank"
          rel="noopener noreferrer"
          onclick="marcarAccionEnviada(${idx}, 'cal', this)"
          class="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-xs transition cursor-pointer"
        >
          <i class="ph-bold ph-calendar-plus text-sm"></i>
          <span>1. Marcar en Calendar (+ invitación)</span>
        </a>

        <a
          href="${item.email_url}"
          onclick="marcarAccionEnviada(${idx}, 'mail', this)"
          class="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-violet-600 hover:bg-violet-700 text-white font-bold text-xs shadow-xs transition cursor-pointer"
        >
          <i class="ph-bold ph-envelope-simple text-sm"></i>
          <span>2. Enviar Correo Individual</span>
        </a>

        <a
          href="${item.whatsapp_url}"
          target="_blank"
          rel="noopener noreferrer"
          onclick="marcarAccionEnviada(${idx}, 'wa', this)"
          class="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs transition cursor-pointer"
        >
          <i class="ph-bold ph-whatsapp-logo text-sm"></i>
          <span>WhatsApp Individual</span>
        </a>
      </div>
    `;

    lista.appendChild(card);
  });
}

function marcarAccionEnviada(idx, tipo, btnEl) {
  if (btnEl) {
    btnEl.classList.add("ring-2", "ring-emerald-400", "opacity-90");
    if (!btnEl.dataset.clicked) {
      btnEl.dataset.clicked = "1";
      btnEl.innerHTML += ` <i class="ph-bold ph-check text-amber-300"></i>`;
    }
  }
  const pill = document.getElementById(`status-pill-${idx}`);
  if (pill) {
    pill.className = "text-[10px] font-extrabold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200";
    pill.innerHTML = `<i class="ph-bold ph-check"></i> Abierto / Notificado`;
  }
}

function asignarRecomendado() {
  if (appState.ultimoResultadoBusqueda && appState.ultimoResultadoBusqueda.recomendado) {
    asignarCandidato(appState.ultimoResultadoBusqueda.recomendado.profesor.id);
  }
}

// ===============================================
// ASIGNACIÓN INDIVIDUAL (1 HORA), CALENDAR, WHATSAPP Y CORREO
// ===============================================

async function asignarCandidato(profesorSustitutoId, btnTrigger = null) {
  const fecha = document.getElementById("input-fecha").value;
  const periodo_id = (appState.tramosSeleccionados && appState.tramosSeleccionados[0]) || document.getElementById("select-tramo").value;
  const profesor_ausente_id = document.getElementById("select-profesor-ausente").value;
  const aula = document.getElementById("input-aula").value || "Aula asignada";
  const curso_grupo = document.getElementById("input-grupo").value;
  const materia = document.getElementById("input-materia").value;
  const observaciones = document.getElementById("input-observaciones").value;

  if (btnTrigger) {
    btnTrigger.disabled = true;
    btnTrigger.classList.add("opacity-70", "cursor-not-allowed");
  }

  try {
    const res = await fetch("/api/asignar-sustitucion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fecha,
        periodo_id,
        profesor_ausente_id,
        profesor_sustituto_id: profesorSustitutoId,
        aula,
        curso_grupo,
        materia,
        observaciones
      })
    });

    const data = await res.json();
    if (data.error) {
      showToast(data.error, "error");
      if (btnTrigger) {
        btnTrigger.disabled = false;
        btnTrigger.classList.remove("opacity-70", "cursor-not-allowed");
      }
      return;
    }

    appState.ultimaSustitucionAsignada = data;
    showToast(`Sustitución asignada a ${data.record.profesor_sustituto_nombre}`, "success");

    // Mostrar panel de confirmación en modo 1 hora
    document.getElementById("panel-resultados").classList.add("hidden");
    document.getElementById("panel-resultados-multiple").classList.add("hidden");
    const confPanel = document.getElementById("panel-confirmacion");
    confPanel.classList.remove("hidden");
    scrollToPanelMobile(confPanel);

    document.getElementById("conf-modo-multiple").classList.add("hidden");
    document.getElementById("conf-modo-unico").classList.remove("hidden");

    const r = data.record;
    document.getElementById("conf-badge-superior").textContent = "Registrada Correctamente";
    document.getElementById("conf-titulo").textContent = "¡Sustitución Asignada!";
    document.getElementById("conf-resumen").textContent = 
      `${r.profesor_sustituto_nombre} cubrirá a ${r.profesor_ausente_nombre} el ${formatFechaEsp(r.fecha)} en ${r.periodo_nombre} (${r.aula}${r.materia ? ' · ' + r.materia : ''}).`;

    document.getElementById("btn-calendar").href = data.calendar_url;
    document.getElementById("btn-whatsapp").href = data.whatsapp_url;

    const btnEmail = document.getElementById("btn-email");
    if (btnEmail) {
      btnEmail.href = data.email_url || "#";
      const lblEmail = document.getElementById("btn-email-sub");
      if (lblEmail && r.profesor_sustituto_email) {
        lblEmail.textContent = r.profesor_sustituto_email;
      }
    }

    document.getElementById("btn-ics").href = data.ics_url;
    document.getElementById("pre-whatsapp").textContent = data.whatsapp_text;

    await cargarDatosIniciales();

  } catch (err) {
    showToast("Error de red al registrar la sustitución", "error");
    console.error(err);
    if (btnTrigger) {
      btnTrigger.disabled = false;
      btnTrigger.classList.remove("opacity-70", "cursor-not-allowed");
    }
  }
}

function nuevaSustitucion() {
  document.getElementById("panel-confirmacion").classList.add("hidden");
  document.getElementById("panel-resultados").classList.add("hidden");
  document.getElementById("panel-resultados-multiple").classList.add("hidden");
  document.getElementById("panel-inicial").classList.remove("hidden");
  
  const fechaActual = document.getElementById("input-fecha").value;
  
  appState.tramosSeleccionados = [];
  const selectTramo = document.getElementById("select-tramo");
  if (selectTramo) selectTramo.value = "";
  actualizarPillsTramo();
  document.getElementById("select-profesor-ausente").value = "";
  limpiarCamposActividad();
  document.getElementById("input-observaciones").value = "";

  if (fechaActual) {
    document.getElementById("input-fecha").value = fechaActual;
    actualizarEtiquetaDiaSemana();
  }
}

function copiarMensajeWA() {
  const texto = document.getElementById("pre-whatsapp").textContent;
  navigator.clipboard.writeText(texto).then(() => {
    showToast("Mensaje copiado al portapapeles", "info");
  });
}

// ===============================================
// PESTAÑA 2: VISOR DE CUADRANTE Y HORARIOS
// ===============================================

async function cargarHorariosSemana() {
  try {
    const etapaParam = window.ETAPA_ACTIVA ? `?etapa=${encodeURIComponent(window.ETAPA_ACTIVA)}` : "";
    if (!appState.horarios || appState.horarios.length === 0) {
      const res = await fetch(`/api/horarios${etapaParam}`);
      appState.horarios = await res.json();
    }
    const filtroActual = document.getElementById("select-filtro-profesor")?.value || "todos";
    renderHorarioProfesor(filtroActual);
  } catch (err) {
    console.error("Error al cargar horarios:", err);
  }
}

function renderHorarioProfesor(filtroProfesorId) {
  const tbody = document.getElementById("tbody-horarios");
  if (!tbody) return;
  tbody.innerHTML = "";

  const checkSoloGuardias = document.getElementById("check-solo-guardias");
  const verSustitutosDisponibles = checkSoloGuardias ? checkSoloGuardias.checked : true;

  const dias = [0, 1, 2, 3, 4]; // Lunes a Viernes
  const etapaActual = window.ETAPA_ACTIVA || "Primaria";

  // Indexar horarios por (dia, periodo, profesor_id)
  const mapaHorario = {};
  (appState.horarios || []).forEach(h => {
    mapaHorario[`${h.dia_semana}_${h.periodo_id}_${h.profesor_id}`] = h;
  });

  // Filtrar estrictamente solo los tramos de la etapa activa
  const tramosEtapa = (appState.tramos || []).filter(t => !t.etapa || t.etapa === etapaActual);

  tramosEtapa.forEach(tramo => {
    const tr = document.createElement("tr");
    tr.className = tramo.es_recreo ? "bg-amber-50/50" : "hover:bg-slate-50/60 transition";

    let html = `
      <td class="p-3.5 border-r border-slate-200 font-bold text-slate-900 bg-slate-50/70">
        <div class="text-xs font-extrabold text-[#132a56]">${tramo.nombre}</div>
        <div class="text-[10px] text-slate-500 font-semibold mt-0.5">${tramo.hora_inicio} - ${tramo.hora_fin}</div>
      </td>
    `;

    dias.forEach(dia => {
      if (tramo.es_recreo) {
        html += `<td class="p-2.5 border-r border-slate-200 text-center text-[11px] font-bold text-amber-700/70 italic">☕ Recreo</td>`;
        return;
      }

      html += `<td class="p-2.5 border-r border-slate-200 align-top">`;

      // CASO A: Vista de un profesor concreto
      if (filtroProfesorId !== "todos") {
        const act = mapaHorario[`${dia}_${tramo.id}_${filtroProfesorId}`];
        if (act && act.tipo_actividad === "LECTIVA") {
          html += `
            <div class="p-2.5 rounded-xl border border-indigo-200 bg-indigo-50/70 text-indigo-950 shadow-2xs">
              <div class="text-[10px] font-extrabold uppercase text-indigo-600">🔴 Clase Lectiva</div>
              <div class="font-extrabold text-xs mt-0.5">${act.materia || 'Clase'}</div>
              <div class="text-[11px] font-semibold text-indigo-800 mt-0.5">Aula: ${act.aula || '-'}</div>
            </div>
          `;
        } else if (act && act.tipo_actividad === "NO_DISPONIBLE") {
          html += `
            <div class="p-2 rounded-xl border border-slate-200 bg-slate-100 text-slate-400 text-[11px] text-center">
              ⚪ No disponible
            </div>
          `;
        } else {
          html += `
            <div class="p-2.5 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-950 shadow-2xs">
              <div class="text-[10px] font-extrabold uppercase text-emerald-700">🟢 Disponible Sustitución</div>
              <div class="text-[11px] font-bold mt-0.5">Hueco libre</div>
            </div>
          `;
        }
        html += `</td>`;
        return;
      }

      // CASO B: Vista Global -> Sustitutos Disponibles ordenados internamente
      if (verSustitutosDisponibles) {
        const disponiblesEnTramo = [];
        const profsEtapa = (appState.profesores || []).filter(p => !p.etapa || p.etapa === etapaActual);
        profsEtapa.forEach(prof => {
          const act = mapaHorario[`${dia}_${tramo.id}_${prof.id}`];
          if (!act || act.tipo_actividad === "DISPONIBLE" || act.tipo_actividad === "GUARDIA_AULA") {
            const pInfo = ORDEN_PRIORIDAD[prof.id] || { orden: 99, nivel: "Disp.", badge: "bg-slate-100 text-slate-700 border-slate-200", icon: "•" };
            disponiblesEnTramo.push({ prof, pInfo });
          }
        });

        disponiblesEnTramo.sort((a, b) => a.pInfo.orden - b.pInfo.orden);

        html += `<div class="space-y-1.5">`;
        disponiblesEnTramo.forEach(item => {
          html += `
            <div class="px-2.5 py-1.5 rounded-xl border border-emerald-200/80 bg-emerald-50/70 text-emerald-950 text-[11px] flex items-center justify-between gap-1 shadow-2xs">
              <span class="truncate font-semibold">${item.prof.nombre}</span>
              <span class="text-[9px] px-1.5 py-0.2 rounded bg-white/80 text-emerald-800 font-extrabold shrink-0 border border-emerald-200/60">Disponible</span>
            </div>
          `;
        });
        html += `</div>`;
      } else {
        // Mostrar todas las clases lectivas de ese día y hora
        const clases = (appState.horarios || []).filter(h => h.dia_semana === dia && h.periodo_id === tramo.id && h.tipo_actividad === "LECTIVA");
        html += `<div class="space-y-1 max-h-48 overflow-y-auto pr-1">`;
        clases.forEach(c => {
          const prof = appState.profesores.find(p => p.id === c.profesor_id);
          html += `
            <div class="px-2 py-1 rounded-lg border border-slate-200 bg-slate-50 text-[10px]">
              <div class="font-bold text-indigo-900 flex justify-between">
                <span>${c.aula}</span>
                <span class="text-slate-500 font-normal truncate max-w-[90px]">${c.materia}</span>
              </div>
              <div class="text-slate-600 truncate">${prof ? prof.nombre : c.profesor_id}</div>
            </div>
          `;
        });
        html += `</div>`;
      }

      html += `</td>`;
    });

    tr.innerHTML = html;
    tbody.appendChild(tr);
  });
}

// ===============================================
// PESTAÑA 3: HISTORIAL Y BALANCE DE CARGA
// ===============================================

function renderEstadisticas() {
  const grid = document.getElementById("grid-estadisticas");
  if (!grid) return;
  grid.innerHTML = "";

  // Conteo directo y reactivo de sustituciones activas
  const conteoReal = {};
  (appState.sustituciones || []).forEach(sub => {
    if (sub.estado !== "CANCELADA" && sub.profesor_sustituto_id) {
      const pid = sub.profesor_sustituto_id.toLowerCase();
      conteoReal[pid] = (conteoReal[pid] || 0) + 1;
      // Normalización de alias
      if (pid === "colivares") conteoReal["jos7"] = (conteoReal["jos7"] || 0) + 1;
      if (pid === "cdue1") conteoReal["cduerto"] = (conteoReal["cduerto"] || 0) + 1;
    }
  });

  // Asegurar que las estadísticas reflejen exactamente el conteo real
  (appState.estadisticas || []).forEach(s => {
    const pid = s.id ? s.id.toLowerCase() : "";
    if (conteoReal[pid] !== undefined) {
      s.sustituciones = conteoReal[pid];
    }
  });

  const maxSust = Math.max(1, ...appState.estadisticas.map(s => s.sustituciones || 0));

  // Ordenar por mayor número de sustituciones y luego por orden de prioridad
  const ordenadas = [...appState.estadisticas].sort((a, b) => {
    if (b.sustituciones !== a.sustituciones) return b.sustituciones - a.sustituciones;
    const oa = ORDEN_PRIORIDAD[a.id]?.orden || 99;
    const ob = ORDEN_PRIORIDAD[b.id]?.orden || 99;
    return oa - ob;
  });

  ordenadas.forEach(s => {
    const pct = Math.round(((s.sustituciones || 0) / maxSust) * 100);
    const pInfo = ORDEN_PRIORIDAD[s.id];
    const card = document.createElement("div");
    card.className = "bg-slate-50/80 hover:bg-white border border-slate-200/90 rounded-2xl p-3.5 transition shadow-2xs flex flex-col justify-between gap-2";
    card.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-9 h-9 rounded-xl ${s.sustituciones > 0 ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600'} font-extrabold text-xs flex items-center justify-center shrink-0">
            ${obtenerIniciales(s.nombre)}
          </div>
          <div class="min-w-0">
            <div class="text-xs font-extrabold text-slate-900 truncate">${s.nombre}</div>
            <div class="text-[10px] text-slate-500 flex items-center gap-1">
              <span>${s.departamento || 'Primaria'}</span>
            </div>
          </div>
        </div>
        <div class="text-right shrink-0">
          <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-extrabold ${s.sustituciones > 0 ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 'bg-slate-200/70 text-slate-500'}">
            ${s.sustituciones}
          </span>
        </div>
      </div>
      <div class="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden">
        <div class="bg-gradient-to-r from-indigo-500 to-emerald-500 h-full rounded-full transition-all duration-500" style="width: ${s.sustituciones > 0 ? Math.max(12, pct) : 0}%"></div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function filtrarHistorial() {
  renderHistorial();
}

function limpiarFiltrosHistorial() {
  const fText = document.getElementById("filtro-historial-texto");
  const fFecha = document.getElementById("filtro-historial-fecha");
  if (fText) fText.value = "";
  if (fFecha) fFecha.value = "";
  renderHistorial();
}

async function renderHistorial() {
  try {
    const etapaParam = window.ETAPA_ACTIVA ? `?etapa=${encodeURIComponent(window.ETAPA_ACTIVA)}` : "";
    const res = await fetch(`/api/sustituciones${etapaParam}`);
    const data = await res.json();
    appState.sustituciones = data;

    actualizarKPIs();
    actualizarSustitucionesDelDia();

    const fTextEl = document.getElementById("filtro-historial-texto");
    const fFechaEl = document.getElementById("filtro-historial-fecha");
    const qTexto = fTextEl ? fTextEl.value.trim().toLowerCase() : "";
    const qFecha = fFechaEl ? fFechaEl.value.trim() : "";

    let filtradas = data;
    if (qTexto) {
      filtradas = filtradas.filter(sub => 
        (sub.profesor_ausente_nombre && sub.profesor_ausente_nombre.toLowerCase().includes(qTexto)) ||
        (sub.profesor_sustituto_nombre && sub.profesor_sustituto_nombre.toLowerCase().includes(qTexto)) ||
        (sub.aula && sub.aula.toLowerCase().includes(qTexto)) ||
        (sub.materia && sub.materia.toLowerCase().includes(qTexto)) ||
        (sub.curso_grupo && sub.curso_grupo.toLowerCase().includes(qTexto))
      );
    }
    if (qFecha) {
      filtradas = filtradas.filter(sub => sub.fecha === qFecha);
    }

    const badgeTotal = document.getElementById("total-sustituciones-badge");
    if (badgeTotal) {
      badgeTotal.textContent = `${filtradas.length} de ${data.length} registros`;
    }

    const tbody = document.getElementById("tbody-historial");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (filtradas.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="p-8 text-center text-xs text-slate-400">
            <i class="ph-duotone ph-folder-open text-2xl block mx-auto mb-1 text-slate-300"></i>
            No hay sustituciones registradas con los filtros seleccionados.
          </td>
        </tr>`;
      return;
    }

    filtradas.forEach(sub => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50/90 transition";
      tr.innerHTML = `
        <td class="p-3.5">
          <div class="font-extrabold text-slate-900">${formatFechaEsp(sub.fecha)}</div>
          <span class="inline-block mt-0.5 text-[10px] bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded-md border border-indigo-100">${sub.periodo_nombre}</span>
        </td>
        <td class="p-3.5">
          <div class="font-bold text-rose-700 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            <span>${sub.profesor_ausente_nombre}</span>
          </div>
        </td>
        <td class="p-3.5">
          <div class="font-extrabold text-emerald-700 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>${sub.profesor_sustituto_nombre}</span>
          </div>
          <div class="text-[10px] text-slate-400 pl-3.5">${sub.profesor_sustituto_email || ''}</div>
        </td>
        <td class="p-3.5">
          <div class="font-bold text-slate-800">${sub.aula} ${sub.curso_grupo && sub.curso_grupo !== sub.aula ? '(' + sub.curso_grupo + ')' : ''}</div>
          <div class="text-[11px] text-slate-500">${sub.materia || ''}</div>
        </td>
        <td class="p-3.5 text-center">
          <div class="flex items-center justify-center gap-1.5">
            ${sub.calendar_url ? `
              <a href="${sub.calendar_url}" target="_blank" title="Añadir a Google Calendar e invitar por email" class="p-2 rounded-xl bg-blue-50 hover:bg-blue-600 text-blue-600 hover:text-white transition">
                <i class="ph-bold ph-calendar-plus text-sm"></i>
              </a>
            ` : ''}
            ${sub.whatsapp_url ? `
              <a href="${sub.whatsapp_url}" target="_blank" title="Avisar por WhatsApp" class="p-2 rounded-xl bg-emerald-50 hover:bg-emerald-600 text-emerald-600 hover:text-white transition">
                <i class="ph-bold ph-whatsapp-logo text-sm"></i>
              </a>
            ` : ''}
            ${sub.email_url ? `
              <a href="${sub.email_url}" title="Enviar correo" class="p-2 rounded-xl bg-violet-50 hover:bg-violet-600 text-violet-600 hover:text-white transition">
                <i class="ph-bold ph-envelope-simple text-sm"></i>
              </a>
            ` : ''}
            <a href="/api/descargar-ics/${sub.id}" title="Descargar archivo .ics" class="p-2 rounded-xl bg-slate-100 hover:bg-slate-700 text-slate-600 hover:text-white transition">
              <i class="ph-bold ph-download-simple text-sm"></i>
            </a>
            <button onclick="eliminarSustitucion('${sub.id}')" title="Anular sustitución" class="p-2 rounded-xl bg-rose-50 hover:bg-rose-600 text-rose-600 hover:text-white transition cursor-pointer">
              <i class="ph-bold ph-trash text-sm"></i>
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Error al renderizar historial:", err);
  }
}

async function eliminarSustitucion(id) {
  if (!confirm("¿Deseas anular esta sustitución? Se descontará del balance acumulado del profesor sustituto.")) return;
  try {
    const res = await fetch(`/api/sustituciones/${id}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Sustitución anulada correctamente", "info");
      await cargarDatosIniciales();
    } else {
      const err = await res.json();
      showToast("No se pudo anular: " + (err.error || "Error del servidor"), "error");
    }
  } catch (err) {
    showToast("Error de conexión al intentar anular la sustitución.", "error");
  }
}

// ===============================================
// IMPORTACIÓN DE HORARIOS JSON
// ===============================================

function cargarEjemploJSON() {
  const ejemplo = {
    "profesores": [
      {
        "id": "ipena",
        "nombre": "Feli Priego",
        "telefono": "",
        "email": "felicitacionpriego@sanbuenaventura.org",
        "departamento": "Primaria",
        "etapa": "Primaria",
        "activo": true,
        "sustituciones_realizadas": 0
      }
    ],
    "horarios": [
      {
        "profesor_id": "ipena",
        "dia_semana": 0,
        "periodo_id": "1H",
        "tipo_actividad": "LECTIVA",
        "aula": "6ºEP-A",
        "materia": "Religión",
        "descripcion": "Religión en 6ºEP-A"
      }
    ]
  };
  document.getElementById("textarea-importar").value = JSON.stringify(ejemplo, null, 2);
}

async function ejecutarImportacion() {
  const contenido = document.getElementById("textarea-importar").value.trim();
  if (!contenido) {
    showToast("Introduce los datos en formato JSON.", "warning");
    return;
  }

  try {
    const datosJSON = JSON.parse(contenido);
    const res = await fetch("/api/importar-horarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datosJSON)
    });

    const resultado = await res.json();
    if (resultado.success) {
      showToast(`Horarios actualizados (${resultado.total_profesores} docentes)`, "success");
      appState.horarios = [];
      await cargarDatosIniciales();
      switchTab("horarios");
    } else {
      showToast("Error en la importación: " + (resultado.error || "Formato incorrecto"), "error");
    }
  } catch (err) {
    showToast("El JSON no es válido: " + err.message, "error");
  }
}
