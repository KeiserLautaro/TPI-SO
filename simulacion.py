# -*- coding: utf-8 -*-
"""
Motor de la simulación: une memoria (Best-Fit), planificación (SRTF) y los
estados de los procesos. NO importa nada de la interfaz: la consola y la
interfaz gráfica solo llaman a estas funciones y muestran el `estado`.

Todo el estado de la simulación vive en un único diccionario `estado`, que
se pasa como parámetro a cada función. Para "volver atrás" alcanza con
guardar copias: copy.deepcopy(estado).

Qué significa el estado en el instante T: es lo que queda después de procesar,
en ese orden, los arribos, la admisión y la planificación de T. Es decir, qué
proceso usa la CPU durante [T, T+1). Un proceso que termina al final de
[T-1, T) figura como terminado en T.
"""

from constantes import MAX_MULTIPROGRAMACION
from memoria import crear_memoria, asignar_memoria, liberar_memoria
from planificador import elegir_proceso_srtf, clave_orden_llegada

# Estados posibles de un proceso
NUEVO = "Nuevo"
LISTO = "Listo"
LISTO_SUSPENDIDO = "Listo y Suspendido"
EJECUCION = "Ejecución"
TERMINADO = "Terminado"


# =============================================================================
# Creación
# =============================================================================

def crear_proceso(id_proceso, tamano, arribo, irrupcion):
    """Diccionario que representa un proceso."""
    return {
        "id": id_proceso,
        "tamano": tamano,
        "arribo": arribo,
        "irrupcion": irrupcion,
        "restante": irrupcion,
        "estado": None,   # None mientras todavía no arribó
        "fin": None,      # instante de finalización
    }


def crear_estado(procesos):
    """
    Crea la simulación con la lista de procesos y la deja en el instante T = 0
    (ya procesados los arribos, la admisión y la planificación de T = 0).
    `procesos` es una lista de diccionarios creados con crear_proceso().
    """
    if len(procesos) == 0:
        raise ValueError("No hay procesos para simular.")

    todos = sorted(procesos, key=clave_orden_llegada)
    estado = {
        "t": 0,
        "procesos": todos,
        "nuevos": [],
        "listos": [],
        "suspendidos": [],
        "en_cpu": None,
        "terminados": [],
        "memoria": crear_memoria(),
        "historial_cpu": [],      # Id del proceso en CPU en cada instante ejecutado (None = ociosa)
        "registro": [],           # Todos los sucesos: {"t", "texto", "alerta"}
        "inicio_paso": 0,         # Posición en "registro" donde empiezan los sucesos del último paso
        "hubo_evento": False,     # Si en el último instante llegó o terminó algún proceso
    }
    procesar_arribos(estado)
    admitir_procesos(estado)
    planificar_cpu(estado)
    return estado


# =============================================================================
# Consultas
# =============================================================================

def simulacion_terminada(estado):
    """True cuando todos los procesos terminaron."""
    return len(estado["terminados"]) == len(estado["procesos"])


def grado_multiprogramacion(estado):
    """Cantidad de procesos en Ejecución + Listos + Listos/Suspendidos."""
    en_cpu = 0
    if estado["en_cpu"] is not None:
        en_cpu = 1
    return en_cpu + len(estado["listos"]) + len(estado["suspendidos"])


def sucesos_del_ultimo_paso(estado):
    """Sucesos registrados desde la pantalla anterior."""
    return estado["registro"][estado["inicio_paso"]:]


def alertas_del_ultimo_paso(estado):
    """Alertas SRTF registradas desde la pantalla anterior."""
    alertas = []
    for suceso in sucesos_del_ultimo_paso(estado):
        if suceso["alerta"]:
            alertas.append(suceso)
    return alertas


def registrar(estado, texto, alerta=False, t=None):
    """Agrega un suceso al registro."""
    if t is None:
        t = estado["t"]
    estado["registro"].append({"t": t, "texto": texto, "alerta": alerta})


