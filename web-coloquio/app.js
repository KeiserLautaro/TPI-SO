//! app.js - Motor de simulación TPI-SO PWA
//!=================================================================
//! Motor de simulación replicado desde Python (constantes.py, memoria.py,
//! planificador.py, simulacion.py) - JavaScript Vanilla, sin frameworks.
//!=================================================================

// ==========================================
// CONSTANTES DEL SISTEMA (replicadas desde constantes.py)
// ==========================================
const MEMORY_SO = 100;          // K reservados para el Sistema Operativo (direcciones 0 a 99)
const MEMORY_USUARIO = 450;     // K para procesos de usuario (direcciones 100 a 549)
const MEMORY_TOTAL = MEMORY_SO + MEMORY_USUARIO;  // 550K total

const MAX_MULTIPROGRAMACION = 5;  // Ejecución + Listos + Listos/Suspendidos
const MAX_PROCESOS = 10;          // Procesos por simulación

// ==========================================
// ESTADO DE LA SIMULACIÓN
// ==========================================
const estado = {
  t: 0,
  procesos: [],
  nuevos: [],
  listos: [],
  suspendidos: [],
  en_cpu: null,
  terminados: [],
  memoria: [],      // Particiones MVT
  historial_cpu: [], // Id del proceso en CPU en cada instante ejecutado (None = ociosa)
  registro: [],     // Todos los sucesos: {t, texto, alerta}
  inicio_paso: 0,   // Posición en "registro" donde empiezan los sucesos del último paso
  hubo_evento: false,
  pila_estados: [], // Para "Ciclo Anterior"
};

// ==========================================
// REFERENCIAS A ELEMENTOS DEL DOM (se inicializarán después)
// ==========================================

// ==========================================
// FUNCIONES AUXILIARES - MIMICAN EL CÓDIGO PYTHON
// ==========================================

/**
 * Normalizar ID: 'p1' -> 'P1'; un ID solo numérico se convierte en 'P' + número ('3' -> 'P3')
 */
function normalizarId(texto) {
  const idLimpio = texto.trim().toUpperCase();
  if (/^\d+$/.test(idLimpio)) {
    return "P" + parseInt(idLimpio);
  }
  return idLimpio;
}

/**
 * Número dentro del Id, para ordenar 'P2' antes que 'P10'
 * (comparados como texto, 'P10' quedaría antes que 'P2').
 */
function numeroDeId(idProceso) {
  let digitos = "";
  for (const caracter of idProceso) {
    if (caracter >= '0' && caracter <= '9') {
      digitos += caracter;
    }
  }
  if (digitos === "") return 0;
  return parseInt(digitos);
}

/**
 * Orden de llegada: menor tiempo de arribo y, ante empate, menor Id.
 */
function claveOrdenLlegada(proceso) {
  return [proceso.arribo, numeroDeId(proceso.id), proceso.id];
}

/**
 * Menor tiempo restante; ante empate, el que llegó primero.
 */
function claveSRTF(proceso) {
  return [proceso.restante, ...claveOrdenLlegada(proceso)];
}

/**
 * Best-Fit: devuelve la posición del hueco libre más chico en el que entra tamano
 * (Best-Fit), o -1 si no entra en ninguno. Ante empate gana el de menor dirección.
 */
function buscarHuecoBestFit(memoria, tamano) {
  let mejor = -1;
  for (let i = 0; i < memoria.length; i++) {
    const particion = memoria[i];
    if (particion.proceso === null && particion.tamano >= tamano) {
      if (mejor === -1 || particion.tamano < memoria[mejor].tamano) {
        mejor = i;
      }
    }
  }
  return mejor;
}

/**
 * Asigna memoria al proceso con Best-Fit. Devuelve True si pudo, False si no.
 * Mismo comportamiento que memoria.py: al asignar, el hueco se corta al tamaño exacto
 * y el sobrante queda como un hueco aparte. La fragmentación interna es siempre 0K.
 */
function asignarMemoria(memoria, idProceso, tamano) {
  const i = buscarHuecoBestFit(memoria, tamano);
  if (i === -1) return false;

  const hueco = memoria[i];
  const sobrante = hueco.tamano - tamano;
  if (sobrante > 0) {
    const nuevoHueco = {
      inicio: hueco.inicio + tamano,
      tamano: sobrante,
      proceso: null,
    };
    memoria.splice(i + 1, 0, nuevoHueco);
  }
  hueco.tamano = tamano;
  hueco.proceso = idProceso;
  return true;
}

/**
 * Libera la partición del proceso y la une con los huecos libres vecinos.
 * Mismo comportamiento que memoria.py: fusión de huecos libres contiguos.
 */
function liberarMemoria(memoria, idProceso) {
  for (const particion of memoria) {
    if (particion.proceso === idProceso) {
      particion.proceso = null;
      break;
    }
  }

  // Fusionar huecos libres contiguos
  let i = 0;
  while (i < memoria.length - 1) {
    const actual = memoria[i];
    const siguiente = memoria[i + 1];
    if (actual.proceso === null && siguiente.proceso === null) {
      actual.tamano += siguiente.tamano;
      memoria.splice(i + 1, 1);
    } else {
      i++;
    }
  }
}

/**
 * Crear un proceso (mismo diccionario que crear_proceso en simulacion.py)
 */
function crearProceso(idProceso, tamano, arribo, irrupcion) {
  return {
    id: normalizarId(idProceso),
    tamano: tamano,
    arribo: arribo,
    irrupcion: irrupcion,
    restante: irrupcion,
    estado: null,   // None mientras todavía no arribó
    fin: null,      // instante de finalización
  };
}

/**
 * Crear el estado en T=0 (mismo comportamiento que crear_estado en simulacion.py)
 */
