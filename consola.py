# -*- coding: utf-8 -*-
"""
Versión por consola del simulador (sirve para verificar el motor sin la interfaz).

Uso:
    python consola.py lotes/lote_1.csv            pausa en cada instante
    python consola.py lotes/lote_1.csv --eventos  pausa solo cuando llega o termina un proceso
"""

import sys

from entrada import leer_archivo
from informe import texto_estado, texto_informe
from simulacion import crear_estado, avanzar_instante, avanzar_hasta_evento, simulacion_terminada

# Líneas en blanco entre un instante y el siguiente, para que no queden pegados
SEPARACION_ENTRE_INSTANTES = "\n" * 2


def cargar_procesos(ruta):
    """Lee el archivo; si hay errores los muestra y pregunta si se sigue con los válidos."""
    procesos, errores = leer_archivo(ruta)
    if len(errores) > 0:
        print("Problemas en el archivo:")
        for error in errores:
            print("  -", error)
        if len(procesos) == 0:
            return None
        ids = []
        for p in procesos:
            ids.append(p["id"])
        respuesta = input(f"¿Continuar con {len(procesos)} proceso(s) válido(s): {', '.join(ids)}? [s/n] ")
        if respuesta.strip().lower() != "s":
            return None
    return procesos


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    ruta = sys.argv[1]
    solo_eventos = "--eventos" in sys.argv

    procesos = cargar_procesos(ruta)
    if procesos is None:
        return

    paso = "evento" if solo_eventos else "instante"
    print(f"Procesos cargados desde {ruta}: {len(procesos)}")
    estado = crear_estado(procesos)
    print()
    print(texto_estado(estado))
    while not simulacion_terminada(estado):
        try:
            respuesta = input(f"\n[Enter] siguiente {paso}, [q] salir: ")
        except EOFError:
            respuesta = "q"
        if respuesta.strip().lower() == "q":
            print("Simulación interrumpida.")
            return
        if solo_eventos:
            avanzar_hasta_evento(estado)
        else:
            avanzar_instante(estado)
        print(SEPARACION_ENTRE_INSTANTES)
        print(texto_estado(estado))

    print(SEPARACION_ENTRE_INSTANTES)
    print(texto_informe(estado, con_gantt=False))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # para que las tildes se vean bien en Windows
    main()