# =============================================================================
# Pasos de cada instante
# =============================================================================

def procesar_arribos(estado):
    """Los procesos cuyo tiempo de arribo es T pasan a Nuevo (en orden de llegada)."""
    for proceso in estado["procesos"]:
        if proceso["estado"] is None and proceso["arribo"] == estado["t"]:
            proceso["estado"] = NUEVO
            estado["nuevos"].append(proceso)
            estado["hubo_evento"] = True
            registrar(estado, f"Arriba {proceso['id']} al estado Nuevo ({proceso['tamano']}K, TI={proceso['irrupcion']})")


def admitir_procesos(estado):
    """
    1. Los Listos/Suspendidos (en orden FIFO) que ahora entran en algún hueco
       reciben memoria y pasan a Listo. Ya cuentan para el grado de
       multiprogramación, así que no consumen cupo. Si uno no entra, los que
       vienen detrás igual pueden entrar.
    2. Mientras el grado de multiprogramación sea menor a 5, los Nuevos (FIFO)
       pasan a Listo si hay hueco, o a Listo/Suspendido si no lo hay.
    """
    memoria = estado["memoria"]

    for proceso in list(estado["suspendidos"]):
        if asignar_memoria(memoria, proceso["id"], proceso["tamano"]):
            estado["suspendidos"].remove(proceso)
            proceso["estado"] = LISTO
            estado["listos"].append(proceso)
            registrar(estado, f"{proceso['id']} ya entra en memoria: pasa de Listo y Suspendido a Listo")

    while len(estado["nuevos"]) > 0 and grado_multiprogramacion(estado) < MAX_MULTIPROGRAMACION:
        proceso = estado["nuevos"].pop(0)
        if asignar_memoria(memoria, proceso["id"], proceso["tamano"]):
            proceso["estado"] = LISTO
            estado["listos"].append(proceso)
            registrar(estado, f"{proceso['id']} es admitido en memoria y pasa a Listo")
        else:
            proceso["estado"] = LISTO_SUSPENDIDO
            estado["suspendidos"].append(proceso)
            registrar(estado, f"{proceso['id']} no entra en memoria: pasa a Listo y Suspendido")


def planificar_cpu(estado):
    """Aplica SRTF. Registra una alerta si el elegido se adelanta al orden de llegada."""
    en_cpu = estado["en_cpu"]
    elegido = elegir_proceso_srtf(en_cpu, estado["listos"])
    if elegido is None or elegido is en_cpu:
        return

    if en_cpu is not None:
        # Expropiación: el que estaba en CPU vuelve a Listos
        en_cpu["estado"] = LISTO
        estado["listos"].append(en_cpu)
        registrar(
            estado,
            f"ALERTA SRTF: {elegido['id']} se adelanta: desaloja a {en_cpu['id']} "
            f"(restante {en_cpu['restante']}), con restante {elegido['restante']}",
            alerta=True,
        )
        registrar(
            estado,
            f"{en_cpu['id']} es desalojado de la CPU y vuelve a Listo "
            f"(restante {en_cpu['restante']} > {elegido['restante']} de {elegido['id']})",
        )
    else:
        # CPU libre: hay alerta si pasa delante de Listos que llegaron antes
        salteados = []
        for proceso in sorted(estado["listos"], key=clave_orden_llegada):
            if proceso is not elegido and clave_orden_llegada(proceso) < clave_orden_llegada(elegido):
                salteados.append(f"{proceso['id']} (restante {proceso['restante']})")
        if len(salteados) > 0:
            if len(salteados) == 1:
                quienes = f"{salteados[0]}, que llegó antes"
            else:
                quienes = f"{', '.join(salteados[:-1])} y {salteados[-1]}, que llegaron antes"
            registrar(
                estado,
                f"ALERTA SRTF: {elegido['id']} se adelanta: pasa delante de {quienes}, "
                f"con restante {elegido['restante']}",
                alerta=True,
            )

    estado["listos"].remove(elegido)
    elegido["estado"] = EJECUCION
    estado["en_cpu"] = elegido
    registrar(estado, f"{elegido['id']} entra a la CPU (restante {elegido['restante']})")