function crearEstado(procesos) {
  if (procesos.length === 0) {
    throw new Error("No hay procesos para simular.");
  }

  // Ordenar por llegada (menor arribo, luego menor ID)
  const todos = [...procesos].sort((a, b) => {
    const ordenA = claveOrdenLlegada(a);
    const ordenB = claveOrdenLlegada(b);
    return ordenA[0] - ordenB[0] || ordenA[1] - ordenB[1] || ordenA[2] - ordenB[2];
  });

  const estado = {
    t: 0,
    procesos: todos,
    nuevos: [],
    listos: [],
    suspendidos: [],
    en_cpu: null,
    terminados: [],
    memoria: crearMemoria(),
    historial_cpu: [],
    registro: [],
    inicio_paso: 0,
    hubo_evento: false,
    pila_estados: [],
  };

  // Procesar arribos de T=0
  procesarArribos(estado);
  // Admitir procesos
  admitirProcesos(estado);
  // Planificar CPU
  planificarCPU(estado);

  return estado;
}

/**
 * Crear memoria inicial: un único hueco libre con los 450K de usuario.
 * Mismo comportamiento que crear_memoria en memoria.py.
 */
function crearMemoria() {
  return [{ inicio: MEMORY_SO, tamano: MEMORY_USUARIO, proceso: null }];
}

/**
 * Procesar arribos: los procesos cuyo tiempo de arribo es T pasan a Nuevo.
 * Mismo comportamiento que procesar_arribos en simulacion.py.
 */
function procesarArribos(estado) {
  for (const proceso of estado.procesos) {
    if (proceso.estado === null && proceso.arribo === estado.t) {
      proceso.estado = "Nuevo";
      estado.nuevos.push(proceso);
      estado.hubo_evento = true;
      registrar(estado, `Arriba ${proceso.id} al estado Nuevo (${proceso.tamano}K, TI=${proceso.irrupcion})`);
    }
  }
}

/**
 * Admitir procesos: dos etapas
 * 1. Los Listos/Suspendidos en orden FIFO que ahora entran en algún hueco
 *    reciben memoria y pasan a Listo.
 * 2. Mientras el grado de multiprogramación sea menor a 5, los Nuevos (FIFO)
 *    pasan a Listo si hay hueco, o a Listo/Suspendido si no lo hay.
 * Mismo comportamiento que admitir_procesos en simulacion.py.
 */
function admitirProcesos(estado) {
  const memoria = estado.memoria;

  // Etapa 1: Los suspendidos que ahora entran en memoria
  for (const proceso of [...estado.suspendidos]) {
    if (asignarMemoria(memoria, proceso.id, proceso.tamano)) {
      // Eliminar de suspendidos
      estado.suspendidos = estado.suspendidos.filter(p => p.id !== proceso.id);
      proceso.estado = "Listo";
      estado.listos.push(proceso);
      registrar(estado, `${proceso.id} ya entra en memoria: pasa de Listo y Suspendido a Listo`);
    }
  }

  // Etapa 2: Los Nuevos hasta el límite de multiprogramación
  while (estado.nuevos.length > 0 && gradoMultiprogramacion(estado) < MAX_MULTIPROGRAMACION) {
    const proceso = estado.nuevos[0]; // FIFO - el primero de la lista
    if (asignarMemoria(memoria, proceso.id, proceso.tamano)) {
      // Eliminar de nuevos (shift quita el primero)
      estado.nuevos.shift();
      proceso.estado = "Listo";
      estado.listos.push(proceso);
      registrar(estado, `${proceso.id} es admitido en memoria y pasa a Listo`);
    } else {
      proceso.estado = "Listo y Suspendido";
      estado.suspendidos.push(proceso);
      registrar(estado, `${proceso.id} no entra en memoria: pasa a Listo y Suspendido`);
    }
  }
}

/**
 * Planificar CPU: Aplica SRTF. Mismo comportamiento que planificar_cpu en simulacion.py.
 */
function planificarCPU(estado) {
  const enCPU = estado.en_cpu;
  let mejorListo = null;

  // Encontrar el mejor en listos
  for (const proceso of estado.listos) {
    if (mejorListo === null || claveSRTF(proceso) < claveSRTF(mejorListo)) {
      mejorListo = proceso;
    }
  }

  if (mejorListo === null || mejorListo === enCPU) return;

  if (enCPU !== null) {
    // Expropiación: el que estaba en CPU vuelve a Listos
    enCPU.estado = "Listo";
    estado.listos.push(enCPU);
    registrar(estado, `ALERTA SRTF: ${mejorListo.id} se adelanta: desaloja a ${enCPU.id} (restante ${enCPU.restante}), con restante ${mejorListo.restante}`, true);
    registrar(estado, `${enCPU.id} es desalojado de la CPU y vuelve a Listo (restante ${enCPU.restante} > ${mejorListo.restante} de ${mejorListo.id})`);
  } else {
    // CPU libre: alerta si pasa delante de Listos que llegaron antes
    const salteados = [];
    for (const proceso of estado.listos) {
      if (proceso !== mejorListo && claveOrdenLlegada(proceso) < claveOrdenLlegada(mejorListo)) {
        salteados.push(proceso);
      }
    }
    if (salteados.length > 0) {
      let quienes;
      if (salteados.length === 1) {
        quienes = `${salteados[0].id} (restante ${salteados[0].restante}), que llegó antes`;
      } else {
        const todosMenosUltimo = salteados.slice(0, -1).map(p => p.id);
        quienes = `${todosMenosUltimo.join(', ')} y ${salteados[salteados.length - 1].id} (restante ${salteados[salteados.length - 1].restante}), que llegaron antes`;
      }
      registrar(estado, `ALERTA SRTF: ${mejorListo.id} se adelanta: pasa delante de ${quienes}, con restante ${mejorListo.restante}`, true);
    }
  }

  // Remover de listos y poner en CPU
  estado.listos = estado.listos.filter(p => p !== mejorListo);
  mejorListo.estado = "Ejecución";
  estado.en_cpu = mejorListo;
  registrar(estado, `${mejorListo.id} entra a la CPU (restante ${mejorListo.restante})`);
}

