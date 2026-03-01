# FinMatcher - AI-Powered Financial Reconciliation System

## 📋 Project Overview

FinMatcher is an enterprise-grade intelligent financial reconciliation system that automates the matching of credit card statements with email receipts. The system leverages advanced AI-powered semantic matching, optical character recognition (OCR), and seamless Google Drive integration to streamline financial operations.

**Key Features:**
- 🤖 AI-powered semantic matching using DeepSeek embeddings
- 📧 Multi-account Gmail integration (IMAP & Gmail API)
- 🔍 Advanced OCR engine for attachment processing (images & PDFs)
- 📊 Automated Excel report generation with detailed analytics
- ☁️ Google Drive synchronization with organized folder structure
- 🚀 High-performance optimization layer (K-D Tree spatial indexing, Bloom Filter, Vectorization)
- 📈 Real-time performance monitoring and metrics
- 🔒 Enterprise-grade security validation and PII sanitization

## 🏗️ System Architecture

### Core Components

```
finmatcher/
├── config/              # Configuration management
├── core/                # Core processing engines
│   ├── email_fetcher.py        # Email ingestion
│   ├── statement_parser.py     # Statement parsing
│   ├── ocr_engine.py           # OCR processing
│   ├── matcher_engine.py       # Transaction matching
│   ├── matching_engine.py      # Advanced matching logic
│   ├── financial_filter.py     # Email filtering
│   └── deepseek_client.py      # AI client
├── database/            # Data persistence
├── optimization/        # Performance optimization
├── orchestration/       # Workflow management
├── reports/             # Report generation & Drive sync
├── storage/             # Checkpoint management
└── utils/               # Utilities (logging, error handling)
```

## 🎯 Workflow & Execution Pipeline

### Milestone-Based Execution Strategy

The system employs a sophisticated milestone-based execution model that optimizes resource utilization through intelligent caching and progressive processing.

**Milestone 1: Meriwest Credit Card Reconciliation**
1. Parse Meriwest PDF statement
2. Fetch emails from all Gmail accounts
3. Process attachments with OCR
4. Match transactions to receipts
5. Generate Excel report
6. Upload to Google Drive

**Milestone 2: Amex Credit Card Reconciliation**
- Reuses cached emails from Milestone 1
- Parses Amex Excel statement
- Matches and generates report

**Milestone 3: Chase Credit Card Reconciliation**
- Reuses cached emails
- Parses Chase Excel statement
- Matches and generates report

**Milestone 4: Unmatched Financial Records**
- Identifies emails not linked to any statement
- Generates "Other_Financial_records.xlsx"

## 🔧 Technology Stack

### Core Technologies
- **Python**: 3.11-3.13
- **Database**: SQLite with WAL mode
- **AI/ML**: 
  - DeepSeek API (semantic embeddings)
  - scikit-learn (K-D Tree spatial indexing)
  - NumPy (vectorized operations)
- **OCR**: Tesseract + PyMuPDF + pdfplumber
- **APIs**: 
  - Gmail API & IMAP
  - Google Drive API
- **Data Processing**: pandas, openpyxl

### Key Dependencies
```toml
pandas = ">=3.0.1"
scikit-learn = ">=1.8.0"
google-api-python-client = ">=2.190.0"
pymupdf = ">=1.27.1"
pytesseract = ">=0.3.10"
openai = ">=1.0.0"  # For DeepSeek client
numpy = ">=2.0.0"
```

## 📊 Advanced Matching Algorithm

### Composite Scoring System

The matching engine implements a sophisticated multi-dimensional scoring algorithm that combines financial, temporal, and semantic features to achieve high-accuracy transaction matching.

```
Composite Score = (W_a × S_a) + (W_d × S_d) + (W_s × S_s)
```

**Where:**
- `W_a = 0.4` (Amount weight)
- `W_d = 0.3` (Date weight)
- `W_s = 0.3` (Semantic weight)

### Amount Score (S_a)
```
S_a = exp(-λ × |amount_txn - amount_receipt|)
λ = 2.0 (decay rate)
```

### Date Score (S_d)
```
S_d = 1 - (|date_diff_days| / max_date_variance)
max_date_variance = 3 days
```

### Semantic Score (S_s)
```
S_s = cosine_similarity(embedding_txn, embedding_receipt)
```

