# -*- coding: utf-8 -*-
"""Textos del estado y del informe final (los usa la consola y la exportación a TXT)."""

from constantes import MAX_MULTIPROGRAMACION
from memoria import tabla_particiones, fragmentacion_externa
from planificador import clave_srtf
from simulacion import (
    calcular_estadisticas, grado_multiprogramacion, sucesos_del_ultimo_paso, simulacion_terminada,
)


# =============================================================================
# Herramientas de formato
# =============================================================================

def tabla_texto(encabezados, filas):
    """Tabla con columnas alineadas y bordes simples."""
    celdas = [[str(c) for c in encabezados]]
    for fila in filas:
        celdas.append([str(c) for c in fila])

    anchos = []
    for columna in range(len(encabezados)):
        ancho = 0
        for fila in celdas:
            ancho = max(ancho, len(fila[columna]))
        anchos.append(ancho)

    separador = "+"
    for ancho in anchos:
        separador += "-" * (ancho + 2) + "+"

    lineas = [separador]
    for numero, fila in enumerate(celdas):
        linea = "|"
        for columna in range(len(fila)):
            linea += " " + fila[columna].rjust(anchos[columna]) + " |"
        lineas.append(linea)
        if numero == 0:
            lineas.append(separador)
    lineas.append(separador)
    return "\n".join(lineas)


