# -*- coding: utf-8 -*-
"""
===============================================================================
UNIVERSIDAD TECNOLÓGICA NACIONAL - FACULTAD REGIONAL RESISTENCIA
Cátedra: Sistemas Operativos
Trabajo Práctico Integrador: Simulador de Asignación de Memoria y Planificación de CPU

PARADIGMA: PROGRAMACIÓN ESTRUCTURADA ESTRICTA (SIN POO - SIN CLASES)
Módulos:
  - Pantalla de Inicio: Bienvenida, carga por CSV y carga manual ordenada con validaciones.
  - Memoria: Particiones Variables (MVT) con política Best-Fit y coalescencia de huecos.
  - CPU: Planificador SRTF (Shortest Remaining Time First) Apropiativo.
  - Admisión: Grado máximo de 5 procesos activos (Ejecución + Listos + Listos/Suspendidos).
  - Control de Tiempo: Avance ciclo a ciclo, retroceso (paso atrás) y salto por eventos.
  - Métricas: TR, TE, TRP, TEP y Rendimiento (Throughput).
===============================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import csv
import copy

# =============================================================================
# SECCIÓN 1: CONSTANTES Y ESTADO GLOBAL DEL SIMULADOR
# =============================================================================

# Constantes del sistema
MEMORIA_SO = 100          # 100K reservados para el Sistema Operativo
MEMORIA_USUARIO = 450     # 450K para trabajos de usuarios
MEMORIA_TOTAL = 550       # 550K memoria total (100K SO + 450K Usuario)
MAX_PROCESOS_ACTIVOS = 5  # Máximo simultáneo en Ejecución + Listos + Listos/Suspendidos
MAX_PROCESOS_TOTAL = 10   # Límite máximo de procesos por corrida

# Variables dinámicas del reloj y estado de ejecución
reloj_t = 0
simulacion_activa = False
simulacion_terminada = False
contador_id_particion = 1

# Listas de procesos
procesos_cargados_iniciales = []  # Lista maestra de procesos cargados (ordenados por arribo)
cola_nuevos = []                  # Procesos en estado NUEVO esperando admisión
cola_listos = []                  # Procesos en estado LISTO con memoria asignada
cola_listos_suspendidos = []      # Procesos admitidos (<5) en swap por falta de memoria
proceso_ejecucion = None          # Proceso actual en CPU (diccionario o None)
cola_terminados = []              # Procesos que culminaron su ciclo

# Tabla de particiones MVT
# Estructura: {"id": str, "inicio": int, "tamano": int, "id_proceso": str, "frag_interna": int}
tabla_particiones = []

# Historial de eventos (logs)
historial_eventos = []

# Pila de historial de estados para permitir retroceder en el tiempo (Ciclo Anterior)
pila_historial_estados = []

# Referencias a la ventana principal y contenedores de pantallas
ventana_principal = None
contenedor_raiz = None
frame_pantalla_inicio = None
frame_pantalla_simulador = None

# Widgets de la Pantalla de Inicio
entry_manual_id = None
entry_manual_tam = None
entry_manual_ta = None
entry_manual_ti = None
tree_procesos_inicio = None
lbl_contador_procesos = None
lbl_ruta_csv_inicio = None

# Widgets de la Pantalla de Simulación
lbl_badge_reloj_t = None
lbl_cpu_actual = None
lbl_cpu_restante = None
lbl_cpu_arribo = None
lbl_cpu_tamano = None
tree_listos = None
tree_suspendidos = None
tree_nuevos = None
tree_particiones = None
canvas_memoria = None
txt_logs = None
tree_estadisticas = None
lbl_metricas_resumen = None


# =============================================================================
# SECCIÓN 2: GESTIÓN DE PARTICIONES Y MEMORIA (MVT - BEST FIT)
# =============================================================================

def inicializar_memoria():
    """
    Inicializa el mapa de memoria con:
    - Partición 0 (0-100K): Sistema Operativo.
    - Partición 1 (100-550K): 450K Libres para procesos de usuario.
    """
    global tabla_particiones, contador_id_particion
    contador_id_particion = 1
    tabla_particiones = [
        {
            "id": "SO",
            "inicio": 0,
            "tamano": MEMORIA_SO,
            "id_proceso": "S.O.",
            "frag_interna": 0
        },
        {
            "id": f"P_LIBRE_{contador_id_particion}",
            "inicio": MEMORIA_SO,
            "tamano": MEMORIA_USUARIO,
            "id_proceso": "LIBRE",
            "frag_interna": 0
        }
    ]
    contador_id_particion += 1


def buscar_hueco_best_fit(tamano_requerido):
    """
    Busca entre las particiones libres la de menor tamaño suficiente (Best-Fit).
    Retorna el índice en 'tabla_particiones' o -1 si no hay hueco.
    """
    indice_mejor = -1
    menor_tamano = float('inf')

    for i in range(len(tabla_particiones)):
        p = tabla_particiones[i]
        if p["id_proceso"] == "LIBRE" and p["tamano"] >= tamano_requerido:
            if p["tamano"] < menor_tamano:
                menor_tamano = p["tamano"]
                indice_mejor = i

    return indice_mejor


def asignar_memoria_proceso(proceso):
    """
    Asigna una partición variable (MVT) al proceso usando Best-Fit.
    Si cabe, divide la partición y retorna True. De lo contrario, False.
    """
    global contador_id_particion
    idx = buscar_hueco_best_fit(proceso["tamano"])
    if idx == -1:
        return False

    hueco = tabla_particiones[idx]
    tamano_hueco = hueco["tamano"]
    inicio_hueco = hueco["inicio"]
    tamano_proc = proceso["tamano"]

    if tamano_hueco == tamano_proc:
        hueco["id"] = f"P_{proceso['id']}"
        hueco["id_proceso"] = proceso["id"]
        hueco["frag_interna"] = 0
    else:
        particion_ocupada = {
            "id": f"P_{proceso['id']}",
            "inicio": inicio_hueco,
            "tamano": tamano_proc,
            "id_proceso": proceso["id"],
            "frag_interna": 0
        }
        particion_restante = {
            "id": f"P_LIBRE_{contador_id_particion}",
            "inicio": inicio_hueco + tamano_proc,
            "tamano": tamano_hueco - tamano_proc,
            "id_proceso": "LIBRE",
            "frag_interna": 0
        }
        contador_id_particion += 1
        tabla_particiones[idx] = particion_ocupada
        tabla_particiones.insert(idx + 1, particion_restante)

    return True


def liberar_memoria_proceso(id_proceso):
    """
    Libera la partición del proceso y unifica huecos libres contiguos (coalescencia).
    """
    for p in tabla_particiones:
        if p["id_proceso"] == id_proceso:
            p["id_proceso"] = "LIBRE"
            p["id"] = "LIBRE"
            p["frag_interna"] = 0
            break

    # Coalescencia / Fusión de huecos contiguos
    i = 0
    while i < len(tabla_particiones) - 1:
        actual = tabla_particiones[i]
        siguiente = tabla_particiones[i + 1]
        if actual["id_proceso"] == "LIBRE" and siguiente["id_proceso"] == "LIBRE":
            actual["tamano"] += siguiente["tamano"]
            tabla_particiones.pop(i + 1)
        else:
            i += 1


# =============================================================================
# SECCIÓN 3: GESTIÓN DE PROCESOS (CREACIÓN, ARCHIVO Y VALIDACIONES)
# =============================================================================

def crear_proceso(id_proc, tamano, arribo, irrupcion):
    """Crea la estructura de diccionario para un proceso."""
    return {
        "id": str(id_proc).strip().upper(),
        "tamano": int(tamano),
        "tiempo_arribo": int(arribo),
        "tiempo_irrupcion": int(irrupcion),
        "tiempo_restante": int(irrupcion),
        "tiempo_inicio": None,
        "tiempo_fin": None,
        "tiempo_retorno": None,
        "tiempo_espera": None,
        "estado": "NUEVO"
    }


def validar_campos_proceso(id_proc, str_tam, str_ta, str_ti):
    """
    Valida estrictamente los campos de un proceso según las reglas de la cátedra:
    - ID no vacío.
    - Valores numéricos enteros.
    - Tamaño > 0 y <= 450 KB.
    - Tiempo de Arribo >= 0.
    - Tiempo de Irrupción > 0.
    Retorna (es_valido, mensaje_error, datos_convertidos).
    """
    id_limpio = str(id_proc).strip()
    if not id_limpio:
        return False, "El ID del proceso no puede estar vacío.", None

    try:
        tam = int(str_tam)
        ta = int(str_ta)
        ti = int(str_ti)
    except ValueError:
        return False, "Tamaño, Tiempo de Arribo y Tiempo de Irrupción deben ser números enteros válidos.", None

    if tam <= 0:
        return False, "El tamaño del proceso debe ser mayor a 0 KB.", None

    if tam > MEMORIA_USUARIO:
        return False, f"El tamaño ({tam} KB) supera el espacio total para usuarios ({MEMORIA_USUARIO} KB).", None

    if ta < 0:
        return False, "El tiempo de arribo debe ser mayor o igual a 0.", None

    if ti <= 0:
        return False, "El tiempo de irrupción debe ser mayor a 0.", None

    return True, "", (id_limpio, tam, ta, ti)


def cargar_desde_csv_o_txt(ruta_archivo):
    """
    Lee un archivo CSV/TXT con formato: id_proceso, tamano, tiempo_arribo, tiempo_irrupcion
    Valida formato incorrecto o exceso de procesos.
    """
    global procesos_cargados_iniciales

    if not os.path.exists(ruta_archivo):
        messagebox.showerror("Archivo no encontrado", f"No se encontró el archivo:\n{ruta_archivo}")
        return False

    lista_temporal = []

    try:
        with open(ruta_archivo, mode='r', encoding='utf-8') as f:
            lineas = [l.strip() for l in f if l.strip()]

        if not lineas:
            messagebox.showerror("Formato de proceso incorrecto", "El archivo seleccionado se encuentra vacío.")
            return False

        delimitador = ';' if ';' in lineas[0] else ','
        lector = csv.reader(lineas, delimiter=delimitador)
        encabezado_saltado = False
        num_linea = 0

        for fila in lector:
            num_linea += 1
            if not fila:
                continue

            # Detectar encabezado opcional
            primer_campo = fila[0].strip().lower()
            if not encabezado_saltado and ("id" in primer_campo or "proceso" in primer_campo):
                encabezado_saltado = True
                continue

            if len(fila) < 4:
                messagebox.showerror(
                    "Formato de proceso incorrecto",
                    f"La fila {num_linea} no contiene los 4 campos requeridos:\n"
                    f"(id_proceso, tamano, tiempo_arribo, tiempo_irrupcion)"
                )
                return False

            valido, err, datos = validar_campos_proceso(fila[0], fila[1], fila[2], fila[3])
            if not valido:
                messagebox.showerror("Formato de proceso incorrecto", f"Error en fila {num_linea}: {err}")
                return False

            # Verificar ID duplicado
            id_p, tam, ta, ti = datos
            for p_exist in lista_temporal:
                if p_exist["id"] == id_p.upper():
                    messagebox.showerror("Formato de proceso incorrecto", f"ID de proceso duplicado: '{id_p}' en fila {num_linea}.")
                    return False

            lista_temporal.append(crear_proceso(id_p, tam, ta, ti))

        # Validación de cantidad máxima de procesos
        if len(lista_temporal) > MAX_PROCESOS_TOTAL:
            messagebox.showerror(
                "Cantidad de procesos superada",
                f"El archivo contiene {len(lista_temporal)} procesos.\n"
                f"La consigna permite como máximo {MAX_PROCESOS_TOTAL} procesos."
            )
            return False

        if len(lista_temporal) == 0:
            messagebox.showerror("Formato de proceso incorrecto", "No se encontraron procesos válidos en el archivo.")
            return False

        # Si tiene entre 1 y 10 procesos, es válido
        procesos_cargados_iniciales = sorted(lista_temporal, key=lambda p: (p["tiempo_arribo"], p["id"]))
        return True

    except Exception as e:
        messagebox.showerror("Formato de proceso incorrecto", f"Ocurrió un error al procesar el archivo:\n{str(e)}")
        return False


# =============================================================================
# SECCIÓN 4: MOTOR DE PLANIFICACIÓN (SRTF) Y CONTROL DE TIEMPO
# =============================================================================

def contar_procesos_activos():
    """Cantidad de procesos en Ejecución + Listos + Listos/Suspendidos (Máximo 5)."""
    en_cpu = 1 if proceso_ejecucion is not None else 0
    return len(cola_listos) + len(cola_listos_suspendidos) + en_cpu


def verificar_arribos(tiempo_actual):
    """Mueve a 'cola_nuevos' los procesos cuyo tiempo de arribo coincide con el reloj T."""
    arribados = []
    for p in procesos_cargados_iniciales:
        if p["tiempo_arribo"] == tiempo_actual and p["estado"] == "NUEVO":
            if p not in cola_nuevos and p not in cola_listos and p not in cola_listos_suspendidos:
                cola_nuevos.append(p)
                arribados.append(p)
                agregar_log(f"[T={tiempo_actual}] Arribo de {p['id']} (Tamaño: {p['tamano']}K, TI: {p['tiempo_irrupcion']}).")
    return arribados


def reintentar_asignacion_suspendidos():
    """Intenta asignar memoria por Best-Fit a procesos en cola de suspendidos (Swap-In)."""
    i = 0
    while i < len(cola_listos_suspendidos):
        proc = cola_listos_suspendidos[i]
        if asignar_memoria_proceso(proc):
            cola_listos_suspendidos.pop(i)
            proc["estado"] = "LISTO"
            cola_listos.append(proc)
            agregar_log(f"[T={reloj_t}] Memoria obtenida (Swap-In): {proc['id']} pasa a LISTO.")
        else:
            i += 1


def admitir_nuevos_procesos():
    """Admite de 'cola_nuevos' mientras activos < 5 según memoria (Listo o Suspendido)."""
    while cola_nuevos and contar_procesos_activos() < MAX_PROCESOS_ACTIVOS:
        proc = cola_nuevos.pop(0)
        if asignar_memoria_proceso(proc):
            proc["estado"] = "LISTO"
            cola_listos.append(proc)
            agregar_log(f"[T={reloj_t}] Admisión: {proc['id']} asignado en RAM -> LISTO.")
        else:
            proc["estado"] = "LISTO_SUSPENDIDO"
            cola_listos_suspendidos.append(proc)
            agregar_log(f"[T={reloj_t}] Admisión: Memoria insuficiente para {proc['id']} -> LISTO Y SUSPENDIDO.")


def planificar_cpu_srtf():
    """
    Planificador SRTF Apropiativo:
    - Selecciona el proceso con menor tiempo restante en cola_listos.
    - Si la CPU está libre, lo despacha.
    - Si hay proceso en CPU y el candidato tiene tiempo restante ESTRICTAMENTE MENOR, expropia.
    - Ante empate, se mantiene el proceso actual en ejecución (evita sobrecarga).
    """
    global proceso_ejecucion

    if not cola_listos:
        return

    # Buscar menor tiempo restante
    idx_mejor = 0
    menor_ti = cola_listos[0]["tiempo_restante"]
    for i in range(1, len(cola_listos)):
        if cola_listos[i]["tiempo_restante"] < menor_ti:
            menor_ti = cola_listos[i]["tiempo_restante"]
            idx_mejor = i

    candidato = cola_listos[idx_mejor]

    if proceso_ejecucion is None:
        cola_listos.pop(idx_mejor)
        proceso_ejecucion = candidato
        proceso_ejecucion["estado"] = "EJECUCION"
        if proceso_ejecucion["tiempo_inicio"] is None:
            proceso_ejecucion["tiempo_inicio"] = reloj_t
        agregar_log(f"[T={reloj_t}] CPU asignada a {proceso_ejecucion['id']} (Restante: {proceso_ejecucion['tiempo_restante']}).")

    elif candidato["tiempo_restante"] < proceso_ejecucion["tiempo_restante"]:
        # Expropiación
        anterior = proceso_ejecucion
        anterior["estado"] = "LISTO"
        cola_listos.pop(idx_mejor)
        cola_listos.append(anterior)

        proceso_ejecucion = candidato
        proceso_ejecucion["estado"] = "EJECUCION"
        if proceso_ejecucion["tiempo_inicio"] is None:
            proceso_ejecucion["tiempo_inicio"] = reloj_t
        agregar_log(
            f"[T={reloj_t}] Expropiación SRTF: {candidato['id']} (T.Restante {candidato['tiempo_restante']}) "
            f"expropia a {anterior['id']} (T.Restante {anterior['tiempo_restante']})."
        )


def guardar_instantanea_estado():
    """Guarda una instantánea profunda del estado actual para permitir retroceder ciclos."""
    snapshot = {
        "reloj_t": reloj_t,
        "simulacion_activa": simulacion_activa,
        "simulacion_terminada": simulacion_terminada,
        "contador_id_particion": contador_id_particion,
        "tabla_particiones": copy.deepcopy(tabla_particiones),
        "cola_nuevos": copy.deepcopy(cola_nuevos),
        "cola_listos": copy.deepcopy(cola_listos),
        "cola_listos_suspendidos": copy.deepcopy(cola_listos_suspendidos),
        "proceso_ejecucion": copy.deepcopy(proceso_ejecucion),
        "cola_terminados": copy.deepcopy(cola_terminados),
        "procesos_cargados_iniciales": copy.deepcopy(procesos_cargados_iniciales),
        "total_logs": len(historial_eventos)
    }
    pila_historial_estados.append(snapshot)


def restaurar_instantanea_estado():
    """Restaura el estado al ciclo anterior desde la pila de historial."""
    global reloj_t, simulacion_activa, simulacion_terminada, contador_id_particion
    global tabla_particiones, cola_nuevos, cola_listos, cola_listos_suspendidos
    global proceso_ejecucion, cola_terminados, procesos_cargados_iniciales, historial_eventos

    if not pila_historial_estados:
        messagebox.showinfo("Ciclo Anterior", "Ya se encuentra en el instante inicial (T = 0). No hay ciclos previos.")
        return False

    snap = pila_historial_estados.pop()
    reloj_t = snap["reloj_t"]
    simulacion_activa = snap["simulacion_activa"]
    simulacion_terminada = snap["simulacion_terminada"]
    contador_id_particion = snap["contador_id_particion"]
    tabla_particiones = snap["tabla_particiones"]
    cola_nuevos = snap["cola_nuevos"]
    cola_listos = snap["cola_listos"]
    cola_listos_suspendidos = snap["cola_listos_suspendidos"]
    proceso_ejecucion = snap["proceso_ejecucion"]
    cola_terminados = snap["cola_terminados"]
    procesos_cargados_iniciales = snap["procesos_cargados_iniciales"]

    # Recortar logs al tamaño anterior
    cant_logs = snap["total_logs"]
    historial_eventos = historial_eventos[:cant_logs]
    if txt_logs is not None:
        txt_logs.delete("1.0", tk.END)
        for m in historial_eventos:
            txt_logs.insert(tk.END, m + "\n")
        txt_logs.see(tk.END)

    actualizar_interfaz_grafica()
    return True


def avanzar_un_ciclo_reloj():
    """Ejecuta un ciclo de reloj completo y actualiza estados."""
    global reloj_t, proceso_ejecucion, simulacion_terminada

    if simulacion_terminada:
        return {"termino_simulacion": True, "arribo": False, "terminacion": False}

    # Guardar snapshot para permitir retroceder
    guardar_instantanea_estado()

    # 1. Arribos en T actual
    arribados = verificar_arribos(reloj_t)

    # 2. Reintento de asignación para suspendidos
    reintentar_asignacion_suspendidos()

    # 3. Admisión de nuevos respetando activos <= 5
    admitir_nuevos_procesos()

    # 4. Planificación SRTF
    planificar_cpu_srtf()

    # 5. Ejecución en CPU
    proceso_terminado_en_este_ciclo = False
    if proceso_ejecucion is not None:
        proceso_ejecucion["tiempo_restante"] -= 1

        if proceso_ejecucion["tiempo_restante"] == 0:
            proc_fin = proceso_ejecucion
            proc_fin["estado"] = "TERMINADO"
            proc_fin["tiempo_fin"] = reloj_t + 1
            proc_fin["tiempo_retorno"] = proc_fin["tiempo_fin"] - proc_fin["tiempo_arribo"]
            proc_fin["tiempo_espera"] = proc_fin["tiempo_retorno"] - proc_fin["tiempo_irrupcion"]

            liberar_memoria_proceso(proc_fin["id"])
            cola_terminados.append(proc_fin)
            proceso_ejecucion = None
            proceso_terminado_en_este_ciclo = True

            agregar_log(
                f"[T={reloj_t + 1}] Finalizó {proc_fin['id']} "
                f"(TR={proc_fin['tiempo_retorno']}, TE={proc_fin['tiempo_espera']}). Memoria liberada."
            )

            # Reintentar suspendidos y nuevos tras liberar memoria
            reintentar_asignacion_suspendidos()
            admitir_nuevos_procesos()

    # 6. Avanzar reloj
    reloj_t += 1

    # Verificar si concluyó toda la simulación
    if len(procesos_cargados_iniciales) > 0 and len(cola_terminados) == len(procesos_cargados_iniciales):
        simulacion_terminada = True
        agregar_log(f"*** SIMULACIÓN FINALIZADA en T={reloj_t} *** Todos los procesos completados.")

    return {
        "tiempo": reloj_t,
        "arribo": len(arribados) > 0,
        "terminacion": proceso_terminado_en_este_ciclo,
        "termino_simulacion": simulacion_terminada
    }


# =============================================================================
# SECCIÓN 5: CÁLCULO DE MÉTRICAS Y ESTADÍSTICAS FINALES
# =============================================================================

def calcular_estadisticas_finales():
    """Calcula las métricas de rendimiento (TR, TE, TRP, TEP y Rendimiento/Throughput)."""
    total = len(cola_terminados)
    if total == 0:
        return {
            "total_procesos": 0,
            "trp": 0.0,
            "tep": 0.0,
            "rendimiento": 0.0,
            "tiempo_total": reloj_t,
            "detalle": []
        }

    suma_tr = sum(p["tiempo_retorno"] for p in cola_terminados)
    suma_te = sum(p["tiempo_espera"] for p in cola_terminados)

    trp = suma_tr / total
    tep = suma_te / total
    tiempo_total = reloj_t if reloj_t > 0 else 1
    rendimiento = total / tiempo_total

    detalle = []
    for p in cola_terminados:
        detalle.append({
            "id": p["id"],
            "tamano": p["tamano"],
            "arribo": p["tiempo_arribo"],
            "irrupcion": p["tiempo_irrupcion"],
            "fin": p["tiempo_fin"],
            "retorno": p["tiempo_retorno"],
            "espera": p["tiempo_espera"]
        })

    return {
        "total_procesos": total,
        "trp": round(trp, 2),
        "tep": round(tep, 2),
        "rendimiento": round(rendimiento, 4),
        "tiempo_total": tiempo_total,
        "detalle": detalle
    }


# =============================================================================
# SECCIÓN 6: INTERFAZ GRÁFICA (PANTALLA DE INICIO Y SIMULADOR)
# =============================================================================

def agregar_log(mensaje):
    """Registra un evento en la lista y en el panel de texto."""
    historial_eventos.append(mensaje)
    if txt_logs is not None:
        txt_logs.insert(tk.END, mensaje + "\n")
        txt_logs.see(tk.END)


def reiniciar_simulacion():
    """Reinicia el estado al tiempo T=0 con los procesos cargados actualmente."""
    global reloj_t, simulacion_activa, simulacion_terminada, proceso_ejecucion
    global cola_nuevos, cola_listos, cola_listos_suspendidos, cola_terminados
    global pila_historial_estados, historial_eventos

    reloj_t = 0
    simulacion_activa = False
    simulacion_terminada = False
    proceso_ejecucion = None

    cola_nuevos.clear()
    cola_listos.clear()
    cola_listos_suspendidos.clear()
    cola_terminados.clear()
    pila_historial_estados.clear()
    historial_eventos.clear()

    for p in procesos_cargados_iniciales:
        p["tiempo_restante"] = p["tiempo_irrupcion"]
        p["tiempo_inicio"] = None
        p["tiempo_fin"] = None
        p["tiempo_retorno"] = None
        p["tiempo_espera"] = None
        p["estado"] = "NUEVO"

    inicializar_memoria()

    if txt_logs is not None:
        txt_logs.delete("1.0", tk.END)

    agregar_log("Simulador reiniciado a T=0. Memoria lista.")
    actualizar_interfaz_grafica()


def ejecutar_paso_a_paso():
    """Avanza exactamente 1 ciclo de reloj."""
    if not procesos_cargados_iniciales:
        messagebox.showinfo("Simulador", "No hay procesos cargados.")
        return

    if simulacion_terminada:
        messagebox.showinfo("Simulador", "La simulación ya finalizó. Puede revisar el informe estadístico.")
        return

    res = avanzar_un_ciclo_reloj()
    actualizar_interfaz_grafica()

    if res["termino_simulacion"]:
        mostrar_dialogo_informe_final()


def retroceder_un_ciclo():
    """Vuelve un ciclo hacia atrás en el tiempo restaurando el estado previo."""
    restaurar_instantanea_estado()


def ejecutar_hasta_siguiente_evento():
    """Avanza ciclo a ciclo hasta un arribo, terminación o fin de simulación."""
    if not procesos_cargados_iniciales:
        messagebox.showinfo("Simulador", "No hay procesos cargados.")
        return

    if simulacion_terminada:
        messagebox.showinfo("Simulador", "La simulación ya finalizó.")
        return

    ciclos = 0
    while not simulacion_terminada and ciclos < 500:
        res = avanzar_un_ciclo_reloj()
        ciclos += 1
        if res["arribo"] or res["terminacion"] or res["termino_simulacion"]:
            break

    actualizar_interfaz_grafica()

    if simulacion_terminada:
        mostrar_dialogo_informe_final()


def dibujar_canvas_memoria():
    """Dibuja en el Canvas la distribución visual de las particiones."""
    if canvas_memoria is None:
        return

    canvas_memoria.delete("all")
    ancho = canvas_memoria.winfo_width()
    alto = canvas_memoria.winfo_height()

    if ancho <= 1:
        ancho = 500
    if alto <= 1:
        alto = 65

    mx = 10
    my = 12
    ancho_util = ancho - (2 * mx)
    alto_barra = alto - (2 * my)

    for p in tabla_particiones:
        x0 = mx + ((p["inicio"] / MEMORIA_TOTAL) * ancho_util)
        x1 = x0 + ((p["tamano"] / MEMORIA_TOTAL) * ancho_util)
        y0 = my
        y1 = y0 + alto_barra

        if p["id_proceso"] == "S.O.":
            color = "#ff7675"
            texto = f"S.O.\n{p['tamano']}K"
        elif p["id_proceso"] == "LIBRE":
            color = "#bdc3c7"  # Gris para memoria libre
            texto = f"Libre\n{p['tamano']}K"
        else:
            color = "#74b9ff"
            texto = f"{p['id_proceso']}\n{p['tamano']}K"

        canvas_memoria.create_rectangle(x0, y0, x1, y1, fill=color, outline="#2d3436", width=1.5)
        if (x1 - x0) > 30:
            canvas_memoria.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=texto, font=("Arial", 8, "bold"))


def actualizar_tabla_tree(tree, lista_datos):
    """Limpia y carga filas en un Treeview."""
    for item in tree.get_children():
        tree.delete(item)
    for fila in lista_datos:
        tree.insert("", tk.END, values=fila)


def actualizar_interfaz_grafica():
    """Refresca todos los paneles del simulador con los datos del estado actual."""
    if ventana_principal is None:
        return

    # 1. Reloj T destacado
    lbl_badge_reloj_t.config(text=f"T = {reloj_t}")

    # 2. Panel CPU
    if proceso_ejecucion is not None:
        lbl_cpu_actual.config(text=f"Proceso en CPU: {proceso_ejecucion['id']}", fg="#27ae60")
        lbl_cpu_restante.config(text=f"T. Restante: {proceso_ejecucion['tiempo_restante']} u.")
        lbl_cpu_arribo.config(text=f"T. Arribo: {proceso_ejecucion['tiempo_arribo']}")
        lbl_cpu_tamano.config(text=f"Tamaño: {proceso_ejecucion['tamano']} KB")
    else:
        lbl_cpu_actual.config(text="Proceso en CPU: LIBRE (Ociosa)", fg="#7f8c8d")
        lbl_cpu_restante.config(text="T. Restante: -")
        lbl_cpu_arribo.config(text="T. Arribo: -")
        lbl_cpu_tamano.config(text="Tamaño: -")

    # 3. Colas
    actualizar_tabla_tree(
        tree_listos,
        [(p["id"], f"{p['tamano']}K", p["tiempo_arribo"], p["tiempo_irrupcion"], p["tiempo_restante"]) for p in cola_listos]
    )
    actualizar_tabla_tree(
        tree_suspendidos,
        [(p["id"], f"{p['tamano']}K", p["tiempo_arribo"], p["tiempo_irrupcion"], p["tiempo_restante"]) for p in cola_listos_suspendidos]
    )
    actualizar_tabla_tree(
        tree_nuevos,
        [(p["id"], f"{p['tamano']}K", p["tiempo_arribo"], p["tiempo_irrupcion"]) for p in cola_nuevos]
    )

    # 4. Memoria
    actualizar_tabla_tree(
        tree_particiones,
        [(p["id"], f"{p['inicio']}K", f"{p['tamano']}K", p["id_proceso"], f"{p['frag_interna']}K") for p in tabla_particiones]
    )
    dibujar_canvas_memoria()

    # 5. Estadísticas de Terminados
    actualizar_tabla_tree(
        tree_estadisticas,
        [(p["id"], f"{p['tamano']}K", p["tiempo_arribo"], p["tiempo_irrupcion"], p["tiempo_fin"], p["tiempo_retorno"], p["tiempo_espera"]) for p in cola_terminados]
    )

    # Resumen inferior
    stats = calcular_estadisticas_finales()
    lbl_metricas_resumen.config(
        text=f"Terminados: {len(cola_terminados)}/{len(procesos_cargados_iniciales)}  |  "
             f"TRP: {stats['trp']} u.  |  TEP: {stats['tep']} u.  |  Rendimiento: {stats['rendimiento']} trab/u."
    )


def mostrar_dialogo_informe_final():
    """Abre la ventana modal con las métricas finales."""
    stats = calcular_estadisticas_finales()

    modal = tk.Toplevel(ventana_principal)
    modal.title("Informe Estadístico Final de la Simulación")
    modal.geometry("680x470")
    modal.transient(ventana_principal)
    modal.grab_set()

    lbl_t = tk.Label(modal, text="INFORME ESTADÍSTICO FINAL DE RENDIMIENTO", font=("Arial", 12, "bold"), pady=10)
    lbl_t.pack()

    frame_t = tk.Frame(modal, padx=10, pady=5)
    frame_t.pack(fill=tk.BOTH, expand=True)

    cols = ("ID", "Tamaño", "TA", "TI", "T_Fin", "TR (Retorno)", "TE (Espera)")
    tr_mod = ttk.Treeview(frame_t, columns=cols, show='headings', height=8)
    for c in cols:
        tr_mod.heading(c, text=c)
        tr_mod.column(c, width=85, anchor='center')
    tr_mod.pack(fill=tk.BOTH, expand=True)

    for item in stats["detalle"]:
        tr_mod.insert("", tk.END, values=(
            item["id"], f"{item['tamano']}K", item["arribo"], item["irrupcion"], item["fin"], item["retorno"], item["espera"]
        ))

    frame_ind = tk.LabelFrame(modal, text="Indicadores Globales", padx=12, pady=10, font=("Arial", 10, "bold"))
    frame_ind.pack(fill=tk.X, padx=15, pady=10)

    txt_res = (
        f"• Cantidad de procesos completados: {stats['total_procesos']}\n"
        f"• Tiempo total transcurrido: {stats['tiempo_total']} unidades de tiempo\n"
        f"• Tiempo de Retorno Promedio (TRP): {stats['trp']} unidades\n"
        f"• Tiempo de Espera Promedio (TEP): {stats['tep']} unidades\n"
        f"• Rendimiento del Sistema (Throughput): {stats['rendimiento']} procesos / unidad de tiempo"
    )
    lbl_info = tk.Label(frame_ind, text=txt_res, justify=tk.LEFT, font=("Arial", 10))
    lbl_info.pack(anchor="w")

    btn_c = tk.Button(
        modal, text="Cerrar", bg="#34495e", fg="white", font=("Arial", 10, "bold"),
        padx=15, pady=4, relief=tk.RAISED, cursor="hand2", command=modal.destroy
    )
    btn_c.pack(pady=8)


# =============================================================================
# SECCIÓN 7: CONTROLADORES DE LA PANTALLA DE INICIO
# =============================================================================

def refrescar_tabla_procesos_inicio():
    """Actualiza la tabla de procesos en la pantalla de bienvenida."""
    filas = [
        (p["id"], f"{p['tamano']} KB", p["tiempo_arribo"], p["tiempo_irrupcion"])
        for p in procesos_cargados_iniciales
    ]
    actualizar_tabla_tree(tree_procesos_inicio, filas)
    lbl_contador_procesos.config(text=f"Procesos cargados: {len(procesos_cargados_iniciales)} / {MAX_PROCESOS_TOTAL}")


def accion_cargar_csv_inicio():
    """Maneja el botón de cargar archivo CSV desde la pantalla de bienvenida."""
    dir_actual = os.path.dirname(os.path.abspath(__file__))
    ruta = filedialog.askopenfilename(
        title="Seleccionar archivo de procesos (CSV o TXT)",
        initialdir=dir_actual,
        filetypes=[("Archivos CSV o Texto", "*.csv *.txt"), ("Todos los archivos", "*.*")]
    )
    if ruta:
        if cargar_desde_csv_o_txt(ruta):
            lbl_ruta_csv_inicio.config(text=f"Archivo cargado: {os.path.basename(ruta)}", fg="#27ae60")
            refrescar_tabla_procesos_inicio()


def accion_agregar_proceso_manual():
    """Valida y agrega un proceso manualmente desde el formulario de la pantalla de bienvenida."""
    if len(procesos_cargados_iniciales) >= MAX_PROCESOS_TOTAL:
        messagebox.showerror(
            "Cantidad de procesos superada",
            f"Se ha alcanzado la cantidad máxima de {MAX_PROCESOS_TOTAL} procesos permitida por la consigna."
        )
        return

    id_p = entry_manual_id.get()
    tam_p = entry_manual_tam.get()
    ta_p = entry_manual_ta.get()
    ti_p = entry_manual_ti.get()

    valido, mensaje_error, datos = validar_campos_proceso(id_p, tam_p, ta_p, ti_p)
    if not valido:
        messagebox.showerror("Formato de proceso incorrecto", mensaje_error)
        return

    id_limpio, tam, ta, ti = datos

    # Comprobar si ya existe el ID
    for p in procesos_cargados_iniciales:
        if p["id"] == id_limpio.upper():
            messagebox.showerror("Formato de proceso incorrecto", f"Ya existe un proceso con el ID '{id_limpio.upper()}'.")
            return

    nuevo_proc = crear_proceso(id_limpio, tam, ta, ti)
    procesos_cargados_iniciales.append(nuevo_proc)
    procesos_cargados_iniciales.sort(key=lambda p: (p["tiempo_arribo"], p["id"]))

    # Limpiar campos de entrada
    entry_manual_id.delete(0, tk.END)
    entry_manual_tam.delete(0, tk.END)
    entry_manual_ta.delete(0, tk.END)
    entry_manual_ti.delete(0, tk.END)
    entry_manual_id.focus_set()

    refrescar_tabla_procesos_inicio()


def accion_eliminar_proceso_seleccionado():
    """Elimina el proceso seleccionado en la tabla de inicio."""
    sel = tree_procesos_inicio.selection()
    if not sel:
        messagebox.showinfo("Atención", "Seleccione un proceso de la tabla para eliminarlo.")
        return

    item = tree_procesos_inicio.item(sel[0])
    pid = item["values"][0]

    for i in range(len(procesos_cargados_iniciales)):
        if procesos_cargados_iniciales[i]["id"] == pid:
            procesos_cargados_iniciales.pop(i)
            break

    refrescar_tabla_procesos_inicio()


def accion_limpiar_todos_los_procesos():
    """Borra todos los procesos cargados en inicio."""
    procesos_cargados_iniciales.clear()
    lbl_ruta_csv_inicio.config(text="Ningún archivo cargado.", fg="#7f8c8d")
    refrescar_tabla_procesos_inicio()


def accion_cargar_ejemplo_defecto():
    """Carga rápidamente el caso de ejemplo estándar."""
    global procesos_cargados_iniciales
    procesos_cargados_iniciales = [
        crear_proceso("P1", 120, 0, 8),
        crear_proceso("P2", 250, 2, 4),
        crear_proceso("P3", 80, 3, 6),
        crear_proceso("P4", 150, 5, 3),
        crear_proceso("P5", 100, 7, 5),
        crear_proceso("P6", 60, 10, 2)
    ]
    lbl_ruta_csv_inicio.config(text="Ejemplo precargado (6 procesos).", fg="#2980b9")
    refrescar_tabla_procesos_inicio()


def iniciar_simulacion_desde_inicio():
    """Realiza la transición de la Pantalla de Inicio al Simulador."""
    if len(procesos_cargados_iniciales) == 0:
        messagebox.showwarning(
            "Sin procesos",
            "Debe cargar al menos 1 proceso (mediante CSV o manualmente) para iniciar la simulación."
        )
        return

    if len(procesos_cargados_iniciales) > MAX_PROCESOS_TOTAL:
        messagebox.showerror(
            "Cantidad de procesos superada",
            f"No se puede iniciar: hay {len(procesos_cargados_iniciales)} procesos (máximo permitido: {MAX_PROCESOS_TOTAL})."
        )
        return

    # Ocultar pantalla de bienvenida y mostrar simulador
    frame_pantalla_inicio.pack_forget()
    frame_pantalla_simulador.pack(fill=tk.BOTH, expand=True)

    reiniciar_simulacion()


def volver_a_pantalla_inicio():
    """Regresa a la pantalla de bienvenida y configuración de procesos."""
    frame_pantalla_simulador.pack_forget()
    frame_pantalla_inicio.pack(fill=tk.BOTH, expand=True)
    refrescar_tabla_procesos_inicio()


# =============================================================================
# SECCIÓN 8: CONSTRUCCIÓN VISUAL DE LAS PANTALLAS (TKINTER ESTRUCTURADO)
# =============================================================================

def construir_pantalla_inicio(parent):
    """Construye los widgets de la pantalla de bienvenida y carga de procesos."""
    global frame_pantalla_inicio, entry_manual_id, entry_manual_tam, entry_manual_ta, entry_manual_ti
    global tree_procesos_inicio, lbl_contador_procesos, lbl_ruta_csv_inicio

    frame_pantalla_inicio = tk.Frame(parent, bg="#f5f6fa")

    # Banner superior de bienvenida
    banner = tk.Frame(frame_pantalla_inicio, bg="#2c3e50", padx=20, pady=16)
    banner.pack(fill=tk.X)

    tk.Label(
        banner,
        text="SISTEMAS OPERATIVOS - UTN FRRe",
        font=("Arial", 11, "bold"),
        fg="#bdc3c7",
        bg="#2c3e50"
    ).pack()

    tk.Label(
        banner,
        text="Simulador de Asignación de Memoria y Planificación de CPU",
        font=("Arial", 16, "bold"),
        fg="#ffffff",
        bg="#2c3e50",
        pady=4
    ).pack()

    tk.Label(
        banner,
        text="Planificador SRTF (Apropiativo) • Memoria con Particiones Variables (MVT Best-Fit)",
        font=("Arial", 10),
        fg="#f1c40f",
        bg="#2c3e50"
    ).pack()

    # Contenedor central de opciones (2 columnas: Carga CSV/Manual y Tabla de procesos)
    cuerpo = tk.Frame(frame_pantalla_inicio, bg="#f5f6fa", padx=15, pady=12)
    cuerpo.pack(fill=tk.BOTH, expand=True)

    col_izq = tk.Frame(cuerpo, bg="#f5f6fa", width=420)
    col_izq.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

    # Tarjeta 1: Carga por CSV
    lf_csv = tk.LabelFrame(col_izq, text="Opción A: Cargar desde Archivo (CSV / TXT)", font=("Arial", 10, "bold"), padx=12, pady=10, bg="white")
    lf_csv.pack(fill=tk.X, pady=(0, 10))

    tk.Label(
        lf_csv,
        text="Seleccione un archivo con columnas:\nid_proceso, tamaño, tiempo_arribo, tiempo_irrupcion",
        font=("Arial", 8),
        justify=tk.LEFT,
        bg="white",
        fg="#555555"
    ).pack(anchor="w", pady=(0, 8))

    btn_explorar = tk.Button(
        lf_csv,
        text="📁 Seleccionar Archivo CSV / TXT",
        font=("Arial", 9, "bold"),
        bg="#3498db",
        fg="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        padx=10,
        pady=5,
        command=accion_cargar_csv_inicio
    )
    btn_explorar.pack(fill=tk.X)

    lbl_ruta_csv_inicio = tk.Label(lf_csv, text="Ningún archivo cargado.", font=("Arial", 8, "italic"), bg="white", fg="#7f8c8d")
    lbl_ruta_csv_inicio.pack(anchor="w", pady=(5, 0))

    # Tarjeta 2: Carga Manual de Procesos
    lf_manual = tk.LabelFrame(col_izq, text="Opción B: Carga Manual de Proceso", font=("Arial", 10, "bold"), padx=12, pady=10, bg="white")
    lf_manual.pack(fill=tk.BOTH, expand=True)

    grid_form = tk.Frame(lf_manual, bg="white")
    grid_form.pack(fill=tk.X, pady=4)

    # Campos del formulario
    tk.Label(grid_form, text="ID Proceso (ej: P1):", font=("Arial", 9), bg="white").grid(row=0, column=0, sticky="w", pady=4)
    entry_manual_id = ttk.Entry(grid_form, width=15)
    entry_manual_id.grid(row=0, column=1, sticky="ew", pady=4, padx=5)

    tk.Label(grid_form, text="Tamaño (KB, máx 450):", font=("Arial", 9), bg="white").grid(row=1, column=0, sticky="w", pady=4)
    entry_manual_tam = ttk.Entry(grid_form, width=15)
    entry_manual_tam.grid(row=1, column=1, sticky="ew", pady=4, padx=5)

    tk.Label(grid_form, text="Tiempo Arribo (TA >= 0):", font=("Arial", 9), bg="white").grid(row=2, column=0, sticky="w", pady=4)
    entry_manual_ta = ttk.Entry(grid_form, width=15)
    entry_manual_ta.grid(row=2, column=1, sticky="ew", pady=4, padx=5)

    tk.Label(grid_form, text="Tiempo Irrupción (TI > 0):", font=("Arial", 9), bg="white").grid(row=3, column=0, sticky="w", pady=4)
    entry_manual_ti = ttk.Entry(grid_form, width=15)
    entry_manual_ti.grid(row=3, column=1, sticky="ew", pady=4, padx=5)

    btn_agregar = tk.Button(
        lf_manual,
        text="➕ Agregar Proceso a la Lista",
        font=("Arial", 9, "bold"),
        bg="#27ae60",
        fg="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        pady=5,
        command=accion_agregar_proceso_manual
    )
    btn_agregar.pack(fill=tk.X, pady=(10, 4))

    # Columna derecha: Tabla de Procesos listos para simular
    col_der = tk.LabelFrame(cuerpo, text="Procesos Cargados para la Simulación", font=("Arial", 10, "bold"), padx=12, pady=10, bg="white")
    col_der.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    cols_inicio = ("ID", "Tamaño", "Tiempo Arribo (TA)", "Tiempo Irrupción (TI)")
    tree_procesos_inicio = ttk.Treeview(col_der, columns=cols_inicio, show='headings', height=10)
    for c in cols_inicio:
        tree_procesos_inicio.heading(c, text=c)
        tree_procesos_inicio.column(c, width=110, anchor='center')
    tree_procesos_inicio.pack(fill=tk.BOTH, expand=True)

    # Barra de estado de carga
    frame_acciones_tabla = tk.Frame(col_der, bg="white", pady=8)
    frame_acciones_tabla.pack(fill=tk.X)

    lbl_contador_procesos = tk.Label(
        frame_acciones_tabla,
        text=f"Procesos cargados: 0 / {MAX_PROCESOS_TOTAL}",
        font=("Arial", 10, "bold"),
        bg="white",
        fg="#2c3e50"
    )
    lbl_contador_procesos.pack(side=tk.LEFT)

    btn_limpiar = tk.Button(
        frame_acciones_tabla,
        text="Limpiar Todo",
        font=("Arial", 8),
        bg="#e74c3c",
        fg="white",
        cursor="hand2",
        command=accion_limpiar_todos_los_procesos
    )
    btn_limpiar.pack(side=tk.RIGHT, padx=4)

    btn_eliminar = tk.Button(
        frame_acciones_tabla,
        text="Eliminar Seleccionado",
        font=("Arial", 8),
        bg="#95a5a6",
        fg="white",
        cursor="hand2",
        command=accion_eliminar_proceso_seleccionado
    )
    btn_eliminar.pack(side=tk.RIGHT, padx=4)

    btn_ejemplo = tk.Button(
        frame_acciones_tabla,
        text="Cargar Ejemplo (6 procesos)",
        font=("Arial", 8, "bold"),
        bg="#f39c12",
        fg="white",
        cursor="hand2",
        command=accion_cargar_ejemplo_defecto
    )
    btn_ejemplo.pack(side=tk.RIGHT, padx=4)

    # Barra inferior fija: BOTÓN INICIAR SIMULACIÓN
    frame_pie_inicio = tk.Frame(frame_pantalla_inicio, bg="#ecf0f1", padx=20, pady=12, bd=1, relief=tk.RIDGE)
    frame_pie_inicio.pack(fill=tk.X, side=tk.BOTTOM)

    btn_iniciar = tk.Button(
        frame_pie_inicio,
        text="🚀 INICIAR SIMULACIÓN CON ESTOS PROCESOS",
        font=("Arial", 12, "bold"),
        bg="#27ae60",
        fg="white",
        activebackground="#219a52",
        activeforeground="white",
        relief=tk.RAISED,
        bd=3,
        cursor="hand2",
        padx=20,
        pady=8,
        command=iniciar_simulacion_desde_inicio
    )
    btn_iniciar.pack()


def construir_pantalla_simulador(parent):
    """Construye la pantalla de ejecución de la simulación con botones abajo y colores distintivos."""
    global frame_pantalla_simulador, lbl_badge_reloj_t
    global lbl_cpu_actual, lbl_cpu_restante, lbl_cpu_arribo, lbl_cpu_tamano
    global tree_listos, tree_suspendidos, tree_nuevos, tree_particiones
    global canvas_memoria, txt_logs, tree_estadisticas, lbl_metricas_resumen

    frame_pantalla_simulador = tk.Frame(parent, bg="#f5f6fa")

    # ------------------ ENCABEZADO SUPERIOR CON RELOJ T DESTACADO ------------------
    frame_top = tk.Frame(frame_pantalla_simulador, bg="#1e272e", padx=16, pady=8)
    frame_top.pack(fill=tk.X)

    # Título en el encabezado
    frame_titulos = tk.Frame(frame_top, bg="#1e272e")
    frame_titulos.pack(side=tk.LEFT)

    tk.Label(
        frame_titulos,
        text="SIMULADOR DE PLANIFICACIÓN CPU (SRTF) Y MEMORIA (MVT BEST-FIT)",
        font=("Arial", 11, "bold"),
        fg="#ffffff",
        bg="#1e272e"
    ).pack(anchor="w")

    tk.Label(
        frame_titulos,
        text="UTN FRRe - Sistemas Operativos | Esquema de 550K (100K SO + 450K Usuario) | Máx 5 activos",
        font=("Arial", 8),
        fg="#95a5a6",
        bg="#1e272e"
    ).pack(anchor="w")

    # BADGE DESTACADO PARA EL RELOJ T (Estilizado, prominente y limpio)
    frame_badge_t = tk.Frame(
        frame_top,
        bg="#000000",
        highlightbackground="#f39c12",
        highlightcolor="#f39c12",
        highlightthickness=2,
        padx=14,
        pady=3
    )
    frame_badge_t.pack(side=tk.RIGHT)

    tk.Label(
        frame_badge_t,
        text="TIEMPO DEL SISTEMA",
        font=("Arial", 7, "bold"),
        fg="#f1c40f",
        bg="#000000"
    ).pack()

    lbl_badge_reloj_t = tk.Label(
        frame_badge_t,
        text="T = 0",
        font=("Consolas", 18, "bold"),
        fg="#00d2d3",
        bg="#000000"
    )
    lbl_badge_reloj_t.pack()

    # ------------------ CONTENEDOR CENTRAL: PANELES DE ESTADO ------------------
    paned_central = tk.PanedWindow(frame_pantalla_simulador, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
    paned_central.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    # --- PANEL IZQUIERDO: CPU Y COLAS ---
    frame_izq = tk.Frame(paned_central, bg="#f5f6fa")
    paned_central.add(frame_izq, minsize=420)

    # 1. Estado del Procesador
    lf_cpu = tk.LabelFrame(frame_izq, text="Estado del Procesador (CPU)", font=("Arial", 9, "bold"), padx=8, pady=4, bg="white")
    lf_cpu.pack(fill=tk.X, pady=2)

    lbl_cpu_actual = tk.Label(lf_cpu, text="Proceso en CPU: LIBRE", font=("Arial", 11, "bold"), fg="#7f8c8d", bg="white")
    lbl_cpu_actual.pack(anchor="w")

    frame_cpu_detalles = tk.Frame(lf_cpu, bg="white")
    frame_cpu_detalles.pack(fill=tk.X, pady=2)

    lbl_cpu_restante = tk.Label(frame_cpu_detalles, text="T. Restante: -", font=("Arial", 9), bg="white")
    lbl_cpu_restante.pack(side=tk.LEFT, padx=6)

    lbl_cpu_arribo = tk.Label(frame_cpu_detalles, text="T. Arribo: -", font=("Arial", 9), bg="white")
    lbl_cpu_arribo.pack(side=tk.LEFT, padx=6)

    lbl_cpu_tamano = tk.Label(frame_cpu_detalles, text="Tamaño: -", font=("Arial", 9), bg="white")
    lbl_cpu_tamano.pack(side=tk.LEFT, padx=6)

    # 2. Cola de Listos
    lf_listos = tk.LabelFrame(frame_izq, text="Cola de Listos (En RAM, esperando CPU)", font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_listos.pack(fill=tk.BOTH, expand=True, pady=2)

    cols_proc = ("ID", "Tamaño", "Arribo", "TI", "T. Restante")
    tree_listos = ttk.Treeview(lf_listos, columns=cols_proc, show='headings', height=3)
    for c in cols_proc:
        tree_listos.heading(c, text=c)
        tree_listos.column(c, width=70, anchor='center')
    tree_listos.pack(fill=tk.BOTH, expand=True)

    # 3. Cola de Listos y Suspendidos
    lf_susp = tk.LabelFrame(frame_izq, text="Cola de Listos y Suspendidos (Admitidos <5, en Swap)", font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_susp.pack(fill=tk.BOTH, expand=True, pady=2)

    tree_suspendidos = ttk.Treeview(lf_susp, columns=cols_proc, show='headings', height=3)
    for c in cols_proc:
        tree_suspendidos.heading(c, text=c)
        tree_suspendidos.column(c, width=70, anchor='center')
    tree_suspendidos.pack(fill=tk.BOTH, expand=True)

    # 4. Cola de Nuevos
    lf_nuevos = tk.LabelFrame(frame_izq, text="Cola de Nuevos (Esperando cupo < 5)", font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_nuevos.pack(fill=tk.BOTH, expand=True, pady=2)

    cols_nuevos = ("ID", "Tamaño", "Arribo", "TI")
    tree_nuevos = ttk.Treeview(lf_nuevos, columns=cols_nuevos, show='headings', height=3)
    for c in cols_nuevos:
        tree_nuevos.heading(c, text=c)
        tree_nuevos.column(c, width=80, anchor='center')
    tree_nuevos.pack(fill=tk.BOTH, expand=True)

    # --- PANEL DERECHO: MEMORIA Y EVENTOS ---
    frame_der = tk.Frame(paned_central, bg="#f5f6fa")
    paned_central.add(frame_der, minsize=480)

    # 1. Tabla de Particiones
    lf_memoria = tk.LabelFrame(frame_der, text="Tabla de Particiones MVT (100K SO + 450K Usuario)", font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_memoria.pack(fill=tk.BOTH, expand=True, pady=2)

    cols_part = ("ID Partición", "Dir. Comienzo", "Tamaño", "ID Proceso", "Frag. Interna")
    tree_particiones = ttk.Treeview(lf_memoria, columns=cols_part, show='headings', height=4)
    for c in cols_part:
        tree_particiones.heading(c, text=c)
        tree_particiones.column(c, width=90, anchor='center')
    tree_particiones.pack(fill=tk.BOTH, expand=True)

    # Gráfico de Memoria
    tk.Label(lf_memoria, text="Mapa Gráfico de Memoria:", font=("Arial", 8, "italic"), bg="white").pack(anchor="w", pady=(2, 0))
    canvas_memoria = tk.Canvas(lf_memoria, height=45, bg="#f9f9f9", bd=1, relief=tk.SUNKEN)
    canvas_memoria.pack(fill=tk.X, pady=2)

    # 2. Registro de Logs
    lf_logs = tk.LabelFrame(frame_der, text="Registro de Eventos y Transiciones de Estado", font=("Arial", 9, "bold"), padx=4, pady=2, bg="white")
    lf_logs.pack(fill=tk.BOTH, expand=True, pady=2)

    scroll_logs = ttk.Scrollbar(lf_logs)
    scroll_logs.pack(side=tk.RIGHT, fill=tk.Y)

    txt_logs = tk.Text(lf_logs, height=5, font=("Consolas", 8), yscrollcommand=scroll_logs.set)
    txt_logs.pack(fill=tk.BOTH, expand=True)
    scroll_logs.config(command=txt_logs.yview)

    # ------------------ PANEL DE HISTORIAL Y MÉTRICAS ------------------
    frame_stats_box = tk.LabelFrame(frame_pantalla_simulador, text="Procesos Finalizados y Métricas", font=("Arial", 9, "bold"), padx=6, pady=2, bg="white")
    frame_stats_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)

    cols_stats = ("ID", "Tamaño", "Arribo (TA)", "Irrupción (TI)", "T. Fin", "Retorno (TR)", "Espera (TE)")
    tree_estadisticas = ttk.Treeview(frame_stats_box, columns=cols_stats, show='headings', height=3)
    for c in cols_stats:
        tree_estadisticas.heading(c, text=c)
        tree_estadisticas.column(c, width=100, anchor='center')
    tree_estadisticas.pack(fill=tk.BOTH, expand=True)

    lbl_metricas_resumen = tk.Label(
        frame_stats_box,
        text="Terminados: 0 | TRP: 0.0 u. | TEP: 0.0 u. | Rendimiento: 0.0 trab/u.",
        font=("Arial", 9, "bold"),
        fg="#2c3e50",
        bg="white"
    )
    lbl_metricas_resumen.pack(anchor="w", pady=1)

    # ------------------ BARRA INFERIOR DE BOTONES (COLORES DISTINTIVOS) ------------------
    # Requisitos:
    # 1. Todos los botones abajo.
    # 2. Siguiente Ciclo en VERDE.
    # 3. Volver hacia atrás los ciclos (comparte color VERDE con siguiente ciclo).
    # 4. Los demás botones abajo, cada uno con color distintivo propio.
    frame_botones_inferior = tk.Frame(frame_pantalla_simulador, bg="#2f3640", padx=10, pady=8, bd=2, relief=tk.RIDGE)
    frame_botones_inferior.pack(fill=tk.X, side=tk.BOTTOM)

    # Botón Ciclo Anterior (VERDE - comparte color)
    btn_ciclo_ant = tk.Button(
        frame_botones_inferior,
        text="⏮ Ciclo Anterior (T - 1)",
        font=("Arial", 10, "bold"),
        bg="#27ae60",
        fg="white",
        activebackground="#219a52",
        activeforeground="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        padx=10,
        pady=5,
        command=retroceder_un_ciclo
    )
    btn_ciclo_ant.pack(side=tk.LEFT, padx=5)

    # Botón Siguiente Ciclo (VERDE - solicitado específicamente)
    btn_siguiente_ciclo = tk.Button(
        frame_botones_inferior,
        text="⏭ Siguiente Ciclo (T + 1)",
        font=("Arial", 10, "bold"),
        bg="#27ae60",
        fg="white",
        activebackground="#219a52",
        activeforeground="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        padx=12,
        pady=5,
        command=ejecutar_paso_a_paso
    )
    btn_siguiente_ciclo.pack(side=tk.LEFT, padx=5)

    # Botón Siguiente Evento (AZUL DISTINTIVO)
    btn_evento = tk.Button(
        frame_botones_inferior,
        text="⏩ Siguiente Evento (Arribo/Fin)",
        font=("Arial", 9, "bold"),
        bg="#2980b9",
        fg="white",
        activebackground="#1f618d",
        activeforeground="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        padx=8,
        pady=5,
        command=ejecutar_hasta_siguiente_evento
    )
    btn_evento.pack(side=tk.LEFT, padx=5)

    # Botón Reiniciar a T=0 (NARANJA DISTINTIVO)
    btn_reiniciar = tk.Button(
        frame_botones_inferior,
        text="🔄 Reiniciar (T=0)",
        font=("Arial", 9, "bold"),
        bg="#e67e22",
        fg="white",
        activebackground="#d35400",
        activeforeground="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        padx=8,
        pady=5,
        command=reiniciar_simulacion
    )
    btn_reiniciar.pack(side=tk.LEFT, padx=5)

    # Botón Ver Informe Final (PÚRPURA / VIOLETA DISTINTIVO)
    btn_informe = tk.Button(
        frame_botones_inferior,
        text="📊 Informe Estadístico",
        font=("Arial", 9, "bold"),
        bg="#8e44ad",
        fg="white",
        activebackground="#71368a",
        activeforeground="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        padx=8,
        pady=5,
        command=mostrar_dialogo_informe_final
    )
    btn_informe.pack(side=tk.LEFT, padx=5)

    # Botón Volver a Inicio / Carga de Procesos (GRIS PIZARRA DISTINTIVO)
    btn_volver = tk.Button(
        frame_botones_inferior,
        text="🏠 Volver a Inicio / Carga",
        font=("Arial", 9, "bold"),
        bg="#7f8c8d",
        fg="white",
        activebackground="#636e72",
        activeforeground="white",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        padx=10,
        pady=5,
        command=volver_a_pantalla_inicio
    )
    btn_volver.pack(side=tk.RIGHT, padx=5)


# =============================================================================
# SECCIÓN 9: PUNTO DE ENTRADA PRINCIPAL (MAIN)
# =============================================================================

def main():
    """Función principal estructurada que lanza la aplicación."""
    global ventana_principal, contenedor_raiz

    ventana_principal = tk.Tk()
    ventana_principal.title("Simulador de Memoria y CPU - Sistemas Operativos (UTN FRRe)")
    ventana_principal.geometry("1120x800")
    ventana_principal.minsize(980, 720)

    contenedor_raiz = tk.Frame(ventana_principal)
    contenedor_raiz.pack(fill=tk.BOTH, expand=True)

    # Construir ambas pantallas
    construir_pantalla_inicio(contenedor_raiz)
    construir_pantalla_simulador(contenedor_raiz)

    # Cargar por defecto el archivo 'procesos.csv' si existe para comodidad
    ruta_defecto = os.path.join(os.path.dirname(os.path.abspath(__file__)), "procesos.csv")
    if os.path.exists(ruta_defecto):
        cargar_desde_csv_o_txt(ruta_defecto)
        lbl_ruta_csv_inicio.config(text=f"Archivo cargado: {os.path.basename(ruta_defecto)}", fg="#27ae60")
        refrescar_tabla_procesos_inicio()

    # Mostrar inicialmente la Pantalla de Inicio
    frame_pantalla_simulador.pack_forget()
    frame_pantalla_inicio.pack(fill=tk.BOTH, expand=True)

    ventana_principal.mainloop()


if __name__ == "__main__":
    main()
