# -*- coding: utf-8 -*-
"""
Memoria con particiones variables (MVT) y política Best-Fit.

La memoria de usuario es una lista de particiones ordenada por dirección.
Cada partición es un diccionario:
    {"inicio": 100, "tamano": 120, "proceso": "P1"}   -> ocupada por P1
    {"inicio": 220, "tamano": 330, "proceso": None}   -> hueco libre

Al asignar, el hueco elegido se corta al tamaño exacto del proceso y el
sobrante queda como un hueco aparte. Por eso la fragmentación interna es
siempre 0K; la fragmentación que aparece en MVT es la externa.
"""

from constantes import MEMORIA_SO, MEMORIA_USUARIO


def crear_memoria():
    """Memoria inicial: un único hueco libre con los 450K de usuario."""
    return [{"inicio": MEMORIA_SO, "tamano": MEMORIA_USUARIO, "proceso": None}]


def buscar_hueco_best_fit(memoria, tamano):
    """
    Devuelve la posición del hueco libre más chico en el que entra `tamano`
    (Best-Fit), o -1 si no entra en ninguno. Ante empate gana el de menor
    dirección, porque se recorre en orden y solo se reemplaza si es más chico.
    """
    mejor = -1
    for i in range(len(memoria)):
        particion = memoria[i]
        if particion["proceso"] is None and particion["tamano"] >= tamano:
            if mejor == -1 or particion["tamano"] < memoria[mejor]["tamano"]:
                mejor = i
    return mejor


def asignar_memoria(memoria, id_proceso, tamano):
    """Asigna memoria al proceso con Best-Fit. Devuelve True si pudo, False si no."""
    i = buscar_hueco_best_fit(memoria, tamano)
    if i == -1:
        return False

    hueco = memoria[i]
    sobrante = hueco["tamano"] - tamano
    if sobrante > 0:
        nuevo_hueco = {"inicio": hueco["inicio"] + tamano, "tamano": sobrante, "proceso": None}
        memoria.insert(i + 1, nuevo_hueco)
    hueco["tamano"] = tamano
    hueco["proceso"] = id_proceso
    return True


def liberar_memoria(memoria, id_proceso):
    """Libera la partición del proceso y la une con los huecos libres vecinos."""
    for particion in memoria:
        if particion["proceso"] == id_proceso:
            particion["proceso"] = None
            break

    # Fusionar huecos libres contiguos
    i = 0
    while i < len(memoria) - 1:
        actual = memoria[i]
        siguiente = memoria[i + 1]
        if actual["proceso"] is None and siguiente["proceso"] is None:
            actual["tamano"] += siguiente["tamano"]
            memoria.pop(i + 1)
        else:
            i += 1


def tabla_particiones(memoria):
    """
    Filas de la tabla de particiones para mostrar. La partición 0 es el SO;
    las demás se numeran por dirección en cada instante (en MVT se crean y
    se fusionan dinámicamente).
    """
    filas = [{
        "numero": 0, "inicio": 0, "tamano": MEMORIA_SO,
        "proceso": "S.O.", "frag_interna": 0, "libre": False,
    }]
    numero = 1
    for particion in memoria:
        filas.append({
            "numero": numero,
            "inicio": particion["inicio"],
            "tamano": particion["tamano"],
            "proceso": particion["proceso"] if particion["proceso"] else "Libre",
            "frag_interna": 0,
            "libre": particion["proceso"] is None,
        })
        numero += 1
    return filas


def fragmentacion_externa(memoria):
    """Resumen de la memoria libre: total, cantidad de huecos y el más grande."""
    total = 0
    cantidad = 0
    mayor = 0
    for particion in memoria:
        if particion["proceso"] is None:
            total += particion["tamano"]
            cantidad += 1
            if particion["tamano"] > mayor:
                mayor = particion["tamano"]
    return {"total_libre": total, "cantidad_huecos": cantidad, "mayor_hueco": mayor}
