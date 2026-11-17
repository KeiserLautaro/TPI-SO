from planificador import elegir_proceso_srtf, numero_de_id
from simulacion import crear_proceso


def proceso(id_p, arribo, restante):
    return crear_proceso(id_p, 10, arribo, restante)


def test_gana_menor_restante():
    a, b = proceso("P1", 0, 5), proceso("P2", 1, 3)
    assert elegir_proceso_srtf(None, [a, b]) is b


def test_empate_con_cpu_sigue_el_que_esta():
    en_cpu, listo = proceso("P1", 0, 3), proceso("P2", 1, 3)
    assert elegir_proceso_srtf(en_cpu, [listo]) is en_cpu


def test_expropia_si_es_estrictamente_menor():
    en_cpu, listo = proceso("P1", 0, 4), proceso("P2", 1, 3)
    assert elegir_proceso_srtf(en_cpu, [listo]) is listo


def test_empate_entre_listos_gana_el_que_llego_primero():
    # Aunque P3 esté primero en la lista, P2 llegó antes
    p3, p2 = proceso("P3", 5, 4), proceso("P2", 3, 4)
    assert elegir_proceso_srtf(None, [p3, p2]) is p2


def test_empate_mismo_arribo_gana_menor_id_numerico():
    p10, p2 = proceso("P10", 0, 4), proceso("P2", 0, 4)
    assert elegir_proceso_srtf(None, [p10, p2]) is p2


def test_numero_de_id():
    assert numero_de_id("P10") == 10
    assert numero_de_id("P2") < numero_de_id("P10")
