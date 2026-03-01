#!/usr/bin/env python3
"""
Phase 1 Integration Test Suite
Comprehensive testing for FastEmailProcessor core integration
"""

import unittest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from phase1_core_integration import FastEmailProcessor, EmailMetadata

class TestPhase1Integration(unittest.TestCase):
    """Test suite for Phase 1 core integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_config = {
            'max_threads': 10,
            'batch_size': 100,
            'db_uri': 'sqlite:///:memory:'  # Use in-memory SQLite for testing
        }
        
        self.processor = FastEmailProcessor(self.test_config)
        
        # Mock Gmail service for testing
        self.mock_gmail_service = Mock()
        self.processor.gmail_service = self.mock_gmail_service
    
    def test_gmail_query_optimization(self):
        """Test Gmail query optimization"""
        print("\n🔍 Testing Gmail Query Optimization...")
        
        # Test basic query
        query = self.processor.create_optimized_gmail_query()
        
        self.assertIn('has:attachment', query)
        self.assertIn('invoice', query)
        self.assertIn('receipt', query)
        self.assertIn('bill', query)
        
        print(f"✅ Basic query generated: {query[:50]}...")
        
        # Test query with date range
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        query_with_date = self.processor.create_optimized_gmail_query((start_date, end_date))
        
        self.assertIn('after:', query_with_date)
        self.assertIn('before:', query_with_date)
        
        print(f"✅ Date-filtered query generated: {