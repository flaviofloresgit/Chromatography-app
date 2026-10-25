# 🧪 Chromatography AI — GC-MS Analysis & Compound Identification

> **Plataforma inteligente para la identificación y cuantificación de compuestos químicos en cromatografía de gases acoplada a espectrometría de masas (GC-MS)**, diseñada para datos de **PerkinElmer Clarus 690 / TurboMass (EI 70 eV)** con integración de la **biblioteca espectral NIST** y deducción analítica avanzada con **Google Gemini AI**.

---

## 🌟 Características Principales

1. **Lectura Directa de Archivos Excel del Equipo (Clarus 690 / TurboMass)**:
   - **Hoja 1 (`Chromatogram`)**: Tiempo de retención (RT) vs Señal (TIC - Total Ion Chromatogram).
   - **Hoja 2 (`Peaks`)**: Picos integrados con ID Peak, RT y Áreas cromatográficas.
   - **Hoja 3 (`Mass spectrum`)**: Espectros de masas completos con fragmentos $m/z$ e intensidades.
2. **Identificación Química con Gemini AI**:
   - Analiza patrones de fragmentación por Impacto Electrónico (EI 70 eV): ion molecular $[M]^{+\bullet}$, pérdidas neutras características ($-15$ metilo, $-18$ agua, etc.), reordenamiento de McLafferty, ion tropilio ($m/z\ 91$), etc.
   - Correlaciona el orden de elución y tiempos de retención según la fase estacionaria (columna no polar **Elite-5MS / DB-5MS**).
   - Detección de artefactos instrumentales y contaminantes: aire/vacío ($m/z\ 28, 32$), sangrado de columna / siloxanos ($m/z\ 73, 207, 281, 355$), disolventes o plastificantes.
   - Opcional: **Google Search Grounding** para consultar en tiempo real bases de datos oficiales (NIST Chemistry WebBook, PubChem, ChemSpider).
3. **Biblioteca Espectral NIST Ultra-Rápida (.MSP)**:
   - Indexación en SQLite de más de **240,000 espectros NIST**.
   - Búsqueda en **~6 milisegundos** por pico empleando el algoritmo estándar **Stein-Scott / Cosine similarity (Dot Product)**.
4. **Cuantificación Cromatográfica Automatizada**:
   - Cálculo automático de áreas relativas: $\text{Área \%} = \frac{\text{Área}_i}{\sum \text{Área}} \times 100\%$.
   - Resumen de pureza asignada, picos mayores, picos medios y trazas.
5. **Generación de Informes Oficiales en PDF (1 Clic)**:
   - Emisión instantánea de un informe de laboratorio profesional con ReportLab y Matplotlib: metadatos de muestra, gráfica TIC en alta resolución, tabla de cuantificación completa, justificación de IA y bloques de firma.
6. **Chat Asistente Químico Interactivo**:
   - Chatea con Gemini AI con todo el contexto cargado de la muestra: pregunta sobre pureza, contaminantes, explicación de fragmentación de cualquier pico o sugerencias para optimizar la rampa de horno.
7. **Historial Persistente con Supabase / Local**:
   - Integración nativa con **Supabase** (tablas PostgreSQL y Cloud Storage para archivos crudos).
   - Modo de respaldo local transparente (funciona 100% offline si aún no configuras tus credenciales).

---

## 🏛️ Arquitectura Desacoplada (Clean Architecture)

El proyecto está diseñado siguiendo una estricta separación de responsabilidades: **la lógica del programa es 100% independiente de Streamlit**. Si en el futuro tu organización decide migrar a FastAPI, Django, React o una CLI, todo el núcleo analítico (`core/`) se reutiliza intacto sin modificar una sola línea de código:

```
Chromatography app/
├── core/                                     # 100% LÓGICA DE NEGOCIO PURA (SIN DEPENDENCIAS DE STREAMLIT)
│   ├── models.py                             # Modelos de dominio (SampleAnalysis, PeakData, MassSpectrum, etc.)
│   ├── parsers/                              # Parsers de archivos Excel (Chromatogram, Peaks, Mass spectrum)
│   │   └── excel_parser.py
│   ├── spectral/                             # Algoritmo de similitud espectral y matcher NIST
│   │   ├── similarity.py                     # Algoritmo Stein-Scott / Cosine similarity (dot product)
│   │   ├── msp_parser.py                     # Parser streaming del formato .MSP
│   │   └── library_index.py                  # Indexador y buscador SQLite de 240k+ espectros NIST
│   ├── quantification/                       # Cuantificación y estadísticas cromatográficas
│   │   └── calculator.py                     # Normalización de áreas relativas %
│   ├── ai/                                   # Integración con Google Gemini AI
│   │   ├── prompt_builder.py                 # Reglas químicas para Clarus 690, columnas y fragmentación EI
│   │   └── gemini_client.py                  # Cliente de Gemini (google-genai) con modo simulación
│   ├── storage/                              # Capa de persistencia e historial
│   │   ├── repository_interface.py           # Interfaz abstracta de repositorio
│   │   ├── supabase_repo.py                  # Implementación Supabase (Postgres + Cloud Storage)
│   │   └── local_repo.py                     # Fallback local (JSON / disco) para trabajo sin conexión
│   └── reporting/                            # Generador de reportes PDF oficiales (ReportLab + Matplotlib)
│       └── pdf_generator.py
│
├── ui/                                       # CAPA EXCLUSIVA DE PRESENTACIÓN STREAMLIT
│   ├── styles.py                             # Sistema de diseño, fuentes y CSS personalizado
│   ├── charts.py                             # Gráficos interactivos Plotly (TIC y Espectro de masas)
│   ├── components.py                         # Tarjetas de métricas, badges e información de pico
│   └── views/                                # Vistas modulares
│       ├── upload_view.py                    # Formulario de condiciones y carga de archivos
│       ├── analysis_view.py                  # Dashboard de resultados, gráficos y descarga PDF
│       ├── chat_view.py                      # Chat conversacional con el asistente de IA
│       └── history_view.py                   # Historial de muestras y recarga de análisis
│
├── database/                                 # Base de datos NIST (.MSP y .sqlite indexado)
│   └── Base de Datos NIST.MSP
│
├── docs/                                     # Manuales oficiales (Clarus 690, TurboMass, AMDIS)
├── supabase/
│   └── schema.sql                            # Script de creación de tablas en Supabase
│
├── .env.example                              # Plantilla de variables de entorno
├── .gitignore                                # Exclusiones para Git (evita exceder 100MB de GitHub)
├── requirements.txt                          # Dependencias de Python
└── app.py                                    # Punto de entrada de la aplicación Streamlit
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/chromatography-app.git
cd "Chromatography app"
```