/**
 * Ejecutar una unidad en CPU [T, T+1).
 * Mismo comportamiento que ejecutar_unidad en simulacion.py.
 */
function ejecutarUnidad(estado) {
  const proceso = estado.en_cpu;
  if (proceso === null) {
    estado.historial_cpu.push(null);
    return;
  }

  estado.historial_cpu.push(proceso.id);
  proceso.restante -= 1;

  if (proceso.restante === 0) {
    const fin = estado.t + 1;
    proceso.estado = "Terminado";
    proceso.fin = fin;
    estado.en_cpu = null;
    estado.terminados.push(proceso);
    liberarMemoria(estado.memoria, proceso.id);
    estado.hubo_evento = true;
    registrar(estado, `${proceso.id} termina y libera su partición de ${proceso.tamano}K (retorno ${fin - proceso.arribo}, espera ${fin - proceso.arribo - proceso.irrupcion})`, true);
  }
}

/**
 * Ejecutar un instante (T -> T+1).
 * Mismo comportamiento que ejecutar_instante en simulacion.py.
 * Orden: (1) Ejecución de 1 unidad en CPU, (2) Reloj a T+1, (3) Arribos,
 * (4) Admisión en dos etapas, (5) Planificación SRTF.
 */
function ejecutarInstante(estado) {
  estado.hubo_evento = false;

  // (1) Ejecución de 1 unidad en CPU
  ejecutarUnidad(estado);

  // (2) Reloj a T+1
  estado.t += 1;

  // (3) Arribos
  procesarArribos(estado);

  // (4) Admisión en dos etapas
  admitirProcesos(estado);

  // (5) Planificación SRTF
  planificarCPU(estado);
}

/**
 * Avanza un instante (T -> T+1). No hace nada si la simulación ya terminó.
 * Mismo comportamiento que avanzar_instante en simulacion.py.
 */
function avanzarInstante(estado) {
  if (simulacionTerminada(estado)) return;

  // Guardar estado actual en pila para "Ciclo Anterior"
  estado.pila_estados.push({
    t: estado.t,
    procesos: estado.procesos.map(p => ({
      id: p.id, tamano: p.tamano, arribo: p.arribo, irrupcion: p.irrupcion,
      restante: p.restante, estado: p.estado, fin: p.fin
    })),
    nuevos: estado.nuevos.map(p => ({...p})),
    listos: estado.listos.map(p => ({...p})),
    suspendidos: estado.suspendidos.map(p => ({...p})),
    en_cpu: estado.en_cpu ? {...estado.en_cpu} : null,
    terminados: estado.terminados.map(p => ({...p})),
    memoria: estado.memoria.map(p => ({...p})),
    historial_cpu: [...estado.historial_cpu],
    registro: [...estado.registro],
    inicio_paso: estado.inicio_paso,
    hubo_evento: estado.hubo_evento,
  });

  // Mantener solo los últimos 20 estados en la pila
  if (estado.pila_estados.length > 20) {
    estado.pila_estados.shift();
  }

  ejecutarInstante(estado);
}

/**
 * Avanza hasta el próximo instante en que llega o termina algún proceso.
 * Mismo comportamiento que avanzar_hasta_evento en simulacion.py.
 */
function avanzarHastaEvento(estado) {
  if (simulacionTerminada(estado)) return;

  ejecutarInstante(estado);

  while (!estado.hubo_evento && !simulacionTerminada(estado)) {
    ejecutarInstante(estado);
  }
}

/**
 * Verifica si la simulación terminó.
 */
function simulacionTerminada(estado) {
  return estado.terminados.length === estado.procesos.length;
}

// Método corto para compatibilidad
estado.terminado = simulacionTerminada;

/**
 * Registrar un suceso en el registro.
 */
function registrar(estado, texto, alerta = false, t = null) {
  if (t === null) t = estado.t;
  estado.registro.push({ t, texto, alerta });
}

/**
 * Calcular estadísticas (mismo comportamiento que calcular_estadisticas en simulacion.py)
 */
function calcularEstadisticas(estado) {
  const detalle = [];
  let sumaRetorno = 0;
  let sumaEspera = 0;
  let tiempoTotal = 0;

  // Ordenar por llegada, luego por ID para consistencia
  const terminadosOrdenados = [...estado.terminados].sort((a, b) => {
    const ka = claveOrdenLlegada(a);
    const kb = claveOrdenLlegada(b);
    return ka[0] - kb[0] || a.id.localeCompare(b.id);
  });

  for (const proceso of terminadosOrdenados) {
    const retorno = proceso.fin - proceso.arribo;
    const espera = retorno - proceso.irrupcion;
    sumaRetorno += retorno;
    sumaEspera += espera;
    if (proceso.fin > tiempoTotal) tiempoTotal = proceso.fin;
    detalle.push({
      id: proceso.id,
      tamano: proceso.tamano,
      arribo: proceso.arribo,
      irrupcion: proceso.irrupcion,
      fin: proceso.fin,
      retorno: retorno,
      espera: espera,
    });
  }

  const n = detalle.length;
  if (n === 0) {
    return {
      detalle: [],
      cantidad: 0,
      retorno_promedio: 0.0,
      espera_promedio: 0.0,
      tiempo_total: 0,
      rendimiento: 0.0,
    };
  }

  return {
    detalle: detalle,
    cantidad: n,
    retorno_promedio: sumaRetorno / n,
    espera_promedio: sumaEspera / n,
    tiempo_total: tiempoTotal,
    rendimiento: n / tiempoTotal,
  };
}

/**
 * Calcular grado de multiprogramación.
 * Mismo comportamiento que grado_multiprogramacion en simulacación.py.
 */
