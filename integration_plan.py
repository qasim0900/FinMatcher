#!/usr/bin/env python3
"""
Integration Plan: Fast Email Processor → Existing FinMatcher
Step-by-step integration strategy for production deployment
"""

import os
from pathlib import Path

def create_integration_roadmap():
    """Create detailed integration roadmap"""
    
    roadmap = {
        "Phase 1: Core Integration (30 minutes)": {
            "tasks": [
                "Replace existing EmailFetcher with FastEmailProcessor",
                "Update main.py to use optimized pipeline",
                "Modify configuration files for new parameters",
                "Test basic functionality"
            ],
            "files_to_modify": [
                "main.py",
                "config.yaml", 
                "finmatcher/core/email_fetcher.py"
            ],
            "risk": "Low"
        },
        
        "Phase 2: Database Integration (45 minutes)": {
            "tasks": [
                "Connect FastEmailProcessor to existing PostgreSQL",
                "Update database models for attachment_file field",
                "Implement bulk database operations",
                "Test database performance"
            ],
            "files_to_modify": [
                "finmatcher/database/models.py",
                "finmatcher/storage/database_manager.py",
                "schema/add_attachment_fields.sql"
            ],
            "risk": "Medium"
        },
        
        "Phase 3: Statement Matching Integration (1 hour)": {
            "tasks": [
                "Integrate K-D Tree with existing matching engine",
                "Connect to statements folder processing",
                "Update matching algorithms",
                "Test matching accuracy"
            ],
            "files_to_modify": [
                "finmatcher/core/matching_engine.py",
                "finmatcher/core/statement_parser.py"
            ],
            "risk": "Medium"
        },
        
        "Phase 4: Excel Generation Optimization (30 minutes)": {
            "tasks": [
                "Optimize Excel generation with pandas",
                "Implement client-specific formatting",
                "Add progress tracking",
                "Test large file generation"
            ],
            "files_to_modify": [
                "finmatcher/reports/excel_generator.py",
                "finmatcher/reports/drive_manager.py"
            ],
            "risk": "Low"
        },
        
        "Phase 5: Production Testing (45 minutes)": {
            "tasks": [
                "Test with real Gmail credentials",
                "Validate PostgreSQL performance",
                "Run end-to-end test with 1000 emails",
                "Monitor memory and CPU usage"
            ],
            "files_to_modify": [
                "test_production.py (new file)"
            ],
            "risk": "High"
        }
    }
    
    return roadmap

def generate_integration_code():
    """Generate integration code snippets"""
    
    integration_code = {
        "main.py_update": '''
# Replace existing email fetching with optimized version
from finmatcher.optimization.fast_email_processor import FastEmailProcessor

class FinMatcherOrchestrator:
    def __init__(self):
        # Initialize optimized processor
        self.fast_processor = FastEmailProcessor({
            'batch_size': 10000,
            'max_workers': 100,
            'process_workers': 16,
            'bloom_capacity': 500000
        })
        
    async def run_milestone_1_optimized(self):
        """Optimized email fetching and processing"""
        self.logger.log_milestone_start("Optimized Email Processing")
        
        # Use optimized pipeline
        results = await self.fast_processor.process_emails_optimized()
        
        # Mark emails with attachments in database
        self._mark_attachment_emails(results['emails'])
        
        self.logger.log_milestone_end(
            "Optimized Email Processing",
            records_processed=len(results['emails']),
            duration_seconds=results['processing_time']
        )
        
        return results
''',
        
        "config.yaml_update": '''
# Add optimization configuration
optimization:
  enabled: true
  fast_processor:
    batch_size: 10000
    max_workers: 100
    process_workers: 16
    bloom_capacity: 500000
    bloom_error_rate: 0.001
  
  # Gmail API optimization
  gmail:
    batch_size: 100
    rate_limit_delay: 0.1
    max_retries: 3
    exponential_backoff: true
  
  # Performance monitoring
  monitoring:
    memory_threshold: 0.85
    cpu_threshold: 0.90
    log_performance: true
''',
        
        "database_update": '''
-- Add attachment_file field to emails table
ALTER TABLE processed_emails 
ADD COLUMN attachment_file BOOLEAN DEFAULT FALSE;

-- Create index for fast filtering
CREATE INDEX idx_emails_attachment_file 
ON processed_emails(attachment_file) 
WHERE attachment_file = TRUE;

-- Create index for fast date/amount matching
CREATE INDEX idx_emails_date_amount 
ON processed_emails(date, amount) 
WHERE attachment_file = TRUE;
''',
        
        "excel_optimization": '''
# Optimized Excel generation
import pandas as pd
from openpyxl.styles import Font, PatternFill
import xlsxwriter

def generate_optimized_excel(matched_emails, output_path):
    """Generate Excel with optimized performance"""
    
    # Use xlsxwriter engine for better performance
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        
        # Convert to DataFrame for vectorized operations
        df = pd.DataFrame(matched_emails)
        
        # Write main data
        df.to_excel(writer, sheet_name='Matched_Emails', index=False)
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Matched_Emails']
        
        # Add formatting (vectorized)
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white'
        })
        
        # Apply header formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, min(max_length + 2, 50))
'''
    }
    
    return integration_code

