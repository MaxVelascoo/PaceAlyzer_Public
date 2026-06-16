# Taxonomía de `workout_library` para PaceAlyzer

Este documento resume la taxonomía revisada manualmente para las plantillas de entrenamiento ciclista de `workout_library`.

La taxonomía se utiliza para:

- estructurar el `embedding_text` de cada plantilla;
- guiar el prompt del agente `Librarian`;
- construir un *silver ground truth* mínimo para evaluar el pipeline RAG;
- analizar la cobertura del catálogo por tipo de sesión, zona, fatiga y carga.

Total de plantillas revisadas: **80**.

---

## 1. `primary_goal`

Campo principal que representa el objetivo fisiológico o funcional dominante de la sesión.

| primary_goal         | count |
| -------------------- | ----- |
| activation_pre_race  | 3     |
| anaerobic_frc        | 8     |
| endurance            | 12    |
| mixed                | 8     |
| neuromuscular_sprint | 7     |
| recovery             | 7     |
| strength_torque      | 6     |
| sweetspot            | 9     |
| tempo                | 4     |
| threshold            | 7     |
| vo2max               | 9     |

### Valores

| Valor | Descripción |
| ----- | ----------- |
| `activation_pre_race` | Sesiones de activación precompetitiva u *openers* suaves cuyo objetivo es llegar fresco a competición. |
| `anaerobic_frc` | Sesiones centradas en FRC, capacidad anaeróbica, tolerancia al lactato y esfuerzos por encima de FTP. |
| `endurance` | Rodajes aeróbicos de base, principalmente Z2, orientados a resistencia, volumen y durabilidad. |
| `mixed` | Sesiones híbridas donde no domina una única familia fisiológica: progresivas, combinadas, tempo-threshold-VO2, etc. |
| `neuromuscular_sprint` | Sprints cortos, explosividad, pico de potencia, velocidad de piernas y coordinación neuromuscular. |
| `recovery` | Recuperación activa, rodajes regenerativos, descarga y movilidad con baja carga fisiológica. |
| `strength_torque` | Fuerza específica sobre la bici, baja cadencia, torque, arrancadas o trabajo de fuerza-resistencia. |
| `sweetspot` | Trabajo subumbral cercano al FTP, normalmente en la banda 88-94% FTP. |
| `tempo` | Trabajo sostenido de tempo, aproximadamente Z3, orientado a resistencia muscular y capacidad aeróbica. |
| `threshold` | Trabajo específico de umbral/FTP, normalmente Z4, con intervalos cerca del 98-102% FTP. |
| `vo2max` | Trabajo de potencia aeróbica máxima, Z5, intervalos VO2max y PAM. |

---

## 2. `work_zone`

Campo que representa la zona o rango de zonas dominante del estímulo principal.

| work_zone | count |
| --------- | ----- |
| mixed     | 12    |
| Z1        | 7     |
| Z2        | 12    |
| Z3        | 4     |
| Z3_Z4     | 11    |
| Z4        | 6     |
| Z4_Z5     | 1     |
| Z5        | 9     |
| Z6_Z7     | 18    |

### Valores

| Valor | Descripción |
| ----- | ----------- |
| `Z1` | Recuperación activa, descarga y rodaje muy suave. |
| `Z2` | Fondo aeróbico, endurance y base. |
| `Z3` | Tempo sostenido. |
| `Z3_Z4` | Sweet spot o transición tempo alto-subumbral. |
| `Z4` | Umbral FTP / threshold. |
| `Z4_Z5` | Sesiones de umbral con componente VO2 o fatiga alta. |
| `Z5` | VO2max / potencia aeróbica máxima. |
| `Z6_Z7` | Sprints, neuromuscular, FRC, anaeróbico o torque explosivo. |
| `mixed` | Sesiones con varios dominios fisiológicos relevantes, sin una única zona dominante. |

---

## 3. `fatigue_suitability`

Campo que indica en qué estado de fatiga del atleta tiene sentido seleccionar la plantilla.

| fatigue_suitability | count |
| ------------------- | ----- |
| fatigued_ok         | 4     |
| fresh_only          | 60    |
| normal_or_fresh     | 9     |
| very_fatigued_ok    | 7     |

### Valores

