-- Supabase Table Setup for Time Sheet Magic
-- Run this SQL in your Supabase SQL Editor to create the required tables

-- Table for storing lead capture data (task 5.2.1)
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id TEXT,
    manager_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    store_name TEXT NOT NULL,
    store_address TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for storing analysis metadata (task 5.2.2)
CREATE TABLE IF NOT EXISTS analysis_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    status TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,
    employee_count INTEGER,
    total_violations INTEGER,
    total_hours DECIMAL,
    overtime_cost DECIMAL,
    processing_time_seconds DECIMAL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_leads_analysis_id ON leads(analysis_id);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);

CREATE INDEX IF NOT EXISTS idx_analysis_metadata_request_id ON analysis_metadata(request_id);
CREATE INDEX IF NOT EXISTS idx_analysis_metadata_status ON analysis_metadata(status);
CREATE INDEX IF NOT EXISTS idx_analysis_metadata_created_at ON analysis_metadata(created_at);

-- Enable Row Level Security (RLS) for security
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_metadata ENABLE ROW LEVEL SECURITY;

-- Create policies to allow service key access
-- Note: Adjust these policies based on your security requirements
CREATE POLICY "Allow service key access to leads" ON leads
    FOR ALL USING (true);

CREATE POLICY "Allow service key access to analysis_metadata" ON analysis_metadata
    FOR ALL USING (true);

-- Grant necessary permissions
GRANT ALL ON leads TO service_role;
GRANT ALL ON analysis_metadata TO service_role;
GRANT USAGE ON SCHEMA public TO service_role; 