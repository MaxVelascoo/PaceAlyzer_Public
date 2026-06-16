# PaceAlyzer Public

Este repositorio contiene una version publica y limpiada de PaceAlyzer, desarrollada como parte de un Trabajo Final de Grado en Ingenieria Informatica.

PaceAlyzer es un prototipo full-stack para la planificacion personalizada de entrenamientos ciclistas mediante lenguaje natural. El sistema combina un backend conversacional multiagente, un pipeline RAG sobre una biblioteca de plantillas de entrenamiento, integracion con datos deportivos y una interfaz web desarrollada con Next.js.

## Nota sobre esta version

Esta carpeta no es una copia exacta del repositorio privado utilizado durante todo el desarrollo ni del codigo desplegado en produccion. Es una version preparada para entrega y revision academica junto con la memoria del TFG.

Se ha limpiado el contenido para facilitar su lectura y evitar incluir material innecesario o sensible. En particular, esta version excluye:

- Archivos `.env`, credenciales, claves privadas y configuraciones locales.
- Entornos virtuales, dependencias instaladas y carpetas generadas automaticamente.
- Outputs completos de experimentos, caches, builds y artefactos de compilacion.
- Documentacion interna, notas de trabajo y codigo obsoleto que no forma parte de la version final descrita en la memoria.

Los archivos `.env.example` incluidos en `backend/` y `frontend/` sirven como referencia de las variables necesarias para ejecutar el proyecto en un entorno propio.

## Requisitos para ejecutar el sistema completo

Para que la aplicacion funcione de forma completa no basta con ejecutar el frontend y el backend. Tambien es necesario disponer de una base de datos Supabase/PostgreSQL con pgvector y con el esquema esperado por el proyecto.

En concreto, el backend espera encontrar tablas como `users`, `planned_workouts`, `workout_library`, `chat_sessions`, `chat_messages`, `daily_metrics`, `weekly_summaries`, `strava_accounts`, `events` y `blocked_days`, entre otras. Ademas, las funcionalidades RAG requieren que la tabla `workout_library` contenga plantillas de entrenamiento con sus metadatos y embeddings generados.

Esta version publica no incluye una base de datos exportada ni credenciales reales. Por tanto, el codigo permite revisar la implementacion y puede servir como base para una instalacion propia, pero para reproducir el comportamiento completo descrito en la memoria es necesario crear/configurar la base de datos correspondiente y completar las variables de entorno.

## Estructura del repositorio

- `backend/`: backend en FastAPI, grafo multiagente con LangGraph, servicios RAG, integracion con Supabase/PostgreSQL + pgvector, herramientas controladas y scripts de evaluacion.
- `frontend/`: aplicacion web en Next.js para dashboard, calendario, vista diaria, metricas y chat conversacional.
- `evaluation/`: datasets YAML usados en los experimentos de evaluacion descritos en la memoria.

## Componentes principales

- Grafo multiagente con `operator`, `librarian`, `workout_editor`, `nutrition_editor`, `week_planner` y `explainer`.
- Pipeline RAG hibrido sobre `workout_library`, combinando filtrado SQL, busqueda vectorial con pgvector y reranking con metadatos.
- Integracion con modelos de lenguaje y embeddings de OpenAI.
- Validaciones tecnicas antes de persistir entrenamientos o cambios de nutricion.
- Instrumentacion de peticiones para medir latencia, ruta multiagente, tokens, herramientas ejecutadas y resumen RAG.
- Scripts de evaluacion para los experimentos de recuperacion RAG, routing del Operator y ejecucion end-to-end.

## Ejecucion del backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Antes de ejecutar el backend es necesario completar las variables de entorno en `.env`, especialmente las relacionadas con Supabase y OpenAI.

## Ejecucion del frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Antes de ejecutar el frontend es necesario completar las variables de entorno en `.env.local`, incluyendo la URL del backend y la configuracion publica de Supabase.

## Scripts de evaluacion

El backend incluye los scripts principales utilizados para los experimentos del TFG:

- `scripts/experiments/evaluate_librarian_rag.py`
- `scripts/experiments/evaluate_operator_routing.py`
- `scripts/experiments/evaluate_end_to_end.py`

Los datasets correspondientes estan disponibles en la carpeta `evaluation/`.

## Alcance

El objetivo de este repositorio es permitir revisar la arquitectura, la organizacion del codigo y los componentes principales implementados durante el TFG. Para entender el diseno completo, las decisiones tecnicas, los experimentos y las limitaciones del sistema, se debe consultar la memoria entregada junto con este codigo.