def create_production_test():
    """Create production testing script"""
    
    test_script = '''
#!/usr/bin/env python3
"""
Production Testing Script
Test optimized FinMatcher with real data
"""

import asyncio
import time
import psutil
import logging
from datetime import datetime, timedelta

async def test_production_pipeline():
    """Test complete production pipeline"""
    
    print("="*60)
    print("PRODUCTION TESTING - OPTIMIZED FINMATCHER")
    print("="*60)
    
    # Monitor system resources
    initial_memory = psutil.virtual_memory().percent
    initial_cpu = psutil.cpu_percent()
    
    print(f"Initial Memory Usage: {initial_memory:.1f}%")
    print(f"Initial CPU Usage: {initial_cpu:.1f}%")
    
    # Test with different email counts
    test_sizes = [100, 500, 1000, 2000]
    
    for size in test_sizes:
        print(f"\\nTesting with {size} emails...")
        
        start_time = time.time()
        
        # Initialize optimized processor
        from finmatcher.optimization.fast_email_processor import FastEmailProcessor
        processor = FastEmailProcessor({
            'batch_size': min(size, 1000),
            'max_workers': 50,
            'process_workers': 8
        })
        
        # Run optimized pipeline
        results = await processor.process_emails_optimized()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Monitor resources
        current_memory = psutil.virtual_memory().percent
        current_cpu = psutil.cpu_percent()
        
        print(f"  Processing Time: {processing_time:.2f}s")
        print(f"  Emails Processed: {results['metrics']['total_emails_processed']}")
        print(f"  Financial Emails: {results['metrics']['financial_emails_found']}")
        print(f"  Memory Usage: {current_memory:.1f}%")
        print(f"  CPU Usage: {current_cpu:.1f}%")
        print(f"  Speed: {size/processing_time:.0f} emails/second")
        
        # Performance validation
        if processing_time > size / 1000:  # Should process 1000+ emails/second
            print(f"  ⚠️  Performance below target")
        else:
            print(f"  ✅ Performance target met")
    
    print(f"\\n" + "="*60)
    print("PRODUCTION TEST COMPLETED")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_production_pipeline())
'''
    
    return test_script

def main():
    """Generate complete integration plan"""
    
    print("="*70)
    print("FINMATCHER INTEGRATION STRATEGY")
    print("Fast Email Processor → Production System")
    print("="*70)
    
    # Generate roadmap
    roadmap = create_integration_roadmap()
    
    print("\\nINTEGRATION ROADMAP:")
    print("-" * 50)
    
    total_time = 0
    for phase, details in roadmap.items():
        time_estimate = int(phase.split('(')[1].split(' ')[0])
        total_time += time_estimate
        
        print(f"\\n{phase}")
        print(f"Risk Level: {details['risk']}")
        print("Tasks:")
        for task in details['tasks']:
            print(f"  - {task}")
        print("Files to modify:")
        for file in details['files_to_modify']:
            print(f"  - {file}")
    
    print(f"\\nTotal Integration Time: {total_time} minutes ({total_time/60:.1f} hours)")
    
    # Generate code snippets
    print("\\n" + "="*70)
    print("INTEGRATION CODE SNIPPETS")
    print("="*70)
    
    integration_code = generate_integration_code()
    
    for section, code in integration_code.items():
        print(f"\\n{section.upper()}:")
        print("-" * 40)
        print(code)
    
    # Risk assessment
    print("\\n" + "="*70)
    print("RISK ASSESSMENT & MITIGATION")
    print("="*70)
    
    risks = {
        "Gmail API Rate Limits": {
            "probability": "Medium",
            "impact": "High",
            "mitigation": "Implement exponential backoff, use multiple accounts"
        },
        "Database Performance": {
            "probability": "Low", 
            "impact": "Medium",
            "mitigation": "Create proper indexes, use connection pooling"
        },
        "Memory Usage": {
            "probability": "Medium",
            "impact": "Medium", 
            "mitigation": "Process in chunks, monitor memory usage"
        },
        "OCR Processing Time": {
            "probability": "Low",
            "impact": "Low",
            "mitigation": "Parallel processing, skip non-financial attachments"
        }
    }
    
    for risk, details in risks.items():
        print(f"\\n{risk}:")
        print(f"  Probability: {details['probability']}")
        print(f"  Impact: {details['impact']}")
        print(f"  Mitigation: {details['mitigation']}")
    
    # Success metrics
    print("\\n" + "="*70)
    print("SUCCESS METRICS")
    print("="*70)
    
    metrics = [
        "Processing speed: 1000+ emails/second",
        "Memory usage: <80% of available RAM", 
        "CPU usage: <90% during processing",
        "Database response time: <100ms per query",
        "Excel generation: <30 seconds for 10k records",
        "Overall completion: <5 hours for 200k emails"
    ]
    
    for metric in metrics:
        print(f"✅ {metric}")
    
    print(f"\\n" + "="*70)
    print("READY FOR INTEGRATION!")
    print("="*70)
    print("\\nNext Steps:")
    print("1. Backup existing FinMatcher code")
    print("2. Start with Phase 1 (Core Integration)")
    print("3. Test each phase before proceeding")
    print("4. Monitor performance metrics")
    print("5. Deploy to production")

if __name__ == "__main__":
    main()