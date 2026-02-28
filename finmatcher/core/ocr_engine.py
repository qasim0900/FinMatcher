"""
OCR engine for text extraction from images and PDFs.

This module uses Tesseract OCR with a 10-process pool for CPU-bound
OCR operations on receipt images and scanned PDFs.

Validates Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 5.2, 12.4
"""

import re
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal
import time

try:
    import pytesseract
    from PIL import Image
    
    # Configure Tesseract path for Windows
    if os.name == 'nt':  # Windows
        # Common installation paths
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe'
        ]
        
        # Try to find Tesseract
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
    
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: pytesseract or PIL not available. OCR functionality will be limited.")
    print("Install with: pip install pytesseract pillow")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("Warning: PyMuPDF not available. PDF OCR will be limited.")
    print("Install with: pip install PyMuPDF")

from finmatcher.config.settings import get_settings
from finmatcher.utils.logger import get_logger
from finmatcher.utils.date_parser import extract_dates


class OCREngine:
    """
    OCR engine using Tesseract with multi-processing.
    
    Uses ProcessPoolExecutor with 10 processes for CPU-bound OCR operations.
    Extracts text from images and scanned PDFs, then parses amounts and dates.
    
    Validates Requirements:
    - 3.1: Process images using Tesseract OCR
    - 3.2: Extract text from PDFs using OCR
    - 3.3: Extract amounts using regex
    - 3.4: Extract dates in multiple formats
    - 3.5: Return extracted text with confidence scores
    - 3.6: Flag receipts with low confidence for manual review
    - 5.2: ProcessPoolExecutor for CPU-bound operations
    - 12.4: Mark receipts as requiring manual review on OCR failure
    """
    
    # Regex pattern for dollar amounts
    AMOUNT_PATTERN = re.compile(r'\$\s?[\d,]+\.\d{2}')
    
    # Keywords that indicate financial content
    FINANCIAL_KEYWORDS = [
        'total', 'amount', 'subtotal', 'tax', 'receipt', 'invoice',
        'payment', 'charge', 'balance', 'due', 'paid'
    ]
    
    def __init__(self, process_pool_size: Optional[int] = None):
        """
        Initialize the OCR engine.
        
        Args:
            process_pool_size: Number of processes (default: from config, typically 10)
            
        Validates Requirement 5.2: ProcessPoolExecutor for CPU-bound operations
        """
        self.settings = get_settings()
        self.logger = get_logger()
        
        # Process pool configuration
        self.process_pool_size = process_pool_size or self.settings.process_pool_size
        
        # OCR settings
        self.confidence_threshold = self.settings.ocr_settings.confidence_threshold
        self.tesseract_path = self.settings.ocr_settings.tesseract_path
        
        # Set Tesseract path if configured
        if self.tesseract_path and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        
        self.logger.info(f"Initialized OCREngine with {self.process_pool_size} processes")
        self.logger.info(f"Confidence threshold: {self.confidence_threshold}")
    
    def process_attachments_batch(
        self,
        attachments: List[Dict]
    ) -> List[Dict]:
        """
        Process a batch of attachments using process pool.
        
        Args:
            attachments: List of attachment dictionaries
            
        Returns:
            List of processed attachment dictionaries with extracted text
            
        Validates Requirement 5.2: Use ProcessPoolExecutor with 10 processes
        """
        if not attachments:
            return []
        
        self.logger.info(f"Processing {len(attachments)} attachments with {self.process_pool_size} processes")
        start_time = time.time()
        
        results = []
        
        # Process in parallel with process pool
        with ProcessPoolExecutor(max_workers=self.process_pool_size) as executor:
            # Submit all tasks
            future_to_attachment = {
                executor.submit(self._process_single_attachment, att): att
                for att in attachments
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_attachment):
                attachment = future_to_attachment[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(
                        f"Error processing attachment {attachment.get('filename', 'unknown')}: {e}"
                    )
                    # Return attachment with error flag
                    attachment['extracted_text'] = ""
                    attachment['confidence_score'] = 0.0
                    attachment['requires_manual_review'] = True
                    attachment['error'] = str(e)
                    results.append(attachment)
        
        duration = time.time() - start_time
        self.logger.info(f"Processed {len(results)} attachments in {duration:.2f}s")
        
        return results
    
    def _process_single_attachment(self, attachment: Dict) -> Dict:
        """
        Process a single attachment (called by process pool workers).
        
        Args:
            attachment: Attachment dictionary
            
        Returns:
            Attachment dictionary with extracted text and metadata
        """
        file_path = Path(attachment['file_path'])
        content_type = attachment.get('content_type', '')
        
        # Determine processing method based on content type
        if 'image' in content_type.lower():
            return self._process_image(attachment)
        elif 'pdf' in content_type.lower():
            return self._process_pdf(attachment)
        else:
            # Unknown type, return as-is
            attachment['extracted_text'] = ""
            attachment['confidence_score'] = 0.0
            return attachment
    
    def _process_image(self, attachment: Dict) -> Dict:
        """
        Process an image attachment using OCR.
        
        Args:
            attachment: Attachment dictionary
            
        Returns:
            Attachment dictionary with extracted text
            
        Validates Requirement 3.1: Process images using Tesseract OCR
        """
        if not TESSERACT_AVAILABLE:
            attachment['extracted_text'] = ""
            attachment['confidence_score'] = 0.0
            attachment['error'] = "Tesseract not available"
            return attachment
        
        try:
            file_path = Path(attachment['file_path'])
            
            # Open image
            image = Image.open(file_path)
            
            # Perform OCR
            ocr_data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                lang=self.settings.ocr_settings.language
            )
            
            # Extract text and calculate confidence
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(ocr_data['conf']):
                if int(conf) > 0:  # Valid confidence
                    text = ocr_data['text'][i].strip()
                    if text:
                        text_parts.append(text)
                        confidences.append(int(conf))
            
            # Combine text
            extracted_text = ' '.join(text_parts)
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            avg_confidence = avg_confidence / 100.0  # Normalize to 0-1
            
            # Update attachment
            attachment['extracted_text'] = extracted_text
            attachment['confidence_score'] = avg_confidence
            attachment['requires_manual_review'] = avg_confidence < self.confidence_threshold
            
            # Extract amounts and dates
            attachment['extracted_amounts'] = self.extract_amounts(extracted_text)
            attachment['extracted_dates'] = extract_dates(extracted_text)
            
            return attachment
        
        except Exception as e:
            attachment['extracted_text'] = ""
            attachment['confidence_score'] = 0.0
            attachment['requires_manual_review'] = True
            attachment['error'] = str(e)
            return attachment
    
    def _process_pdf(self, attachment: Dict) -> Dict:
        """
        Process a PDF attachment using OCR if needed.
        
        Args:
            attachment: Attachment dictionary
            
        Returns:
            Attachment dictionary with extracted text
            
        Validates Requirement 3.2: Extract text from PDFs using OCR
        """
        if not PYMUPDF_AVAILABLE:
            attachment['extracted_text'] = ""
            attachment['confidence_score'] = 0.0
            attachment['error'] = "PyMuPDF not available"
            return attachment
        
        try:
            file_path = Path(attachment['file_path'])
            
            # Open PDF
            doc = fitz.open(file_path)
            
            extracted_text = ""
            total_confidence = 0.0
            page_count = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Try text extraction first
                text = page.get_text()
                
                if text.strip():
                    # Text-based PDF
                    extracted_text += text + "\n"
                    total_confidence += 1.0  # High confidence for text-based
                    page_count += 1
                else:
                    # Scanned PDF, use OCR
                    if TESSERACT_AVAILABLE:
                        # Convert page to image
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # Perform OCR
                        ocr_text = pytesseract.image_to_string(
                            img,
                            lang=self.settings.ocr_settings.language
                        )
                        
                        extracted_text += ocr_text + "\n"
                        
                        # Estimate confidence (simplified)
                        confidence = 0.7 if ocr_text.strip() else 0.0
                        total_confidence += confidence
                        page_count += 1
            
            doc.close()
            
            # Calculate average confidence
            avg_confidence = total_confidence / page_count if page_count > 0 else 0.0
            
            # Update attachment
            attachment['extracted_text'] = extracted_text
            attachment['confidence_score'] = avg_confidence
            attachment['requires_manual_review'] = avg_confidence < self.confidence_threshold
            
            # Extract amounts and dates
            attachment['extracted_amounts'] = self.extract_amounts(extracted_text)
            attachment['extracted_dates'] = extract_dates(extracted_text)
            
            return attachment
        
        except Exception as e:
            attachment['extracted_text'] = ""
            attachment['confidence_score'] = 0.0
            attachment['requires_manual_review'] = True
            attachment['error'] = str(e)
            return attachment
    
    def extract_amounts(self, text: str) -> List[Decimal]:
        """
        Extract dollar amounts from text using regex.
        
        Args:
            text: Text to extract amounts from
            
        Returns:
            List of Decimal amounts
            
        Validates Requirement 3.3: Use regex pattern to identify dollar amounts
        """
        amounts = []
        
        # Find all matches
        matches = self.AMOUNT_PATTERN.findall(text)
        
        for match in matches:
            try:
                # Clean and parse amount
                amount_str = match.replace('$', '').replace(',', '').strip()
                amount = Decimal(amount_str)
                
                if amount > 0:
                    amounts.append(amount)
            except:
                continue
        
        return amounts
    
    def extract_merchant_name(self, text: str) -> Optional[str]:
        """
        Extract merchant/vendor name from text.
        
        This is a simplified implementation. In production, you might use
        NER (Named Entity Recognition) for better accuracy.
        
        Args:
            text: Text to extract merchant from
            
        Returns:
            Merchant name or None
        """
        # Look for common patterns
        lines = text.split('\n')
        
        # Usually merchant name is in first few lines
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) > 3 and len(line) < 50:
                # Filter out common non-merchant text
                if not any(keyword in line.lower() for keyword in ['receipt', 'invoice', 'total', 'date']):
                    return line
        
        return None
    
    def is_financial_document(self, text: str) -> bool:
        """
        Determine if text contains financial information.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if financial document, False otherwise
        """
        text_lower = text.lower()
        
        # Check for financial keywords
        keyword_count = sum(1 for keyword in self.FINANCIAL_KEYWORDS if keyword in text_lower)
        
        # Check for amounts
        has_amounts = bool(self.AMOUNT_PATTERN.search(text))
        
        # Consider it financial if it has keywords and amounts
        return keyword_count >= 2 and has_amounts


# Convenience function
def process_attachments(attachments: List[Dict]) -> List[Dict]:
    """
    Process attachments using OCR.
    
    Args:
        attachments: List of attachment dictionaries
        
    Returns:
        List of processed attachments with extracted text
    """
    engine = OCREngine()
    return engine.process_attachments_batch(attachments)
