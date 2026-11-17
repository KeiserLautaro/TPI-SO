from memoria import fragmentacion_externa
from simulacion import calcular_estadisticas, simulacion_terminada


def tabla_texto(encabezados, filas):
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
    return f"{valor:.{decimales}f}".replace(".", ",")


def suspendidos_bloqueados_por_fragmentacion(estado):
    resumen = fragmentacion_externa(estado["memoria"])
    bloqueados = []
    for p in estado["suspendidos"]:
        if resumen["mayor_hueco"] < p["tamano"] <= resumen["total_libre"]:
            bloqueados.append(p["id"])
    return bloqueados


def texto_informe(estado):
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
    return "\n".join(lineas)
