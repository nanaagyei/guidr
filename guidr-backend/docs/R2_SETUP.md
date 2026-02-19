# Cloudflare R2 Object Storage Setup Guide

This guide explains how to configure Cloudflare R2 for document storage in Guidr.

## What You Need

For **S3-compatible API access** (which is what Guidr uses), you only need:

1. ✅ **Account ID** - Your Cloudflare account ID
2. ✅ **S3 API Access Key ID** - Created in R2 dashboard
3. ✅ **S3 API Secret Access Key** - Created with the Access Key ID
4. ✅ **Bucket Name** - Your R2 bucket name

## What You DON'T Need

- ❌ **Account API Token** - Not needed for S3-compatible operations
- ❌ **User API Token** - Not needed for S3-compatible operations

These tokens are only required if you're using Cloudflare's REST API directly, not for S3-compatible operations with boto3.

## Getting Your Credentials

### Step 1: Get Your Account ID

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Your Account ID is visible in the right sidebar on most pages
3. Or go to any R2 bucket page - the Account ID is in the URL: `https://dash.cloudflare.com/{ACCOUNT_ID}/r2/...`

### Step 2: Create S3 API Credentials

1. Go to **R2** → **Manage R2 API Tokens**
   - Or navigate to: `https://dash.cloudflare.com/{ACCOUNT_ID}/r2/api-tokens`
2. Click **Create API token**
3. Configure the token:
   - **Token name**: `guidr-production` (or your preferred name)
   - **Permissions**: 
     - ✅ **Object Read & Write** (or **Admin Read & Write** if you need bucket management)
   - **TTL**: Optional expiration date (leave blank for no expiration)
   - **Allow List Operations**: ✅ (recommended)
4. Click **Create API Token**
5. **IMPORTANT**: Copy both values immediately:
   - **Access Key ID** - This is your `R2_ACCESS_KEY_ID`
   - **Secret Access Key** - This is your `R2_SECRET_ACCESS_KEY` (shown only once!)

### Step 3: Get Your Bucket Name

1. Go to **R2** → **Buckets**
2. Find your bucket (or create one if you haven't)
3. The bucket name is what you see in the list

## Environment Variables Setup

Add these to your `.env` file in the `guidr-backend` directory:

```bash
# Cloudflare R2 Configuration
R2_ACCOUNT_ID=your_account_id_here
R2_ACCESS_KEY_ID=your_access_key_id_here
R2_SECRET_ACCESS_KEY=your_secret_access_key_here
R2_BUCKET_NAME=your_bucket_name_here
```

### Example `.env` file

```bash
DATABASE_URL=postgresql://guidr_user:guidr_password@localhost:5432/guidr_db
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production-min-32-chars
REDIS_URL=redis://localhost:6379/0
ENV=development

# Email configuration for 2FA
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
EMAIL_FROM=nanakwameagyeituffour@gmail.com

# Cloudflare R2 Configuration
R2_ACCOUNT_ID=abc123def456789
R2_ACCESS_KEY_ID=a1b2c3d4e5f6g7h8i9j0
R2_SECRET_ACCESS_KEY=w0x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6n7o8p9q0
R2_BUCKET_NAME=guidr-documents
```

## Phase 1 Data Pipeline Environment Variables

In addition to the R2 settings above, the data-ingestion stack relies on the following environment variables (see `.env.example` for defaults):

| Key | Purpose |
| --- | --- |
| `COLLEGE_SCORECARD_API_KEY` | Required to call the U.S. Department of Education College Scorecard API |
| `MEILISEARCH_HOST` / `MEILISEARCH_MASTER_KEY` | Configures the self-hosted Meilisearch instance for fast querying |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | Optional LLM providers that power the structured extraction flow |
| `SCRAPER_USER_AGENT`, `SCRAPER_DELAY_SECONDS`, `SCRAPER_MAX_RETRIES` | Control polite scraping defaults for IPEDS/Scrapy jobs |
| `ENABLE_LLM_EXTRACTION`, `LLM_EXTRACTION_MODEL` | Toggle LLM-powered extraction and choose a preferred model |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `OPENAI_EMBEDDING_MODEL` | Select the embedding backend (local Sentence-Transformers vs OpenAI) |

Set these values before running `python scripts/seed_from_apis.py` or the `/ingestion/*` API endpoints so the pipeline can authenticate with each service.

## Verifying Your Setup

After adding the credentials, verify the configuration:

### Test 1: Check Configuration Loading

Start your backend server:
```bash
cd guidr-backend
uvicorn src.main:app --reload --port 8000
```

Check the logs - there should be no errors about missing R2 credentials.

### Test 2: Test File Upload (via API)

1. Make sure you're logged in (have a valid JWT token)
2. Request an upload URL:
   ```bash
   curl -X POST http://localhost:8000/documents/upload-url \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "filename": "test.txt",
       "document_type": "transcript"
     }'
   ```
3. You should receive a presigned upload URL if R2 is configured correctly

## Troubleshooting

### Error: "Storage not configured"

This means one or more R2 environment variables are missing or empty. Check:
- ✅ All 4 variables are set in `.env`
- ✅ No typos in variable names
- ✅ Values don't have extra spaces or quotes

### Error: "Access Denied" or "403 Forbidden"

This usually means:
- ❌ Incorrect Access Key ID or Secret Access Key
- ❌ API token doesn't have the right permissions
- ❌ Bucket name is incorrect
- ❌ Access Key ID and Secret Access Key don't match (they're a pair)

**Solution**: Create a new S3 API token and ensure it has "Object Read & Write" permissions.

### Error: "Bucket not found"

- ❌ Bucket name is incorrect
- ❌ Bucket exists in a different Cloudflare account
- ❌ Bucket was deleted

**Solution**: Double-check the bucket name in your R2 dashboard.

### Error: "Endpoint URL incorrect"

This shouldn't happen with the current code, but if you see connection errors:
- ✅ Verify your Account ID is correct
- ✅ The endpoint format is: `https://{ACCOUNT_ID}.r2.cloudflarestorage.com`

## Security Best Practices

1. **Never commit `.env` file** - It's already in `.gitignore`
2. **Use different buckets for dev/prod** - Create separate R2 buckets
3. **Rotate credentials periodically** - Create new API tokens and update `.env`
4. **Use least privilege** - Only grant "Object Read & Write" if you don't need bucket management
5. **Use environment-specific secrets** - Use different credentials for development, staging, and production

## Additional Resources

- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [R2 S3 API Compatibility](https://developers.cloudflare.com/r2/api/s3/api/)
- [Creating R2 API Tokens](https://developers.cloudflare.com/r2/api/s3/tokens/)