function gradoMultiprogramacion(estado) {
  let enCPU = 0;
  if (estado.en_cpu !== null) enCPU = 1;
  return enCPU + estado.listos.length + estado.suspendidos.length;
}

/**
 * Devolver los sucesos del último paso.
 */
function sucesosDelUltimoPaso(estado) {
  return estado.registro.slice(estado.inicio_paso);
}

/**
 * Devolver alertas del último paso.
 */
function alertasDelUltimoPaso(estado) {
  const alertas = [];
  for (const suceso of sucesosDelUltimoPaso(estado)) {
    if (suceso.alerta) alertas.push(suceso);
  }
  return alertas;
}

// ==========================================
// RENDERIZADO EN DOM - FUNCIONES DE ACTUALIZACIÓN
// ==========================================

/**
 * Actualizar toda la interfaz de estado visual.
 */
function actualizarInterfaz() {
  const simulacionTerminada = estado.terminado(estado);

  // 1. Reloj T y estado de botones
  const relojEl = document.getElementById('reloj-t');
  if (relojEl) relojEl.textContent = `T = ${estado.t}`;

  // Botones de control
  const btnPaso = document.getElementById('btn-paso');
  const btnEvento = document.getElementById('btn-evento');
  const btnRetroceder = document.getElementById('btn-retroceder');
  const btnReiniciar = document.getElementById('btn-reiniciar');

  btnPaso.disabled = simulacionTerminada;
  btnEvento.disabled = simulacionTerminada;
  btnRetroceder.disabled = estado.pila_estados.length === 0;
  btnReiniciar.disabled = false;

  // 2. Panel CPU
  const lblCPUActual = document.getElementById('estado-cpu');
  const lblCPURestante = document.getElementById('resto-cpu');
  const lblGrado = document.getElementById('grado');

  if (estado.en_cpu !== null) {
    lblCPUActual.textContent = `Proceso en CPU: ${estado.en_cpu.id}`;
    lblCPUActual.className = 'status-value success';
    lblCPURestante.textContent = `T. Restante: ${estado.en_cpu.restante} u.`;
    lblGrado.textContent = `Grado de multiprogramación: ${gradoMultiprogramacion(estado)} / ${MAX_MULTIPROGRAMACION}`;
  } else {
    lblCPUActual.textContent = 'LIBRE (Ociosa)';
    lblCPUActual.className = 'status-value';
    lblCPURestante.textContent = '-';
    lblGrado.textContent = `Grado de multiprogramación: 0 / ${MAX_MULTIPROGRAMACION}`;
  }

  // 3. Alerta SRTF
  const lblAlertas = document.getElementById('alertas');
  const alertas = alertasDelUltimoPaso(estado);
  if (alertas.length > 0) {
    const textos = alertas.map(a => a.texto);
    lblAlertas.textContent = textos.join(' | ');
    lblAlertas.className = 'status-value warning';
  } else {
    lblAlertas.textContent = '--';
    lblAlertas.className = 'status-value';
  }

  // 4. Visualización de memoria
  actualizarVisualizacionMemoria();

  // 5. Colas de procesos
  actualizarColasProcesos();

  // 6. Registro de sucesos
  actualizarRegistroSucesos();

  // 7. Gantt chart
  actualizarGantt();
}

/**
 * Actualizar visualización de memoria.
 */
function actualizarVisualizacionMemoria() {
  const memoryBar = document.getElementById('memory-bar');
  if (!memoryBar) return;

  // Calcular ancho porcentual para cada partición
  let offset = 0;
  memoryBar.innerHTML = ''; // Limpiar

  // Segmento SO (siempre al inicio, 100K de 550K total = ~18.18%)
  const segmentSO = document.createElement('div');
  segmentSO.className = 'memory-segment so';
  segmentSO.innerHTML = `SO (100K)`;
  const soPorcentaje = (MEMORY_SO / MEMORY_TOTAL) * 100;
  segmentSO.style.width = `${soPorcentaje}%`;
  memoryBar.appendChild(segmentSO);

  // Segmentos de particiones de memoria
  const memoria = estado.memoria;
  for (const particion of memoria) {
    const segment = document.createElement('div');
    segment.className = 'memory-segment';

    // Calcular posición y ancho relativos al área de usuario
    const anchoPorcentaje = (particion.tamano / MEMORY_USUARIO) * 100;
    const posicionPorcentaje = (offset / MEMORY_USUARIO) * 100;

    segment.style.left = `${posicionPorcentaje}%`;
    segment.style.width = `${anchoPorcentaje}%`;

    if (particion.proceso === null) {
      segment.style.background = '#dfe6e9';
      segment.style.color = '#2c3e50';
      segment.innerHTML = `Libre (${particion.tamano}K)`;
    } else {
      segment.style.background = '#3498db';
      segment.style.color = 'white';
      segment.innerHTML = `${particion.proceso} (${particion.tamano}K)`;
    }

    memoryBar.appendChild(segment);
    offset += particion.tamano;
  }
}

/**
 * Actualizar colas de procesos.
 */