### Thresholds
- **Exact Match**: ≥ 0.98
- **High Confidence**: ≥ 0.85
- **Amount Tolerance**: $1.00
- **Date Variance**: ±3 days

## 🚀 Performance Optimization Architecture

The system implements a multi-layered optimization strategy designed to handle large-scale financial data processing with minimal latency and resource consumption.

### 1. K-D Tree Spatial Indexing
- **Purpose**: Fast candidate filtering
- **Features**: Amount + Date dimensions
- **Leaf Size**: 40
- **Caching**: Enabled with 7-day expiration

### 2. Vectorized Batch Scoring
- **Batch Size**: 100,000 operations
- **Technology**: NumPy broadcasting
- **Speedup**: 10-100x vs loops

### 3. Bloom Filter Deduplication
- **Capacity**: 100,000 items
- **Error Rate**: 0.1%
- **Purpose**: Fast duplicate detection

### 4. Memory Management
- **Chunk Size**: 1,000 records
- **Warning Threshold**: 80% memory usage
- **Pause Threshold**: 90% memory usage
- **Auto GC**: Triggered at 90%

## 📧 Intelligent Email Processing

### Three-Layer Financial Classification Filter

The system employs a cost-optimized three-tier filtering strategy that minimizes AI API costs while maintaining high classification accuracy.

**Layer 1: Auto-Reject (Marketing/Spam)**
- Keywords: unsubscribe, newsletter, discount, sale
- No AI cost

**Layer 2: Auto-Accept (Clear Financial)**
- Keywords: receipt, invoice, bill, payment, transaction
- No AI cost

**Layer 3: AI Verification (Ambiguous)**
- Uses DeepSeek API
- Only for unclear cases
- Target: 80% rule-based filtering

### Multi-Account Support
```python
EMAIL_ACCOUNTS=
  account1@gmail.com,app_password1,INBOX|Spam;
  account2@gmail.com,app_password2,INBOX|Spam;
  account3@gmail.com,app_password3,INBOX|Spam
```

## 📄 Statement Parsing Engine

### Supported Statement Formats

**1. Meriwest PDF**
- Parser: PyMuPDF + pdfplumber
- Extracts: Date, Description, Amount

**2. Amex Excel**
- Parser: pandas + openpyxl
- Columns: Date, Description, Amount

**3. Chase Excel**
- Parser: pandas + openpyxl
- Columns: Transaction Date, Description, Amount

### Transaction Model
```python
@dataclass
class Transaction:
    date: str              # YYYY-MM-DD
    description: str       # Merchant name
    amount: Decimal        # Transaction amount
    statement_name: str    # Source statement
    category: Optional[str]
```

## 🖼️ OCR Processing Engine

### Supported Document Formats
- **Images**: JPG, JPEG, PNG, GIF, BMP, TIFF
- **Documents**: PDF

### Processing Pipeline
1. **Image Preprocessing**
   - Grayscale conversion
   - Contrast enhancement
   - Noise reduction

2. **Text Extraction**
   - Tesseract OCR
   - Multi-language support

3. **Data Extraction**
   - Amount detection (regex patterns)
   - Date extraction
   - Merchant name identification

### Parallel Processing
- **Process Pool**: 10 workers
- **Batch Processing**: Enabled
- **Timeout**: 30 seconds per attachment

## 📊 Report Generation & Distribution

### Excel Report Structure

**1. Statement Reports**
```
{Statement_Name}_records.xlsx
Columns:
- Transaction Date
- Description
- Amount
- Match Status
- Receipt Date
- Sender Name
- Email Link
- Confidence Score
```

**2. Other Financial Records**
```
Other_Financial_records.xlsx
- Unmatched receipts
- Financial emails not in statements
```

### Google Drive Structure
```
FinMatcher_Excel_Reports/
├── Meriwest_Credit_Card_Statement_records.xlsx/
├── Amex_Credit_Card_Statement_records.xlsx/
├── Chase_Credit_Card_Statement_records.xlsx/
├── Other_receipts_email.xlsx/
├── Attach_files/          # PDF, DOC attachments
├── Attach_Image/          # Image attachments
├── Unmatch_Email_Attach_files/
└── unmatch_attach_image/
```

## 🗄️ Database Schema Design

### Relational Data Model

The system utilizes a normalized relational schema optimized for transactional integrity and query performance.

