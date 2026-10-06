-- ==============================================================================
-- CHROMATOGRAPHY APP (GC-MS CLARUS 690) - SUPABASE DATABASE SCHEMA
-- ==============================================================================
-- Ejecuta este script en el SQL Editor de tu proyecto en Supabase.
-- ==============================================================================

-- 1. EXTENSIONES
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. TABLA: SAMPLES (Muestras analizadas y sus metadatos cromatográficos)
CREATE TABLE IF NOT EXISTS public.samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sample_name VARCHAR(255) NOT NULL,
    sample_code VARCHAR(100),
    analysis_date DATE DEFAULT CURRENT_DATE,
    column_type VARCHAR(255) DEFAULT 'Elite-5MS (30m x 0.25mm x 0.25µm)',
    carrier_gas VARCHAR(50) DEFAULT 'Helium',
    inlet_temperature VARCHAR(50) DEFAULT '250 °C',
    oven_program TEXT,
    split_ratio VARCHAR(50) DEFAULT '20:1',
    flow_rate VARCHAR(50) DEFAULT '1.0 mL/min',
    operator VARCHAR(100),
    notes TEXT,
    total_area DOUBLE PRECISION DEFAULT 0.0,
    peak_count INTEGER DEFAULT 0,
    original_file_name VARCHAR(255),
    storage_file_path TEXT,
    report_pdf_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. TABLA: PEAKS (Picos integrados del cromatograma)
CREATE TABLE IF NOT EXISTS public.peaks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sample_id UUID NOT NULL REFERENCES public.samples(id) ON DELETE CASCADE,
    peak_id INTEGER NOT NULL,
    retention_time DOUBLE PRECISION NOT NULL,
    area DOUBLE PRECISION NOT NULL,
    relative_area_pct DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_sample_peak UNIQUE (sample_id, peak_id)
);

-- 4. TABLA: IDENTIFICATIONS (Resultados de identificación IA + NIST por pico)
CREATE TABLE IF NOT EXISTS public.identifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sample_id UUID NOT NULL REFERENCES public.samples(id) ON DELETE CASCADE,
    peak_id INTEGER NOT NULL,
    compound_name VARCHAR(255) NOT NULL,
    iupac_name TEXT,
    cas_number VARCHAR(50),
    formula VARCHAR(100),
    molecular_weight DOUBLE PRECISION,
    confidence_level VARCHAR(20) DEFAULT 'Medium', -- 'High', 'Medium', 'Low'
    confidence_score DOUBLE PRECISION,            -- 0 to 100%
    nist_similarity DOUBLE PRECISION,             -- Score de similitud espectral NIST (0-1000 o 0-100%)
    identification_source VARCHAR(100) DEFAULT 'Gemini AI + NIST Library',
    chemical_family VARCHAR(100),
    retention_behavior_analysis TEXT,
    fragmentation_rationale TEXT,
    key_ions JSONB DEFAULT '[]'::jsonb,
    alternative_candidates JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_sample_peak_identification UNIQUE (sample_id, peak_id)
);

-- 5. TABLA: CHAT_MESSAGES (Historial de consultas al asistente de IA sobre cada muestra)
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sample_id UUID REFERENCES public.samples(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. ÍNDICES PARA BÚSQUEDA RÁPIDA
CREATE INDEX IF NOT EXISTS idx_samples_created_at ON public.samples (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_peaks_sample_id ON public.peaks (sample_id);
CREATE INDEX IF NOT EXISTS idx_identifications_sample_id ON public.identifications (sample_id);
CREATE INDEX IF NOT EXISTS idx_identifications_compound ON public.identifications (compound_name);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sample_id ON public.chat_messages (sample_id, created_at ASC);

-- 7. CONFIGURACIÓN DEL STORAGE BUCKET (Opcional si usas Supabase Storage)
-- En el panel de Supabase: Storage -> Create new bucket -> "chromatography-files" (público o con RLS)
INSERT INTO storage.buckets (id, name, public)
VALUES ('chromatography-files', 'chromatography-files', true)
ON CONFLICT (id) DO NOTHING;

-- 8. POLÍTICAS RLS (Row Level Security) - Acceso permisivo para API keys de servicio o anónimas
ALTER TABLE public.samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.peaks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access to samples" ON public.samples FOR SELECT USING (true);
CREATE POLICY "Allow public insert to samples" ON public.samples FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update to samples" ON public.samples FOR UPDATE USING (true);
CREATE POLICY "Allow public delete to samples" ON public.samples FOR DELETE USING (true);

CREATE POLICY "Allow public read access to peaks" ON public.peaks FOR SELECT USING (true);
CREATE POLICY "Allow public insert to peaks" ON public.peaks FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update to peaks" ON public.peaks FOR UPDATE USING (true);
CREATE POLICY "Allow public delete to peaks" ON public.peaks FOR DELETE USING (true);

CREATE POLICY "Allow public read access to identifications" ON public.identifications FOR SELECT USING (true);
CREATE POLICY "Allow public insert to identifications" ON public.identifications FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update to identifications" ON public.identifications FOR UPDATE USING (true);
CREATE POLICY "Allow public delete to identifications" ON public.identifications FOR DELETE USING (true);

CREATE POLICY "Allow public read access to chat" ON public.chat_messages FOR SELECT USING (true);
CREATE POLICY "Allow public insert to chat" ON public.chat_messages FOR INSERT WITH CHECK (true);