function actualizarColasProcesos() {
  // Lista de procesos en Listos (ordenados por SRTF)
  const listosOrdenados = [...estado.listos].sort((a, b) => {
    const kA = claveSRTF(a);
    const kB = claveSRTF(b);
    return kA[0] - kB[0] || kA[1] - kB[1] || kA[2] - kB[2];
  });

  // Actualizar tabla de Listos
  const listosBody = document.querySelector('#tab-listos tbody');
  if (listosBody) {
    listosBody.innerHTML = '';
    if (listosOrdenados.length === 0) {
      listosBody.innerHTML = '<tr><td colspan="6" class="empty-state">Ningún proceso en Listos</td></tr>';
    } else {
      for (const p of listosOrdenados) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${p.id}</td>
          <td class="tamanio">${p.tamano}K</td>
          <td class="arribo">${p.arribo}</td>
          <td class="irrupcion">${p.irrupcion}</td>
          <td>${p.restante}</td>
          <td><span class="estado estado-listo">Listo</span></td>
        `;
        listosBody.appendChild(tr);
      }
    }
  }

  // Actualizar tabla de Listos y Suspendidos
  const suspBody = document.querySelector('#tab-suspendidos tbody');
  if (suspBody) {
    suspBody.innerHTML = '';
    if (estado.suspendidos.length === 0) {
      suspBody.innerHTML = '<tr><td colspan="6" class="empty-state">Ningún proceso en Listos y Suspendidos</td></tr>';
    } else {
      for (const p of estado.suspendidos) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${p.id}</td>
          <td class="tamanio">${p.tamano}K</td>
          <td class="arribo">${p.arribo}</td>
          <td class="irrupcion">${p.irrupcion}</td>
          <td>${p.restante}</td>
          <td><span class="estado estado-suspendido">Listo y Suspendido</span></td>
        `;
        suspBody.appendChild(tr);
      }
    }
  }

  // Actualizar tabla de Nuevos
  const nuevosBody = document.querySelector('#tab-nuevos tbody');
  if (nuevosBody) {
    nuevosBody.innerHTML = '';
    if (estado.nuevos.length === 0) {
      nuevosBody.innerHTML = '<tr><td colspan="6" class="empty-state">Ningún proceso en Nuevo</td></tr>';
    } else {
      for (const p of estado.nuevos) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${p.id}</td>
          <td class="tamanio">${p.tamano}K</td>
          <td class="arribo">${p.arribo}</td>
          <td class="irrupcion">${p.irrupcion}</td>
          <td>-</td>
          <td><span class="estado estado-nuevo">Nuevo</span></td>
        `;
        nuevosBody.appendChild(tr);
      }
    }
  }
}

/**
 * Actualizar log de sucesos.
 */
function actualizarRegistroSucesos() {
  const logContent = document.getElementById('log-content');
  const logEmpty = document.getElementById('log-empty');

  if (!logContent) return;

  const eventosRecientes = sucesosDelUltimoPaso(estado);

  if (eventosRecientes.length === 0) {
    logContent.innerHTML = '';
    if (logEmpty) logEmpty.style.display = 'block';
    return;
  }

  if (logEmpty) logEmpty.style.display = 'none';

  let contenido = '';
  for (const suceso of eventosRecientes) {
    const clase = suceso.alerta ? 'alert' : '';
    contenido += `<div class="${clase}" style="margin: 4px 0; font-family: Consolas, monospace; font-size: 0.75rem;">`;
    contenido += `<span style="color: var(--primary-color);">[T=${suceso.t}]</span> ${suceso.texto}`;
    if (suceso.alerta) {
      contenido += ' <span style="color: var(--danger-color);">[ALERTA]</span>';
    }
    contenido += '</div>';
  }

  logContent.innerHTML = contenido;
}

/**
 * Actualizar diagrama de Gantt.
 */
function actualizarGantt() {
  const ganttCanvas = document.getElementById('gantt-canvas');
  if (!ganttCanvas) return;

  const ctx = ganttCanvas.getContext('2d');
  const historial = estado.historial_cpu;
  const ancho = ganttCanvas.width;
  const alto = ganttCanvas.height;
  const margen = 10;

  // Limpiar canvas
  ctx.clearRect(0, 0, ancho, alto);

  if (historial.length === 0) {
    ctx.fillStyle = '#7f8c8d';
    ctx.font = '10px Consolas';
    ctx.fillText('Sin ejecución aún', margen, 20);
    return;
  }

  const celda = Math.max(1, (ancho - 2 * margen) / historial.length);
  const y0 = 6, y1 = 30;

  let inicio = 0;
  while (inicio < historial.length) {
    let fin = inicio;
    while (fin + 1 < historial.length && historial[fin + 1] === historial[inicio]) {
      fin++;
    }

    const idProceso = historial[inicio];
    const x0 = margen + inicio * celda;
    const x1 = margen + (fin + 1) * celda;

    let color;
    if (idProceso === null) {
      color = '#ffffff'; // CPU ociosa - blanca
    } else {
      // Color basado en el ID del proceso
      const hueso = parseInt(idProceso.replace('P', '')) || 1;
      const r = (hueso * 57 + 13) % 256;
      const g = (hueso * 123 + 71) % 256;
      const b = (hueso * 199 + 31) % 256;
      color = `rgb(${r}, ${g}, ${b})`;
    }

    ctx.fillStyle = color;
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);

    // Etiqueta del proceso
    if (idProceso !== null && (x1 - x0) > 18) {
      ctx.fillStyle = 'white';
      ctx.font = 'bold 8px Consolas';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(idProceso, (x0 + x1) / 2, (y0 + y1) / 2);
    }

    // Marca de tiempo debajo
    ctx.fillStyle = '#2c3e50';
    ctx.font = '7px Consolas';
    ctx.textAlign = 'center';
    ctx.fillText(String(inicio), (x0 + x1) / 2, y1 + 14);

    inicio = fin + 1;
  }

  // Marca final de tiempo
  ctx.fillStyle = '#2c3e50';
  ctx.font = '7px Consolas';
  ctx.textAlign = 'end';
  ctx.fillText(String(historial.length), margen + historial.length * celda - 2, y1 + 14);
}

/**
 * Actualizar tabla de métricas.
 */
function actualizarMetrics() {
  const stats = calcularEstadisticas(estado);
  const procesoCount = estado.procesos.length;
  const terminadosCount = estado.terminados.length;

  // Actualizar tarjetas de métricas globales
  const metricTRP = document.getElementById('metric-trp');
  const metricTEP = document.getElementById('metric-tep');
  const metricRendimiento = document.getElementById('metric-rendimiento');
  const metricTiempo = document.getElementById('metric-tiempo');

  if (metricTRP) metricTRP.textContent = stats.retorno_promedio.toFixed(2);
  if (metricTEP) metricTEP.textContent = stats.espera_promedio.toFixed(2);
  if (metricRendimiento) metricRendimiento.textContent = `${stats.cantidad}/${stats.tiempo_total} = ${stats.rendimiento.toFixed(4)} proc/tiempo`;
  if (metricTiempo) metricTiempo.textContent = stats.tiempo_total;

  // Tabla de procesos con métricas
  const procesoStatsBody = document.getElementById('processes-stats-body');
  if (procesoStatsBody) {
    procesoStatsBody.innerHTML = '';

    for (const d of stats.detalle) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${d.id}</td>
        <td>${d.tamano}K</td>
        <td>${d.arribo}</td>
        <td>${d.irrupcion}</td>
        <td>${d.fin !== undefined ? d.fin : '--'}</td>
        <td class="retorno">${d.retorno}</td>
        <td class="espera">${d.espera}</td>
      `;
      procesoStatsBody.appendChild(tr);
    }
  }

  // Indicadores globales
  const indicadoresGlobales = document.getElementById('indicadores-globales');
  if (indicadoresGlobales) {
    indicadoresGlobales.innerHTML = `
      <p>• Procesos terminados: ${stats.cantidad} de ${procesoCount}</p>
      <p>• Tiempo total: ${stats.tiempo_total} unidades de tiempo</p>
      <p>• Retorno Promedio (TRP): ${stats.retorno_promedio.toFixed(2)} unidades</p>
      <p>• Espera Promedio (TEP): ${stats.espera_promedio.toFixed(2)} unidades</p>
      <p>• Rendimiento del sistema: ${stats.cantidad}/${stats.tiempo_total} = ${stats.rendimiento.toFixed(4)} procesos/tiempo</p>
    `;
  }
}