**emails**
```sql
- email_id (PK)
- message_id (unique)
- account_email
- sender_name, sender_email
- subject, body_text
- received_date
- amount, merchant_name, transaction_date
- has_attachments
- created_at, updated_at
```

**receipts**
```sql
- receipt_id (PK)
- amount, merchant_name
- transaction_date
- category, payment_method
- filter_method (auto_accept, auto_reject, ai_verified)
```

**matches**
```sql
- match_id (PK)
- email_id (FK), receipt_id (FK)
- match_score (0-1)
- match_type (exact, fuzzy, partial)
- confidence_level (high, medium, low)
- amount_diff, date_diff_days
- semantic_score
```

**jobs** (Pipeline orchestration)
```sql
- job_id (PK)
- email_id (FK)
- status (pending, downloaded, matched, uploaded, failed)
- stage (ingestion, matching, reporting, upload)
- retry_count, max_retries
```

## 🔐 Security & Compliance

### Security Features
1. **PII Sanitization**
   - Email addresses → [EMAIL]
   - Credit cards → [CARD]
   - Account numbers → [ACCOUNT]
   - API keys → ***REDACTED***

2. **Credential Management**
   - Environment variables (.env)
   - OAuth 2.0 for Google APIs
   - Encrypted token storage

3. **Input Validation**
   - File path validation
   - SQL injection prevention
   - API rate limiting

## 📝 Logging & Observability

### Structured Logging System
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (80% memory)
- **ERROR**: Error messages
- **CRITICAL**: Critical errors (90% memory)

### Log Features
- **Rotating File Handler**: 100MB max, 90 backups
- **PII Sanitization**: Automatic
- **Structured Format**: Timestamp | Level | Module | Function | Message
- **UTF-8 Encoding**: Windows compatible

### Log Locations
```
logs/
└── finmatcher.log
```

## ⚙️ Configuration Management

### Configuration Schema (config.yaml)
```yaml
matching:
  weights:
    amount: 0.4
    date: 0.3
    semantic: 0.3
  thresholds:
    exact_match: 0.98
    high_confidence: 0.85

financial_filter:
  enable_ai: true
  target_rule_based_percentage: 0.80

deepseek:
  api_key: ${DEEPSEEK_API_KEY}
  timeout: 30

parallelism:
  thread_pool_size: 50
  process_pool_size: 10

optimization:
  enabled: true
  kdtree:
    leaf_size: 40
    cache_enabled: true
  vectorization:
    batch_size: 100000
  bloom_filter:
    initial_capacity: 100000
    error_rate: 0.001
```

## 🚀 Installation & Setup

### System Prerequisites
```bash
# Python 3.11-3.13
python --version

# Poetry (package manager)
pip install poetry

# Tesseract OCR
# Windows: Download from GitHub
# Linux: sudo apt-get install tesseract-ocr
# Mac: brew install tesseract

# PostgreSQL (recommended for production)
# Ubuntu: sudo apt-get install postgresql postgresql-contrib
# Windows: Download from postgresql.org
# Mac: brew install postgresql
```

### Setup Steps

1. **Clone Repository**
```bash
git clone <repository-url>
cd finmatcher
```

2. **Install Dependencies**
```bash
poetry install
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Setup Google Credentials**
```bash
# Place credentials.json in finmatcher/auth_files/
# Run authentication:
python -c "from finmatcher.reports.drive_sync import DriveSync; DriveSync()._authenticate()"
```

5. **Initialize Database (Ubuntu)**
```bash
# Single command for complete setup
python setup_ubuntu.py
```

This unified setup script will:
- Create the database if it doesn't exist
- Run all migrations from `schema/migrations/`
- Validate all required tables
- Confirm the database is ready for use

For ongoing migration management, use:
```bash
python migrate.py status  # Check migration status
python migrate.py up      # Apply new migrations
```

## 🎮 Usage & Execution

### Running Full Reconciliation Pipeline
```bash
# Windows
run.bat

# Linux/Mac
python run_reconciliation.py
```

### Run Specific Milestone
```bash
python main.py --mode milestone_1  # Meriwest
python main.py --mode milestone_2  # Amex
python main.py --mode milestone_3  # Chase
python main.py --mode milestone_4  # Unmatched
```

### Run All Milestones
```bash
python main.py --mode full_reconciliation
```

## 🧪 Testing & Quality Assurance

### Comprehensive Test Suite
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=finmatcher --cov-report=html

# Run specific test file
pytest tests/test_matcher_engine.py

# Run with verbose output
pytest -v
```