### 2. Crear Entorno Virtual e Instalar Dependencias
```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno (`.env`)
Copia el archivo de plantilla `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` con tus claves:
```env
# Clave gratuita de Google Gemini (https://aistudio.google.com/)
GEMINI_API_KEY=tu_api_key_de_gemini

# Modelo recomendado (rápido y con alta cuota)
GEMINI_MODEL=gemini-3.5-flash-lite

# Opcional: Credenciales de Supabase (si deseas historial en la nube)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu_anon_o_service_key
```

### 4. Indexar la Base de Datos NIST (Opcional - La app lo hace automáticamente al primer inicio)
Para pre-indexar los 242,466 espectros del archivo `database/Base de Datos NIST.MSP` en la base de datos SQLite local:
```bash
python -c "from core.spectral.library_index import NistLibraryMatcher; m = NistLibraryMatcher(); m.build_index()"
```
*(Tarda solo ~13 segundos y genera `database/nist_library.sqlite` para búsquedas sub-milisegundo).*

### 5. Iniciar la Aplicación
```bash
streamlit run app.py
```
Abre tu navegador en `http://localhost:8501`.

---

## ☁️ Configuración de Supabase (Paso a Paso)

Si deseas sincronizar los análisis e historial con tu cuenta de Supabase:

1. Ingresa a tu panel en [Supabase](https://supabase.com/).
2. Ve al **SQL Editor** y ejecuta el contenido del archivo [`supabase/schema.sql`](supabase/schema.sql). Esto creará:
   - Tabla `samples`: Metadatos cromatográficos y condiciones de la corrida.
   - Tabla `peaks`: Picos integrados con RT y área.
   - Tabla `identifications`: Compuestos identificados, fórmulas, CAS, similitud NIST y deducción de IA.
   - Tabla `chat_messages`: Historial de conversación con la IA por muestra.
   - Políticas RLS de seguridad.
   - Storage Bucket `chromatography-files` para almacenar los archivos Excel originales y reportes.
3. Copia tu `Project URL` y `API Key` (anon o service_role) de *Settings -> API* en tu archivo `.env` o directamente en la barra lateral de la app.

---

## 🌐 Despliegue en Streamlit Cloud

1. Sube tu proyecto a tu repositorio de GitHub:
   ```bash
   git add .
   git commit -m "feat: Aplicacion de cromatografia GC-MS con Gemini e indexador NIST"
   git push origin main
   ```
   *(Nota: El archivo `.gitignore` ya está configurado para no subir el archivo raw `.MSP` de 275MB que supera el límite estricto de 100MB de GitHub).*
2. En [Streamlit Community Cloud](https://share.streamlit.io/), selecciona tu repositorio y rama `main`, con archivo principal `app.py`.
3. En **Settings -> Secrets**, agrega tus variables:
   ```toml
   GEMINI_API_KEY = "tu_api_key_aqui"
   GEMINI_MODEL = "gemini-3.5-flash-lite"
   SUPABASE_URL = "https://tu-proyecto.supabase.co"
   SUPABASE_KEY = "tu_clave_supabase"
   ```
4. ¡Listo! Tu app estará en línea accesible desde cualquier navegador.

---

## 🔬 Referencias Instrumentales

- **Cromatógrafo**: PerkinElmer Clarus 690 Gas Chromatograph
- **Espectrómetro de Masas**: Clarus SQ 8 MS (Quadrupole, 70 eV Electron Ionization)
- **Software**: PerkinElmer TurboMass / AMDIS
- **Columna de Referencia**: Elite-5MS (5% Difenil / 95% Dimetilpolisiloxano, 30m × 0.25mm × 0.25µm)
- Documentación técnica completa disponible en la carpeta local [`docs/`](docs/).
