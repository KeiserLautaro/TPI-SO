# -*- coding: utf-8 -*-
"""
Script de verificación exhaustiva del simulador estructurado.
Prueba:
1. Caso de estudio SRTF oficial (PlanifCPU-Resumen.pdf)
2. Particiones variables MVT, Best-Fit y coalescencia de memoria
3. Grado de multiprogramación (máximo 5 activos)
4. Retroceso de ciclos (paso atrás / undo)
"""
import sys
import os
import simulador

def probar_caso_estudio_srtf():
    print("\n--- TEST 1: Caso de Estudio SRTF Oficial ---")
    simulador.inicializar_memoria()
    
    p1 = simulador.crear_proceso("P1", 100, 0, 12)
    p2 = simulador.crear_proceso("P2", 100, 2, 3)
    p3 = simulador.crear_proceso("P3", 100, 3, 6)
    
    simulador.procesos_cargados_iniciales = [p1, p2, p3]
    simulador.reiniciar_simulacion()
    
    pasos = 0
    while not simulador.simulacion_terminada and pasos < 100:
        simulador.avanzar_un_ciclo_reloj()
        pasos += 1
        
    stats = simulador.calcular_estadisticas_finales()
    assert abs(stats["trp"] - 10.67) < 0.02
    assert abs(stats["tep"] - 3.67) < 0.02
    print("✓ Caso de estudio SRTF superado con éxito.")

def probar_best_fit_y_coalescencia():
    print("\n--- TEST 2: Memoria MVT (Best-Fit y Coalescencia) ---")
    simulador.inicializar_memoria()
    
    pA = simulador.crear_proceso("PA", 150, 0, 10)
    pB = simulador.crear_proceso("PB", 100, 0, 5)
    pC = simulador.crear_proceso("PC", 200, 0, 10)
    
    assert simulador.asignar_memoria_proceso(pA) == True
    assert simulador.asignar_memoria_proceso(pB) == True
    assert simulador.asignar_memoria_proceso(pC) == True
    
    pD = simulador.crear_proceso("PD", 50, 0, 4)
    assert simulador.asignar_memoria_proceso(pD) == False
    
    simulador.liberar_memoria_proceso("PB")
    assert simulador.asignar_memoria_proceso(pD) == True
    
    simulador.liberar_memoria_proceso("PA")
    simulador.liberar_memoria_proceso("PD")
    
    idx = simulador.buscar_hueco_best_fit(250)
    assert idx != -1
    assert simulador.tabla_particiones[idx]["tamano"] == 250
    print("✓ Asignación Best-Fit y coalescencia de huecos verificadas con éxito.")

def probar_limite_cinco_activos():
    print("\n--- TEST 3: Restricción de Máximo 5 Procesos Activos ---")
    simulador.inicializar_memoria()
    
    procesos = [simulador.crear_proceso(f"P{i}", 40, 0, 5) for i in range(1, 8)]
    simulador.procesos_cargados_iniciales = procesos
    simulador.reiniciar_simulacion()
    
    simulador.avanzar_un_ciclo_reloj()
    
    activos = simulador.contar_procesos_activos()
    print(f"Total activos en sistema: {activos} (debe ser <= 5)")
    assert activos == 5
    assert len(simulador.cola_nuevos) == 2
    print("✓ Restricción de máximo 5 activos verificada con éxito.")

def probar_retroceso_ciclos():
    print("\n--- TEST 4: Retroceso de Ciclos (Undo / Paso Atrás) ---")
    simulador.inicializar_memoria()
    p1 = simulador.crear_proceso("P1", 100, 0, 5)
    simulador.procesos_cargados_iniciales = [p1]
    simulador.reiniciar_simulacion()
    
    # T=0
    assert simulador.reloj_t == 0
    # Avanzar a T=1
    simulador.avanzar_un_ciclo_reloj()
    assert simulador.reloj_t == 1
    # Avanzar a T=2
    simulador.avanzar_un_ciclo_reloj()
    assert simulador.reloj_t == 2
    
    # Retroceder a T=1
    simulador.restaurar_instantanea_estado()
    assert simulador.reloj_t == 1
    # Retroceder a T=0
    simulador.restaurar_instantanea_estado()
    assert simulador.reloj_t == 0
    print("✓ Retroceso de ciclos verificado con éxito.")

if __name__ == "__main__":
    probar_caso_estudio_srtf()
    probar_best_fit_y_coalescencia()
    probar_limite_cinco_activos()
    probar_retroceso_ciclos()
    print("\n=========================================")
    print("¡TODAS LAS PRUEBAS DE VALIDACIÓN EXITOSAS!")
    print("=========================================")