// ==========================================
// MÓDULO DE CARGA DE LOTES Y PROCESOS
// ==========================================

/**
 * Cargar un lote específico desde la carpeta lotes/
 * Los lotes están en formato CSV con columnas: Proceso,TA,TI,Tamaño
 */
function cargarLote(numeroLote) {
  const ruta = `lotes/lote_${numeroLote}.csv`;
  fetch(ruta)
    .then(response => {
      if (!response.ok) throw new Error('Error al cargar el lote');
      return response.text();
    })
    .then(texto => procesarCSV(texto))
    .then(({procesos}) => {
      // Guardar procesos en el estado
      estado.procesos = procesos;
      // Reiniciar simulación
      reiniciarSimulacionInterna();
      actualizarInterfaz();
    })
    .catch(err => {
      mostrarError(`Error al cargar lote ${numeroLote}: ${err.message}`);
    });
}

/**
 * Procesar contenido CSV y retornar lista de procesos
 */
function procesarCSV(texto) {
  const lineas = [];
  for (const linea of texto.split('\n')) {
    if (linea.trim() !== '') {
      lineas.push(linea);
    }
  }

  const procesos = [];
  let encabezado = true;

  for (const linea of lineas) {
    const campos = separarCSV(linea);
    if (campos.length === 0) continue;

    if (encabezado) {
      // Verificar si tiene encabezado buscando en los nombres de columnas
      const primerCampo = campos[0].toLowerCase().trim();
      const posibleEncabezado = ['proceso', 'id', 'tamaño', 'tamanio', 'memoria', 'ta', 'ti',
        'tiempo_arribo', 'llegada', 'irrupcion', 'tiempo_irrupcion', 'rafaga'];
      encabezado = posibleEncabezado.some(p => primerCampo.includes(p));
      if (encabezado) continue; // Saltar la línea de encabezado
    }

    if (campos.length >= 4) {
      const id = normalizarId(campos[0]);
      const tamano = parseInt(campos[1]);
      const arribo = parseInt(campos[2]);
      const irrupcion = parseInt(campos[3]);

      if (!isNaN(tamano) && !isNaN(arribo) && !isNaN(irrupcion)) {
        procesos.push(crearProceso(id, tamano, arribo, irrupcion));
      }
    }
  }

  return { procesos };
}

/**
 * Separar una línea CSV considerando comas, punto y salto o tabulaciones.
 */
function separarCSV(linea) {
  for (const separador of [';', ',', '\t']) {
    if (linea.includes(separador)) {
      return linea.split(separador).map(c => c.trim());
    }
  }
  return linea.split('').map(c => c.trim());
}

/**
 * Cargar CSV propio desde texto pegado por el usuario
 */
function cargarCSVPropio() {
  const texto = prompt('Pega el contenido CSV de tus procesos (formato: Id,Tamaño,Arribo,Irrupción):\nEjemplo: P1,120,3,2\n(Opcional: incluye encabezado "Proceso,TA,TI,Tamaño" en la primera línea)');
  if (texto) {
    procesarCSV(texto).then(({procesos}) => {
      if (procesos.length > 0) {
        estado.procesos = procesos;
        reiniciarSimulacionInterna();
        actualizarInterfaz();
      } else {
        mostrarError('No se pudieron procesar los procesos del CSV. Verifique el formato.');
      }
    });
  }
}

/**
 * Reiniciar la simulación internamente (sin afectar la pila de estados)
 */
function reiniciarSimulacionInterna() {
  // Limpiar pila de estados para empezar fresco
  estado.pila_estados = [];

  // Crear nuevo estado T=0
  try {
    estado = crearEstado(estado.procesos);
  } catch (e) {
    mostrarError(e.message);
    return;
  }

  // Calcular estadísticas iniciales
  actualizarMetrics();
  actualizarInterfaz();
  actualizarGantt();
}

/**
 * Mostrar mensaje de error en la interfaz
 */
