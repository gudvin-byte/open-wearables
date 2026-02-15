# Ultrahuman Real Data Testing

This directory contains scripts for testing the Ultrahuman integration with real data.

## test_ultrahuman_real_data.py

A comprehensive script for testing Ultrahuman integration with real API data.

### Prerequisites

1. **Ultrahuman Developer Credentials**
   - Get credentials from the [Ultrahuman Developer Portal](https://vision.ultrahuman.com/developer-docs)
   - You'll need:
     - Client ID
     - Client Secret
     - Redirect URI (must use HTTPS)

2. **Environment Variables**
   Set these in your `.env` file:

   ```bash
   ULTRAHUMAN_CLIENT_ID=your-client-id
   ULTRAHUMAN_CLIENT_SECRET=your-client-secret
   ULTRAHUMAN_REDIRECT_URI=https://your-domain.com/api/v1/oauth/ultrahuman/callback
   ULTRAHUMAN_DEFAULT_SCOPE=ring_data cgm_data profile
   ```

   **Important:** Ultrahuman requires HTTPS redirect URLs. For local testing, use [ngrok](https://ngrok.com):

   ```bash
   # Start ngrok
   ngrok http 8000

   # Use the ngrok URL as your redirect URI
   ULTRAHUMAN_REDIRECT_URI=https://your-ngrok-url.ngrok.io/api/v1/oauth/ultrahuman/callback
   ```

3. **Database Setup**
   Ensure your database is running:
   ```bash
   docker compose up db -d
   ```

### Usage Modes

#### 1. Check Credentials Only

Verify that your Ultrahuman credentials are properly configured:

```bash
cd backend
uv run python scripts/test_ultrahuman_real_data.py --mode check-creds
```

#### 2. Interactive Mode (Default)

Step-by-step OAuth flow and data testing:

```bash
cd backend
uv run python scripts/test_ultrahuman_real_data.py
# or
uv run python scripts/test_ultrahuman_real_data.py --mode interactive
```

This will:
1. Generate an OAuth authorization URL
2. Guide you through the authorization flow
3. Fetch and display your user profile
4. Optionally fetch daily metrics
5. Optionally save data to the database and test full sync

#### 3. Fetch-Only Mode

If you already have a valid access token, fetch data without OAuth:

```bash
cd backend
uv run python scripts/test_ultrahuman_real_data.py \
  --mode fetch-only \
  --token YOUR_ACCESS_TOKEN \
  --date 2024-01-15
```

Parameters:
- `--token`: Your existing Ultrahuman access token (required)
- `--date`: Date to fetch metrics in YYYY-MM-DD format (optional, defaults to yesterday)

### What Gets Tested

1. **OAuth Flow**
   - Authorization URL generation
   - Token exchange
   - User profile fetching

2. **API Data Fetching**
   - Daily metrics endpoint
   - Sleep data
   - Recovery metrics
   - Activity samples (HR, HRV, temperature, steps)

3. **Data Normalization**
   - Sleep data mapping to EventRecord
   - Activity samples mapping to DataPointSeries
   - Proper timestamp handling

4. **Database Operations**
   - Creating test users
   - Saving user connections
   - Storing normalized data
   - Querying saved records

### Example Output

```
============================================================
  Checking Ultrahuman Credentials
============================================================

✓ Ultrahuman credentials found:
  - Client ID: RRq5RtPLJB...
  - Redirect URI: https://ultrahuman.example.com/api/v1/oauth/ultrahuman/callback

============================================================
  Fetch User Profile
============================================================

✓ User profile fetched:
  - User ID: 12345
  - Username: test_user
  - Email: user@example.com

============================================================
  Fetch Daily Metrics for 2024-01-15
============================================================

✓ Daily metrics fetched:
  - Available metric types: Sleep, hr, hrv, temp, steps

============================================================
  Test Full Data Sync
============================================================

Syncing data from 2024-01-13 to 2024-01-16

✓ Sync completed!
  - Sleep sessions synced: 3
  - Activity samples saved: 2540
  - Recovery days synced: 0
  - Failed days: 0

============================================================
  Query Saved Data
============================================================

Sleep records found: 3

  - Date: 2024-01-15
    Duration: 7h 45m
    External ID: sleep-2024-01-15

  - Date: 2024-01-14
    Duration: 8h 12m
    External ID: sleep-2024-01-14

============================================================
  Testing Complete
============================================================
```

### Troubleshooting

#### "Ultrahuman credentials not found"
- Ensure environment variables are set in your `.env` file
- Restart your development environment after updating `.env`

#### "HTTP error: 401 Unauthorized"
- Your access token may have expired
- Try running the OAuth flow again to get a new token

#### "HTTP error: 403 Forbidden"
- Check that your redirect URI matches exactly what's configured in Ultrahuman
- Ensure your Ultrahuman app has the required permissions

#### "No data available for this date"
- The specified date may not have any data (e.g., future dates, or days without wearable usage)
- Try yesterday or another recent date

#### Database Errors
- Ensure PostgreSQL is running: `docker compose ps db`
- Check database connection settings in your `.env` file
- Run database migrations: `make migrate`

### Security Notes

- **Never commit your `.env` file** or any credentials to version control
- Use environment variables for all sensitive data
- If using ngrok for local testing, be aware that your redirect URI is public
- Rotate your client secrets regularly
- Revoke unused OAuth tokens from Ultrahuman

### Next Steps

After successful real-data testing:

1. **Verify Data Quality**: Check that the data in the database looks correct
2. **Test Frontend**: Ensure the data appears correctly in the dashboard
3. **Edge Cases**: Test with various data scenarios (missing data, outliers, etc.)
4. **Performance**: Test with larger date ranges to ensure performance is acceptable

### Related Documentation

- [Ultrahuman API Docs](https://vision.ultrahuman.com/developer-docs)
- [Backend AGENTS.md](../AGENTS.md)
- [Provider Testing Guide](../../tests/providers/ultrahuman/README.md)
