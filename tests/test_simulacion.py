# -*- coding: utf-8 -*-
"""Resultados de los lotes de la cátedra (verificados contra otro simulador independiente)."""
import copy
import os

import pytest

from entrada import leer_archivo
from simulacion import (crear_estado, crear_proceso, avanzar_instante, avanzar_hasta_evento,
                        ejecutar_completa, calcular_estadisticas, simulacion_terminada,
                        grado_multiprogramacion, alertas_del_ultimo_paso)

LOTES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lotes")

# {proceso: (fin, retorno, espera)}, TRP, TEP, tiempo total
ESPERADOS = {
    1: ({"P1": (5, 2, 0), "P2": (15, 5, 1), "P3": (11, 1, 0), "P4": (17, 3, 1), "P5": (22, 2, 0)},
        2.6, 0.4, 22),
    2: ({"P1": (56, 56, 36), "P2": (2, 2, 0), "P3": (26, 26, 11), "P4": (36, 36, 26), "P5": (11, 11, 2)},
        26.2, 15.0, 56),
    3: ({"P1": (23, 23, 13), "P2": (1, 1, 0), "P3": (40, 40, 28), "P4": (3, 3, 1), "P5": (55, 55, 40),
         "P6": (13, 10, 4), "P7": (7, 4, 0), "P8": (28, 24, 19)}, 20.0, 13.125, 55),
    4: ({"P1": (56, 56, 36), "P2": (38, 36, 27), "P3": (8, 5, 1), "P4": (5, 1, 0), "P5": (10, 4, 2),
         "P6": (30, 23, 17), "P7": (13, 5, 2), "P8": (20, 11, 6), "P9": (15, 5, 3), "P10": (24, 13, 9)},
        15.9, 10.3, 56),
}


def leer_lote(numero):
    return leer_archivo(os.path.join(LOTES, f"lote_{numero}.csv"))


def correr_lote(numero):
    procesos, errores = leer_lote(numero)
    estado = crear_estado(procesos)
    ejecutar_completa(estado)
    return estado, errores


@pytest.mark.parametrize("numero", [1, 2, 3, 4])
def test_lotes_validos(numero):
    estado, errores = correr_lote(numero)
    assert errores == []
    est = calcular_estadisticas(estado)
    por_proceso, trp, tep, total = ESPERADOS[numero]
    assert {d["id"]: (d["fin"], d["retorno"], d["espera"]) for d in est["detalle"]} == por_proceso
    assert est["retorno_promedio"] == pytest.approx(trp)
    assert est["espera_promedio"] == pytest.approx(tep)
    assert est["tiempo_total"] == total
    assert est["rendimiento"] == pytest.approx(len(por_proceso) / total)


def test_lote_5_se_simula_sin_el_proceso_de_451k():
    estado, errores = correr_lote(5)
    assert len(errores) == 1 and "451K" in errores[0]
    assert [p["id"] for p in estado["procesos"]] == ["P1", "P3"]
    # En T=2 llega P3 (TI 4) y P1 tiene restante 3: sigue P1 hasta T=5, después P3 hasta T=9.
    est = calcular_estadisticas(estado)
    assert {d["id"]: d["fin"] for d in est["detalle"]} == {"P1": 5, "P3": 9}


def test_lote_6_toma_los_10_primeros():
    estado, errores = correr_lote(6)
    assert len(errores) == 1 and "P11, P12" in errores[0]
    assert len(estado["procesos"]) == 10


def test_lote_1_el_estado_en_T_ya_incluye_los_arribos_de_T():
    """En T=3 llega P1: la pantalla de T=3 ya lo tiene que mostrar en CPU."""
    procesos, _ = leer_lote(1)
    estado = crear_estado(procesos)
    for _ in range(3):
        avanzar_instante(estado)
    assert estado["t"] == 3
    assert estado["en_cpu"]["id"] == "P1"
    avanzar_instante(estado)
    avanzar_instante(estado)
    assert estado["t"] == 5 and estado["en_cpu"] is None
    assert estado["terminados"][0]["id"] == "P1"


def test_lote_2_en_T0_ya_hay_admitidos_y_suspendidos():
    procesos, _ = leer_lote(2)
    estado = crear_estado(procesos)
    assert estado["t"] == 0
    assert estado["en_cpu"]["id"] == "P2"
    assert [p["id"] for p in estado["suspendidos"]] == ["P4", "P5"]
    assert grado_multiprogramacion(estado) == 5


def test_grado_multiprogramacion_maximo_5():
    procesos = [crear_proceso(f"P{i}", 40, 0, 5) for i in range(1, 8)]
    estado = crear_estado(procesos)
    assert grado_multiprogramacion(estado) == 5
    assert [p["id"] for p in estado["nuevos"]] == ["P6", "P7"]


def test_mismo_arribo_se_ordena_por_numero_de_id():
    procesos = [crear_proceso(f"P{i}", 40, 0, 5) for i in range(10, 0, -1)]
    estado = crear_estado(procesos)
    assert [p["id"] for p in estado["nuevos"]] == ["P6", "P7", "P8", "P9", "P10"]


def test_alerta_por_expropiacion():
    estado = crear_estado([crear_proceso("P1", 50, 0, 5), crear_proceso("P2", 50, 1, 2)])
    avanzar_instante(estado)
    assert estado["en_cpu"]["id"] == "P2"
    assert len(alertas_del_ultimo_paso(estado)) == 1


def test_volver_atras_con_copias_da_lo_mismo():
    procesos, _ = leer_lote(4)
    directo = crear_estado(copy.deepcopy(procesos))
    ejecutar_completa(directo)

    estado = crear_estado(copy.deepcopy(procesos))
    pila = []
    paso = 0
    while not simulacion_terminada(estado):
        pila.append(copy.deepcopy(estado))
        avanzar_instante(estado)
        paso += 1
        if paso % 4 == 0:   # cada tanto, retroceder dos pasos
            pila.pop()
            estado = pila.pop()
    assert calcular_estadisticas(estado) == calcular_estadisticas(directo)
    assert estado["historial_cpu"] == directo["historial_cpu"]


def test_siguiente_evento_da_lo_mismo_que_instante_a_instante():
    procesos, _ = leer_lote(3)
    a = crear_estado(copy.deepcopy(procesos))
    b = crear_estado(copy.deepcopy(procesos))
    ejecutar_completa(a)
    while not simulacion_terminada(b):
        avanzar_hasta_evento(b)
        assert b["hubo_evento"]
    assert calcular_estadisticas(a) == calcular_estadisticas(b)