### Test Categories
- Unit tests
- Integration tests
- Performance tests
- Property-based tests (Hypothesis)

## 📈 Performance Metrics & Monitoring

### Target Performance Benchmarks
- **Throughput**: Process 1M emails in < 24 hours
- **Memory**: < 4GB RAM usage
- **Accuracy**: > 95% match accuracy

### Monitoring
```python
from finmatcher.utils.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
monitor.log_performance_summary(
    emails_processed=10000,
    matches_found=8500,
    duration_seconds=3600
)
```

## 🔄 Database Migration Strategy

### Unified Migration System

FinMatcher uses a streamlined migration system with clear entry points:

**For Initial Setup (Ubuntu):**
```bash
python setup_ubuntu.py
```
This single script handles complete database setup: creates the database, runs all migrations from `schema/migrations/`, and validates the installation.

**For Ongoing Migrations:**
```bash
# Check current migration status
python migrate.py status

# Apply pending migrations
python migrate.py up

# Rollback last migration
python migrate.py down
```

### Migration Files

All migrations are stored in `schema/migrations/` and tracked in the `schema_migrations` table:

- `001_initial_schema.sql` - Creates all base tables
- `002_add_optimization_fields.sql` - Adds performance optimization fields
- `003_add_performance_indexes.sql` - Creates indexes for query performance

### Deprecated Files

The following files have been deprecated and replaced by the unified system:

- ❌ `schema/migrate.py` → Use `migrate.py` instead
- ❌ `complete_setup.sh` → Use `setup_ubuntu.py` instead
- ❌ `setup_linux.sh` → Use `setup_ubuntu.py` instead
- ❌ `reset_and_migrate.sh` → Use `migrate.py` instead
- ❌ `fix_database.sh` → Use `setup_ubuntu.py` instead

These deprecated scripts have been moved to `.deprecated` extensions with notices pointing to the new unified system.

## 🐛 Troubleshooting Guide

### Common Issues & Resolutions

**1. Gmail Authentication Failed**
```bash
# Solution: Generate app password
# Go to: Google Account → Security → 2-Step Verification → App passwords
```

**2. OCR Not Working**
```bash
# Solution: Install Tesseract
# Windows: Download from GitHub releases
# Add to PATH: C:\Program Files\Tesseract-OCR
```

**3. Memory Issues**
```bash
# Solution: Reduce chunk size in config.yaml
memory:
  chunk_size: 500  # Reduce from 1000
```

**4. DeepSeek API Errors**
```bash
# Solution: Check API key and quota
# Verify: echo $DEEPSEEK_API_KEY
```

## 📚 API Reference & Integration

### Core API Components

#### EmailFetcher
```python
fetcher = EmailFetcher()
emails = fetcher.fetch_all_emails(
    date_range=(start_date, end_date),
    use_cache=True
)
```

#### MatcherEngine
```python
matcher = MatcherEngine()
matches = matcher.match_transactions_to_receipts(
    transactions=transactions,
    receipts=receipts
)
```

#### OCREngine
```python
ocr = OCREngine(process_pool_size=10)
result = ocr.process_attachment(file_path)
```

## 🤝 Contributing Guidelines

### Development Environment Setup
```bash
# Install dev dependencies
poetry install --with test

# Run linter
poetry run flake8 finmatcher/

# Format code
poetry run black finmatcher/
```

### Code Quality Standards
- Follow PEP 8
- Use type hints
- Write docstrings
- Add unit tests

## 📄 License

This project is proprietary software. All rights reserved.

## 👥 Project Team

- **Lead Developer**: qasim0900
- **Contact**: Available via GitHub

## 🙏 Acknowledgments

- DeepSeek AI for providing advanced semantic embedding capabilities
- Google for Gmail & Drive API infrastructure
- Tesseract OCR team for open-source OCR technology
- Python community for exceptional library ecosystem

## 📞 Support & Contact

For technical support, bug reports, or feature requests:

1. Review application logs: `logs/finmatcher.log`
2. Consult the troubleshooting section above
3. Open a GitHub issue with the following information:
   - Detailed error message
   - Relevant log excerpts
   - Steps to reproduce the issue
   - System environment details

---

**Version**: 3.0  
**Last Updated**: 2024  
**Status**: Production Ready ✅  
**Maintained By**: qasim0900
