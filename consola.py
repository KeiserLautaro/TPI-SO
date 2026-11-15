# -*- coding: utf-8 -*-
"""
Versión por consola del simulador (sirve para verificar el motor sin la interfaz).

Uso:
    python consola.py lotes/lote_1.csv

En cada pausa se elige cómo avanzar (igual que los botones de la interfaz):
    [Enter]  siguiente instante (T + 1)
    [e]      siguiente evento (hasta que llegue o termine un proceso)
    [q]      salir
"""

import sys

from entrada import leer_archivo
from informe import texto_estado, texto_informe
from simulacion import crear_estado, avanzar_instante, avanzar_hasta_evento, simulacion_terminada

# Líneas en blanco entre un instante y el siguiente, para que no queden pegados
SEPARACION_ENTRE_INSTANTES = "\n" * 2


def leer_tecla(mensaje):
    """
    Muestra el mensaje y devuelve la tecla apretada, sin esperar Enter.
    Devuelve "" para Enter y "q" para Ctrl+C o fin de entrada.
    Si la entrada no es una terminal (por ejemplo, viene de un pipe), lee una línea entera.
    """
    if not sys.stdin.isatty():
        try:
            return input(mensaje).strip().lower()
        except EOFError:
            return "q"

    print(mensaje, end="", flush=True)
    try:
        import msvcrt   # Windows
        tecla = msvcrt.getwch()
        if tecla in ("\x00", "\xe0"):   # flechas y teclas especiales mandan dos caracteres
            msvcrt.getwch()
            tecla = "?"
    except ImportError:
        import termios, tty   # Linux / Mac
        fd = sys.stdin.fileno()
        config_anterior = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            tecla = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, config_anterior)

    if tecla in ("\r", "\n"):
        tecla = ""
    elif tecla in ("\x03", "\x04", "\x1a"):   # Ctrl+C, Ctrl+D, Ctrl+Z
        tecla = "q"
    print(tecla if tecla.isprintable() else "")
    return tecla.lower()


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

    procesos = cargar_procesos(ruta)
    if procesos is None:
        return

    print(f"Procesos cargados desde {ruta}: {len(procesos)}")
    estado = crear_estado(procesos)
    print()
    print(texto_estado(estado))
    while not simulacion_terminada(estado):
        opcion = leer_tecla("\n[Enter] siguiente instante, [e] siguiente evento, [q] salir: ")
        if opcion == "q":
            print("Simulación interrumpida.")
            return
        if opcion == "e":
            avanzar_hasta_evento(estado)
        elif opcion == "":
            avanzar_instante(estado)
        else:
            print("Opción no válida.")
            continue
        print(SEPARACION_ENTRE_INSTANTES)
        print(texto_estado(estado))

    print(SEPARACION_ENTRE_INSTANTES)
    print(texto_informe(estado, con_gantt=False))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # para que las tildes se vean bien en Windows
    main()
