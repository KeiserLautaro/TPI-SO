import copy
import os

import pytest

from entrada import leer_archivo
from informe import suspendidos_bloqueados_por_fragmentacion
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
    # Lotes propios
    7: ({"P1": (2, 2, 0), "P2": (15, 15, 5), "P3": (5, 5, 2), "P4": (31, 31, 19), "P5": (19, 18, 14)},
        14.2, 8.0, 31),
    8: ({"P1": (4, 4, 0), "P2": (11, 10, 7), "P3": (6, 4, 2), "P10": (8, 6, 4)}, 6.0, 3.25, 11),
    9: ({"P1": (1, 1, 0), "P2": (21, 21, 11), "P3": (3, 3, 1), "P4": (33, 33, 21), "P5": (6, 6, 3),
         "P6": (9, 2, 0), "P7": (12, 5, 2)}, 71 / 7, 38 / 7, 33),
    11: ({"P1": (3, 3, 0), "P2": (15, 15, 5), "P3": (17, 16, 14), "P4": (5, 4, 2)}, 9.5, 5.25, 17),
}


def leer_lote(numero):
    return leer_archivo(os.path.join(LOTES, f"lote_{numero}.csv"))


def correr_lote(numero):
    procesos, errores = leer_lote(numero)
    estado = crear_estado(procesos)
    ejecutar_completa(estado)
    return estado, errores


@pytest.mark.parametrize("numero", [1, 2, 3, 4, 7, 8, 9, 11])
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


def avanzar_hasta(estado, t):
    while estado["t"] < t:
        avanzar_instante(estado)


def test_lote_7_fragmentacion_externa_bloquea_a_P5():
    procesos, _ = leer_lote(7)
    estado = crear_estado(procesos)
    avanzar_hasta(estado, 5)
    # Libres: 150K + 150K = 300K, pero separados por P2: P5 (200K) no entra
    assert suspendidos_bloqueados_por_fragmentacion(estado) == ["P5"]
    avanzar_hasta(estado, 15)
    # P2 termina, los huecos se fusionan y P5 entra
    assert suspendidos_bloqueados_por_fragmentacion(estado) == []
    assert estado["en_cpu"]["id"] == "P5"


def test_lote_9_best_fit_elige_el_hueco_mas_chico():
    procesos, _ = leer_lote(9)
    estado = crear_estado(procesos)
    avanzar_hasta(estado, 7)
    # Huecos libres antes de admitir: 100K (dir 100), 60K (dir 250) y 190K (dir 360)
    inicio = {p["proceso"]: p["inicio"] for p in estado["memoria"] if p["proceso"]}
    assert inicio["P6"] == 250   # 55K va al hueco de 60K, no al primero (100K)
    assert inicio["P7"] == 100   # 95K va al hueco de 100K, no al más grande (190K)


def test_lote_10_informa_cada_error_y_simula_los_validos():
    estado, errores = correr_lote(10)
    assert len(errores) == 7
    assert [p["id"] for p in estado["procesos"]] == ["P1", "P8"]
    est = calcular_estadisticas(estado)
    assert est["retorno_promedio"] == pytest.approx(2.5)
    assert est["espera_promedio"] == pytest.approx(0.5)


def test_lote_11_columnas_en_otro_orden_e_ids_numericos():
    procesos, errores = leer_lote(11)
    assert errores == []
    assert [(p["id"], p["tamano"], p["arribo"], p["irrupcion"]) for p in procesos] == [
        ("P1", 300, 0, 3), ("P2", 150, 0, 10), ("P3", 350, 1, 2), ("P4", 100, 1, 2)]
    estado = crear_estado(procesos)
    avanzar_hasta(estado, 3)
    # Se libera un hueco de 300K: P3 (350K) sigue suspendido, pero P4 (detrás) entra igual
    assert [p["id"] for p in estado["suspendidos"]] == ["P3"]
    assert estado["en_cpu"]["id"] == "P4"


def test_lote_1_el_estado_en_T_ya_incluye_los_arribos_de_T():
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
