def numero_de_id(id_proceso):
    digitos = ""
    for caracter in id_proceso:
        if caracter.isdigit():
            digitos += caracter
    if digitos == "":
        return 0
    return int(digitos)


def clave_orden_llegada(proceso):
    return (proceso["arribo"], numero_de_id(proceso["id"]), proceso["id"])


def clave_srtf(proceso):
    return (proceso["restante"],) + clave_orden_llegada(proceso)


def elegir_proceso_srtf(en_cpu, listos):
    mejor_listo = None
    for proceso in listos:
        if mejor_listo is None or clave_srtf(proceso) < clave_srtf(mejor_listo):
            mejor_listo = proceso

    if en_cpu is None:
        return mejor_listo
    if mejor_listo is not None and mejor_listo["restante"] < en_cpu["restante"]:
        return mejor_listo
    return en_cpu