function mostrarError(mensaje) {
  const errorDiv = document.createElement('div');
  errorDiv.style = `
    background: var(--danger-color);
    color: white;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
    text-align: center;
  `;
  errorDiv.textContent = mensaje;

  // Insertar después del header
  const container = document.querySelector('.pwa-container');
  if (container && document.querySelector('#error-place')) {
    document.getElementById('error-place').appendChild(errorDiv);
  } else if (container) {
    // Insertar antes del primer section
    const firstSection = container.querySelector('section');
    if (firstSection) {
      container.insertBefore(errorDiv, firstSection);
    } else {
      container.insertBefore(errorDiv, container.firstChild);
    }
  }
}

// ==========================================
// EVENT LISTENERS - CONTROLES DE SIMULACIÓN
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
  // =======================
  // CONFIGURAR PESTAÑAS
  // =======================
  const tabItems = document.querySelectorAll('.tab-item');
  const pwaSections = document.querySelectorAll('.pwa-section');

  tabItems.forEach(boton => {
    boton.addEventListener('click', function() {
      // Remover clase active de todos los botones
      tabItems.forEach(b => b.classList.remove('active'));
      // Remover clase active de todas las secciones
      pwaSections.forEach(s => s.classList.remove('active'));

      // Activar el botón clickeado
      this.classList.add('active');
      // Activar el contenido correspondiente
      const tabId = this.getAttribute('data-tab');
      document.getElementById(tabId).classList.add('active');
    });
  });

  // =======================
  // CARGAR MÓDULOS Y DIAGRAMAS AL INICIAR
  // =======================
  // Cargar información de los módulos Python
  cargarModulosInfo();

  // Cargar diagrama de ciclo de vida
  cargarDiagramaCicloVida();

  // =======================
  // CONFIGURAR CONTROLES DE SIMULACIÓN
  // =======================
  const btnInicio = document.getElementById('btn-reiniciar');
  const btnPaso = document.getElementById('btn-paso');
  const btnEvento = document.getElementById('btn-evento');
  const btnRetroceder = document.getElementById('btn-retrocedor');
  const btnLote1 = document.getElementById('btn-lote-1');
  const btnLote2 = document.getElementById('btn-lote-2');
  const btnLote3 = document.getElementById('btn-lote-3');
  const btnLote4 = document.getElementById('btn-lote-4');
  const btnLote5 = document.getElementById('btn-lote-5');
  const btnLote6 = document.getElementById('btn-lote-6');
  const btnCSVPropio = document.getElementById('btn-csv-proprio');

  // Event listeners para botones de simulación
  if (btnInicio) btnInicio.addEventListener('click', () => {
    if (estado.procesos.length === 0) {
      alert('Primeme primero cargue un lote o agregue procesos.');
      return;
    }
    reiniciarSimulacionInterna();
  });

  if (btnPaso) btnPaso.addEventListener('click', () => {
    if (estado.terminado(estado)) return;
    avanzarInstante(estado);
    actualizarInterfaz();
    actualizarMetrics();
    actualizarGantt();
  });

  if (btnEvento) btnEvento.addEventListener('click', () => {
    if (estado.terminado(estado)) return;
    avanzarHastaEvento(estado);
    actualizarInterfaz();
    actualizarMetrics();
    actualizarGantt();
  });

  if (btnRetroceder) btnRetrocedor.addEventListener('click', () => {
    if (estado.pila_estados.length === 0) return;
    const estadoAnterior = estado.pila_estados.pop();
    // Restaurar estado desde la pila
    Object.assign(estado, estadoAnterior);
    actualizarInterfaz();
    actualizarMetrics();
    actualizarGantt();
  });

  if (btnLote1) btnLote1.addEventListener('click', () => cargarLote(1));
  if (btnLote2) btnLote2.addEventListener('click', () => cargarLote(2));
  if (btnLote3) btnLote3.addEventListener('click', () => cargarLote(3));
  if (btnLote4) btnLote4.addEventListener('click', () => cargarLote(4));
  if (btnLote5) btnLote5.addEventListener('click', () => cargarLote(5));
  if (btnLote6) btnLote6.addEventListener('click', () => cargarLote(6));

  if (btnCSVPropio) btnCSVPropio.addEventListener('click', cargarCSVPropio);

  // =======================
  // FLASHCARDS LOGIC
  // =======================
  const flashcardOptions = document.querySelectorAll('.flashcard-option');
  const flashcardContainer = document.getElementById('flashcard-container');
  const noFlashcards = document.getElementById('no-flashcards');
  const flashcardQuestion = document.getElementById('flashcard-question');
  const flashcardAnswer = document.getElementById('flashcard-answer');
  const flashcardCounter = document.getElementById('flashcard-counter');
  const btnPrev = document.getElementById('btn-prev');
  const btnNext = document.getElementById('btn-next');
  const btnReveal = document.getElementById('btn-reveal');

  // Datos de flashcards basados en los lotes y casos borde
  const flashcardsData = {
    lote1: [
      {
        pregunta: "¿Qué pasa en el instante T=0 cuando se crean procesos que llegan al mismo tiempo?",
        respuesta: "Los procesos con el mismo tiempo de arribo se ordenan por ID numérico (P2 antes que P10). El grado de multiprogramación cuenta desde T=0."
      },
      {
        pregunta: "¿Por qué la fragmentación interna en MVT es siempre 0K?",
        respuesta: "Porque en MVT cada partición se corta exactamente al tamaño del proceso, no hay espacio desperdiciado dentro de una partición asignada."
      },
      {
        pregunta: "¿Qué significa el grado de multiprogramación máximo de 5?",
        respuesta: "Ejecución + Listos + Listos/Suspendidos no puede superar 5 procesos activos simultáneos. Los procesos adicionales esperan en estado Nuevo o Listo/Suspendido."
      }
    ],
    lote2: [
      {
        pregunta: "¿Por qué en el Lote 2 hay procesos en estado Listo y Suspendido al empezar?",
        respuesta: "Porque los procesos P4 y P5 (tamaño 140K y 180K) no caben en memoria de 450K al instante T=0, por lo que van a Listo y Suspendidos esperando entrar en un hueco libre."
      },
      {
        pregunta: "¿Qué ocurre cuando un proceso en Listo y Suspendido entra en memoria?",
        respuesta: "Recibe memoria, pasa a estado Listo y se mueve a la cola de Listos, consumiendo cupo del grado de multiprogramación."
      },
      {
        pregunta: "¿Cuál es la diferencia entre Listo y Listo y Suspendido?",
        respuesta: "Listo significa que el proceso está en memoria y esperando CPU. Listo y Suspendido significa que está fuera de memoria (en disco) y debe entrar en un hueco para poder ejecutarse."
      }
    ],
    lote4: [
      {
        pregunta: "¿Qué es una expropiación en SRTF y cuándo ocurre?",
        respuesta: "La expropiación es cuando el proceso en CPU es desplazado por otro de menor tiempo restante. Ocurre cuando un nuevo proceso llega con restante estrictamente menor que el actual, o cuando un Listo tiene restante menor y llegó antes."
      },
      {
        pregunta: "¿Por qué SRTF es llamado planificación expropiativa?",
        respuesta: "Porque el sistema puede quitar la CPU a un proceso en ejecución si otro proceso tiene un tiempo restante menor, asegurando que siempre ejecute el trabajo más corto."
      },
      {
        pregunta: "¿Cuál es la regla de desempate en SRTF cuando hay empate en tiempo restante?",
        respuesta: "Gana el proceso que llegó primero (menor tiempo de arribo). Si también empatan en arribo, gana el de menor ID numérico (P2 antes que P10)."
      }
    ]
  };

  // Estado de flashcards
  let flashcardsActuales = [];
  let indiceActual = 0;

  // Cargar un conjunto de flashcards
  function cargarConjunto(loteKey) {
    flashcardsActuales = flashcardsData[loteKey] || [];
    indiceActual = 0;
    mostrarFlashcard();
  }

  // Mostrar flashcard actual
  function mostrarFlashcard() {
    if (flashcardsActuales.length === 0) {
      if (flashcardContainer) flashcardContainer.style.display = 'none';
      if (noFlashcards) noFlashcards.style.display = 'block';
      return;
    }

    if (noFlashcards) noFlashcards.style.display = 'none';
    if (flashcardContainer) flashcardContainer.style.display = 'block';

    const actual = flashcardsActuales[indiceActual];

    if (flashcardQuestion) {
      flashcardQuestion.innerHTML = `
        <div class="panel-header">
          <h4>Pregunta</h4>
          <span class="panel-close" aria-label="Cerrar">×</span>
        </div>
        <div class="panel-body">
          ${actual.pregunta}
        </div>
      `;
      // Añadir evento para cerrar panel
      const closeBtn = flashcardQuestion.querySelector('.panel-close');
      if (closeBtn) {
        closeBtn.onclick = () => {
          flashcardQuestion.style.display = 'none';
          flashcardAnswer.style.display = 'none';
        };
      }
    }

    if (flashcardCounter) {
      flashcardCounter.textContent = `${indiceActual + 1} / ${flashcardsActuales.length}`;
    }
  }

  // Reveal answer
  function revelarRespuesta() {
    if (flashcardsActuales.length === 0) return;

    flashcardAnswer.style.display = 'block';
    const actual = flashcardsActuales[indiceActual];
    if (flashcardAnswer.querySelector('.panel-body')) {
      flashcardAnswer.querySelector('.panel-body').textContent = actual.respuesta;
    }
    if (btnReveal) btnReveal.textContent = 'Cerrar';
  }

  // Next flashcard
  function siguienteFlashcard() {
    if (flashcardsActuales.length === 0) return;
    indiceActual = (indiceActual + 1) % flashcardsActuales.length;
    mostrarFlashcard();
    // Ocultar respuesta anterior si está visible
    if (flashcardAnswer && flashcardAnswer.style.display !== 'none') {
      flashcardAnswer.style.display = 'none';
      if (btnReveal) btnReveal.textContent = 'Revelar Respuesta';
    }
  }

  // Previous flashcard
  function anteriorFlashcard() {
    if (flashcardsActuales.length === 0) return;
    indiceActual = (indiceActual - 1 + flashcardsActuales.length) % flashcardsActuales.length;
    mostrarFlashcard();
    if (flashcardAnswer && flashcardAnswer.style.display !== 'none') {
      flashcardAnswer.style.display = 'none';
      if (btnReveal) btnReveal.textContent = 'Revelar Respuesta';
    }
  }

  // Event listeners de flashcards
  flashcardOptions.forEach(boton => {
    boton.addEventListener('click', function() {
      // Remover clase active de todos
      flashcardOptions.forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      // Cargar el conjunto correspondiente
      const loteKey = this.getAttribute('data-set');
      cargarConjunto(loteKey);
    });
  });

  if (btnReveal) {
    btnReveal.addEventListener('click', function() {
      if (flashcardAnswer.style.display === 'none' || flashcardAnswer.style.display === '') {
        revelarRespuesta();
      } else {
        flashcardAnswer.style.display = 'none';
        this.textContent = 'Revelar Respuesta';
      }
    });
  }

  if (btnNext) btnNext.addEventListener('click', siguienteFlashcard);
  if (btnPrev) btnPrev.addEventListener('click', anteriorFlashcard);

  // =======================
  // RECOMENDATIONS TABS
  // =======================
  const tipCards = document.querySelectorAll('.tip-card');

  // =======================
  // INICIALIZACIÓN
  // =======================
  // Si hay procesos cargados, iniciar simulación
  // Si no, solo actualizar interfaz con mensaje vacío
  actualizarInterfaz();
  actualizarMetrics();
  actualizarGantt();
}

});
</script>