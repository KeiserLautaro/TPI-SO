# -*- coding: utf-8 -*-
"""Planificación de CPU: SRTF (Shortest Remaining Time First), expropiativo."""


def numero_de_id(id_proceso):
    """
    Número dentro del Id, para ordenar 'P2' antes que 'P10'
    (comparados como texto, 'P10' quedaría antes que 'P2').
    """
    digitos = ""
    for caracter in id_proceso:
        if caracter.isdigit():
            digitos += caracter
    if digitos == "":
        return 0
    return int(digitos)


def clave_orden_llegada(proceso):
    """Orden de llegada: menor tiempo de arribo y, ante empate, menor Id."""
    return (proceso["arribo"], numero_de_id(proceso["id"]), proceso["id"])


def clave_srtf(proceso):
    """Menor tiempo restante; ante empate, el que llegó primero."""
    return (proceso["restante"],) + clave_orden_llegada(proceso)


def elegir_proceso_srtf(en_cpu, listos):
    """
    Devuelve el proceso que debe ocupar la CPU (o None si no hay ninguno).

    Compiten el proceso en ejecución y los Listos; gana el de menor tiempo
    restante. Reglas de desempate:
      - Si empata con el que está en CPU, sigue el que está en CPU
        (expropiar solo si el otro es estrictamente menor).
      - Entre Listos, gana el de menor tiempo de arribo y luego el de menor Id.
    """
    mejor_listo = None
    for proceso in listos:
        if mejor_listo is None or clave_srtf(proceso) < clave_srtf(mejor_listo):
            mejor_listo = proceso

    if en_cpu is None:
        return mejor_listo
    if mejor_listo is not None and mejor_listo["restante"] < en_cpu["restante"]:
        return mejor_listo
    return en_cpu
