# Supabase Setup Guide for Time Sheet Magic

## Why No Data in Supabase?

The most likely reason you're not seeing data in your Supabase database is that **the required tables haven't been created yet**. The backend code is configured to write to Supabase, but it needs the proper database schema to be set up first.

## Quick Fix: Set Up Required Tables

### Step 1: Access Your Supabase Dashboard

1. Go to [supabase.com](https://supabase.com)
2. Sign in to your account
3. Navigate to your project dashboard

### Step 2: Create the Required Tables

1. In your Supabase dashboard, go to the **SQL Editor**
2. Copy and paste the contents of `backend/setup_supabase_tables.sql`
3. Click **Run** to execute the SQL

This will create:
- **`leads`** table - stores lead capture data (manager info, store details)
- **`analysis_metadata`** table - stores analysis metadata (file info, processing results)

### Step 3: Verify the Setup

Run the test script to verify everything is working:

```bash
cd backend
python test_supabase_connection.py
```

This will:
- ✅ Check environment variables
- ✅ Test Supabase connection
- ✅ Test data insertion
- ✅ Test data querying

## What Data Gets Stored in Supabase?

### Analysis Metadata Table
Every time someone uploads a timesheet file, the system logs:
- Request ID and filename
- Processing status (success/failure)
- File size and type
- Number of employees processed
- Total violations found
- Processing time
- Error messages (if any)

### Leads Table
When someone submits their contact information after analysis:
- Manager name and email
- Phone number
- Store name and address
- Analysis ID (links to the analysis)

## Environment Variables

Your Fly.dev backend already has the correct environment variables set:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_KEY` - Service role key for database access

You can verify these are set with:
```bash
flyctl secrets list --app timesheet-magic-backend
```

## Troubleshooting

### If the test script fails:

1. **"Supabase client not available"**
   - Check that environment variables are set correctly
   - Verify your Supabase project is active

2. **"Table doesn't exist" errors**
   - Run the SQL setup script in your Supabase dashboard
   - Check that tables were created successfully

3. **Permission errors**
   - Verify you're using the service role key, not the anon key
   - Check that RLS policies are set up correctly

### Check Your Data

After running a few analyses and lead submissions, you can view your data in Supabase:

1. Go to **Table Editor** in your Supabase dashboard
2. Select the `analysis_metadata` table to see processing logs
3. Select the `leads` table to see captured lead information

## Data Flow

Here's how data flows into Supabase:

1. **File Upload** → Analysis starts → Metadata logged to `analysis_metadata`
2. **Analysis Complete** → Success/failure status updated in `analysis_metadata`
3. **Lead Submission** → Contact info stored in `leads` table

## Security Notes

The tables are set up with Row Level Security (RLS) enabled and policies that allow full access to the service role. In production, you may want to:

- Create more restrictive policies
- Set up user authentication
- Add data retention policies
- Enable audit logging

## Next Steps

1. Run the SQL setup script
2. Test the connection with the test script
3. Upload a timesheet file and submit lead info
4. Check your Supabase dashboard to see the data!

The backend is already configured to write to Supabase - you just needed the tables to exist first. 