def ejecutar_unidad(estado):
    """
    El proceso en CPU ejecuta durante [T, T+1). Si termina, su finalización es
    T+1 y libera su memoria (los huecos vecinos se fusionan).
    """
    proceso = estado["en_cpu"]
    if proceso is None:
        estado["historial_cpu"].append(None)
        return

    estado["historial_cpu"].append(proceso["id"])
    proceso["restante"] -= 1
    if proceso["restante"] == 0:
        fin = estado["t"] + 1
        proceso["estado"] = TERMINADO
        proceso["fin"] = fin
        estado["en_cpu"] = None
        estado["terminados"].append(proceso)
        liberar_memoria(estado["memoria"], proceso["id"])
        estado["hubo_evento"] = True
        registrar(
            estado,
            f"{proceso['id']} termina y libera su partición de {proceso['tamano']}K "
            f"(retorno {fin - proceso['arribo']}, espera {fin - proceso['arribo'] - proceso['irrupcion']})",
            t=fin,
        )


def ejecutar_instante(estado):
    """Pasa de T a T+1: ejecuta una unidad y procesa arribos, admisión y planificación de T+1."""
    estado["hubo_evento"] = False
    ejecutar_unidad(estado)
    estado["t"] += 1
    procesar_arribos(estado)
    admitir_procesos(estado)
    planificar_cpu(estado)


# =============================================================================
# Avance (lo que llaman la consola y la interfaz)
# =============================================================================

def avanzar_instante(estado):
    """Avanza un instante (T -> T+1). No hace nada si la simulación ya terminó."""
    if simulacion_terminada(estado):
        return
    estado["inicio_paso"] = len(estado["registro"])
    ejecutar_instante(estado)


def avanzar_hasta_evento(estado):
    """Avanza hasta el próximo instante en que llega o termina algún proceso."""
    if simulacion_terminada(estado):
        return
    estado["inicio_paso"] = len(estado["registro"])
    ejecutar_instante(estado)
    while not estado["hubo_evento"] and not simulacion_terminada(estado):
        ejecutar_instante(estado)


def ejecutar_completa(estado):
    """Corre hasta el final (para tests y verificación)."""
    while not simulacion_terminada(estado):
        avanzar_instante(estado)


# =============================================================================
# Estadísticas
# =============================================================================

def calcular_estadisticas(estado):
    """
    Retorno = finalización - arribo; espera = retorno - irrupción.
    Rendimiento = procesos terminados / tiempo total, donde el tiempo total es
    la finalización del último proceso contada desde T = 0.
    Si la simulación no terminó, calcula sobre los procesos ya terminados.
    """
    detalle = []
    suma_retorno = 0
    suma_espera = 0
    tiempo_total = 0
    for proceso in sorted(estado["terminados"], key=clave_orden_llegada):
        retorno = proceso["fin"] - proceso["arribo"]
        espera = retorno - proceso["irrupcion"]
        suma_retorno += retorno
        suma_espera += espera
        if proceso["fin"] > tiempo_total:
            tiempo_total = proceso["fin"]
        detalle.append({
            "id": proceso["id"],
            "tamano": proceso["tamano"],
            "arribo": proceso["arribo"],
            "irrupcion": proceso["irrupcion"],
            "fin": proceso["fin"],
            "retorno": retorno,
            "espera": espera,
        })

    n = len(detalle)
    if n == 0:
        return {"detalle": [], "cantidad": 0, "retorno_promedio": 0.0,
                "espera_promedio": 0.0, "tiempo_total": 0, "rendimiento": 0.0}
    return {
        "detalle": detalle,
        "cantidad": n,
        "retorno_promedio": suma_retorno / n,
        "espera_promedio": suma_espera / n,
        "tiempo_total": tiempo_total,
        "rendimiento": n / tiempo_total,
    }
