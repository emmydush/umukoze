-- Initialize PostgreSQL database for Umukozi
-- This script runs when the database container starts

-- Create database if it doesn't exist
-- (PostgreSQL handles this automatically with POSTGRES_DB)

-- Set up extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE umukozi_db TO umukozi_user;