def formato_numero(valor, decimales=2):
    """2.6 -> '2,60' (coma decimal)."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def lista_o_vacia(partes, vacia="(vacía)"):
    if len(partes) == 0:
        return vacia
    return ", ".join(partes)


# =============================================================================
# Estado en cada pausa
# =============================================================================

def suspendidos_bloqueados_por_fragmentacion(estado):
    """Suspendidos para los que alcanza la memoria libre total, pero no entran en ningún hueco."""
    resumen = fragmentacion_externa(estado["memoria"])
    bloqueados = []
    for p in estado["suspendidos"]:
        if resumen["mayor_hueco"] < p["tamano"] <= resumen["total_libre"]:
            bloqueados.append(p["id"])
    return bloqueados


def texto_fragmentacion(estado):
    """Una línea con la memoria libre, en cuántos huecos y si eso deja procesos afuera."""
    resumen = fragmentacion_externa(estado["memoria"])
    if resumen["cantidad_huecos"] == 0:
        return "Fragmentación externa: 0K (no hay huecos libres)"
    if resumen["cantidad_huecos"] == 1:
        huecos = "1 hueco"
    else:
        huecos = f"{resumen['cantidad_huecos']} huecos"
    texto = (f"Fragmentación externa: {resumen['total_libre']}K libres en {huecos} "
             f"(el mayor de {resumen['mayor_hueco']}K)")
    bloqueados = suspendidos_bloqueados_por_fragmentacion(estado)
    if len(bloqueados) > 0:
        texto += (f". Impide admitir a {', '.join(bloqueados)}: entraría en el total libre, "
                  f"pero no en un solo hueco")
    return texto


def texto_tabla_particiones(estado):
    filas = []
    for fila in tabla_particiones(estado["memoria"]):
        if fila["numero"] == 0 or fila["libre"]:
            frag_interna = "-"
        else:
            frag_interna = f"{fila['frag_interna']}K"
        frag_externa = f"{fila['tamano']}K" if fila["libre"] else "-"
        filas.append((fila["numero"], f"{fila['inicio']}K", f"{fila['tamano']}K", fila["proceso"],
                      frag_interna, frag_externa))
    return tabla_texto(("Partición", "Inicio", "Tamaño", "Proceso", "Frag. interna", "Frag. externa"), filas)


def texto_colas(estado):
    """Una línea por cola, con los títulos alineados."""
    en_cpu = estado["en_cpu"]
    if en_cpu is None:
        ejecucion = "CPU libre (ociosa)"
    else:
        ejecucion = f"{en_cpu['id']} (restante {en_cpu['restante']})"

    nuevos = [p["id"] for p in estado["nuevos"]]
    listos = [f"{p['id']} (restante {p['restante']})" for p in sorted(estado["listos"], key=clave_srtf)]
    suspendidos = [f"{p['id']} (tamaño {p['tamano']}K)" for p in estado["suspendidos"]]
    terminados = [f"{p['id']} (finalización {p['fin']})" for p in estado["terminados"]]

    colas = [
        ("En ejecución", ejecucion),
        ("Nuevo", lista_o_vacia(nuevos)),
        ("Listos", lista_o_vacia(listos)),
        ("Listos y Suspendidos", lista_o_vacia(suspendidos)),
        (f"Terminados ({len(estado['terminados'])}/{len(estado['procesos'])})", lista_o_vacia(terminados)),
    ]
    lineas = []
    for titulo, contenido in colas:
        lineas.append(f"  {(titulo + ':'):<24}{contenido}")
    return "\n".join(lineas)


def texto_estado(estado):
    """Bloque completo de salida para una pausa."""
    es_evento = estado["t"] == 0 or estado["hubo_evento"]
    marca = "  [EVENTO]" if es_evento else ""
    lineas = [f"=============== T = {estado['t']}{marca} ==============="]

    sucesos = sucesos_del_ultimo_paso(estado)
    for suceso in sucesos:
        if suceso["alerta"]:
            lineas.append(f"  [!] {suceso['texto']}")

    lineas.append("Sucesos:")
    hay_sucesos = False
    for suceso in sucesos:
        if not suceso["alerta"]:
            lineas.append(f"  - T={suceso['t']}: {suceso['texto']}")
            hay_sucesos = True
    if not hay_sucesos:
        lineas.append("  (ninguno)")

    en_cpu = estado["en_cpu"]
    if en_cpu is None:
        cpu = "Libre (ociosa)"
    else:
        cpu = f"{en_cpu['id']} (restante {en_cpu['restante']})"

    lineas += [
        "",
        f"Procesador: {cpu}",
        f"Grado de multiprogramación: {grado_multiprogramacion(estado)}/{MAX_MULTIPROGRAMACION}",
        "",
        "Tabla de particiones:",
        texto_tabla_particiones(estado),
        texto_fragmentacion(estado),
        "",
        "Colas:",
        texto_colas(estado),
    ]
    return "\n".join(lineas)


# =============================================================================
# Informe final
# =============================================================================

def texto_gantt(estado):
    """Diagrama de Gantt de una línea: un casillero por unidad de tiempo ('--' = CPU ociosa)."""
    historial = estado["historial_cpu"]
    if len(historial) == 0:
        return "(sin ejecución)"
    etiquetas = []
    for id_proceso in historial:
        etiquetas.append(id_proceso if id_proceso is not None else "--")
    ancho = max(len(e) for e in etiquetas)

    barra = "|"
    for etiqueta in etiquetas:
        barra += etiqueta.center(ancho) + "|"
    tiempos = ""
    for t in range(len(historial) + 1):
        tiempos += str(t).ljust(ancho + 1)
    return barra + "\n" + tiempos.rstrip()


def texto_informe(estado, con_gantt=True):
    """Informe estadístico final (con el diagrama de Gantt al final si `con_gantt`)."""
    est = calcular_estadisticas(estado)
    filas = []
    for d in est["detalle"]:
        filas.append((d["id"], f"{d['tamano']}K", d["arribo"], d["irrupcion"], d["fin"], d["retorno"], d["espera"]))

    lineas = ["================ INFORME FINAL ================"]
    if not simulacion_terminada(estado):
        lineas = [f"========= INFORME PARCIAL (T = {estado['t']}) =========",
                  "(Solo los procesos que ya terminaron)"]
    lineas += [
        tabla_texto(("Proceso", "Tamaño", "Arribo", "Irrupción", "Finalización", "Retorno", "Espera"), filas),
        "",
        f"Tiempo de retorno promedio: {formato_numero(est['retorno_promedio'])}",
        f"Tiempo de espera promedio:  {formato_numero(est['espera_promedio'])}",
        f"Tiempo total de simulación: {est['tiempo_total']}",
        f"Rendimiento del sistema:    {est['cantidad']}/{est['tiempo_total']} = "
        f"{formato_numero(est['rendimiento'], 4)} trabajos por unidad de tiempo",
    ]
    if con_gantt:
        lineas += ["", "Diagrama de Gantt:", texto_gantt(estado)]
    return "\n".join(lineas)