| Valor | Descripción |
| ----- | ----------- |
| `very_fatigued_ok` | Adecuada incluso con fatiga alta. Normalmente recuperación activa o descarga. |
| `fatigued_ok` | Aceptable con cierta fatiga, siempre que la sesión sea de baja exigencia. |
| `normal_or_fresh` | Requiere estado normal o fresco; no recomendable con fatiga marcada. |
| `fresh_only` | Requiere atleta fresco o bien recuperado. Aplica a sesiones intensas, técnicas o de alta calidad. |

---

## 4. `load_level`

Campo que representa la carga global esperada de la sesión, combinando duración, intensidad y TSS estimado.

| load_level | count |
| ---------- | ----- |
| high       | 34    |
| low        | 7     |
| medium     | 18    |
| very_high  | 17    |
| very_low   | 4     |

### Valores

| Valor | Descripción |
| ----- | ----------- |
| `very_low` | Carga mínima, típica de recuperación muy suave. |
| `low` | Carga baja, útil para recuperación, activación ligera o sesiones muy controladas. |
| `medium` | Carga moderada, asumible dentro de una semana normal de entrenamiento. |
| `high` | Carga alta, requiere planificación y cierto nivel de frescura. |
| `very_high` | Carga muy alta, reservada para atletas frescos y sesiones clave. |

---

## 5. Uso recomendado en `embedding_text`

Cada plantilla debería construir su `embedding_text` con una estructura estable y semánticamente alineada con las queries generadas por el agente `Librarian`.

Formato recomendado:

```text
TITLE: <title>

SUMMARY: <descripción semántica de la sesión, evitando depender de números como único significado>

RELATED_CONCEPTS: <lista de conceptos en español e inglés relevantes para recuperación semántica>

SEMANTIC_LABELS:
primary_goal=<primary_goal>
secondary_goals=<secondary_goals separados por coma>
work_zone=<work_zone>
structure_type=<structure_type>
fatigue_suitability=<fatigue_suitability>
load_level=<load_level>
duration_class=<duration_class>
```

---

## 6. Uso recomendado en el agente `Librarian`

El agente que genera la query semántica debería usar una estructura compatible con el `embedding_text`.

Ejemplo para una petición de umbral en subida:

```text
SUMMARY: Sesión de ciclismo orientada a desarrollar umbral FTP en subida mediante intervalos largos en Z4. El atleta necesita trabajo de threshold, pacing, tolerancia al lactato y potencia sostenida.

RELATED_CONCEPTS: FTP, threshold, umbral, Z4, climbing, subida, sustained power, pacing, lactate tolerance

SEMANTIC_LABELS:
primary_goal=threshold
secondary_goals=ftp_development,threshold_power,climbing_power,lactate_tolerance,pacing
work_zone=Z4
structure_type=long_intervals
fatigue_suitability=fresh_only
load_level=high
duration_class=medium
```

---

## 7. Uso como silver ground truth

Esta taxonomía puede utilizarse para construir un *silver ground truth* mínimo sin dataset externo.

Una plantilla puede considerarse relevante para una query si cumple, por ejemplo:

1. coincide el `primary_goal`, o pertenece a una familia compatible;
2. coincide o es compatible el `work_zone`;
3. coincide o es compatible el `structure_type`;
4. comparte al menos un elemento relevante en `secondary_goals`;
5. respeta las restricciones de fatiga y carga del contexto del atleta.

Escala sugerida de relevancia:

| Grado | Significado |
| ----- | ----------- |
| 3 | Muy relevante: coincide objetivo principal, zona, estructura y contexto. |
| 2 | Relevante: coincide objetivo principal y varios metadatos importantes. |
| 1 | Parcialmente relevante: fisiológicamente cercano, pero no ideal. |
| 0 | No relevante. |

Métricas recomendadas para el experimento:

| Fase del RAG | Métricas |
| ------------ | -------- |
| Filtro SQL | Candidate Recall, número de candidatos, cobertura por duración |
| Búsqueda vectorial | Recall@10, Recall@20, MRR@20, Hit@3 |
| Reranking | Precision@3, Hit@1, Hit@3, MRR@3, nDCG@3 |

---

## 8. Nota sobre cobertura

La distribución muestra que el catálogo está concentrado en sesiones intensas (`fresh_only`) y carga alta (`high`/`very_high`). Esto es importante para interpretar resultados del RAG: algunas queries pueden fallar no por el pipeline, sino por falta de cobertura real en el catálogo.

Ejemplo: si una query pide una estructura muy específica no representada en las plantillas, el fallo debe clasificarse como **problema de cobertura del catálogo**, no necesariamente como error de similitud vectorial.
