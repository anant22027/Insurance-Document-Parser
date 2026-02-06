"""
Insurance Document Financial Parser
====================================
A comprehensive parser for extracting financial fields from insurance documents.
Supports multiple parsing strategies with fallback mechanisms.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import sys


class FieldCategory(Enum):
    """Categories of financial fields in insurance documents"""
    PREMIUM = "premium"
    COVERAGE = "coverage"
    DEDUCTIBLE = "deductible"
    CLAIM = "claim"
    TAX = "tax"
    FEE = "fee"
    BENEFIT = "benefit"
    LIMIT = "limit"


@dataclass
class FinancialField:
    """Represents a parsed financial field"""
    field_name: str
    value: float
    currency: str
    category: FieldCategory
    context: str  # Surrounding text for verification
    confidence: float  # 0.0 to 1.0
    line_number: Optional[int] = None
    extraction_method: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary with enum handling"""
        data = asdict(self)
        data['category'] = self.category.value
        return data


class InsuranceParser:
    CURRENCY_SYMBOLS = {
        '₹': 'INR',
        'Rs.': 'INR',
        'Rs': 'INR',
        'INR': 'INR',
        '$': 'USD',
        'USD': 'USD',
        '€': 'EUR',
        'EUR': 'EUR',
        '£': 'GBP',
        'GBP': 'GBP'
    }
    
    # Comprehensive field patterns
    FIELD_PATTERNS = {
        # Premium patterns
        'annual_premium': [
            r'Annual\s+Premium(?:\s+Amount)?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Total\s+Annual\s+Premium[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Yearly\s+Premium[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'monthly_premium': [
            r'Monthly\s+Premium(?:\s+Amount)?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Per\s+Month\s+Premium[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'quarterly_premium': [
            r'Quarterly\s+Premium(?:\s+Amount)?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Coverage patterns
        'sum_insured': [
            r'Sum\s+Insured[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Coverage\s+(?:Amount|Limit)[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Annual\s+Coverage\s+Limit[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'maximum_coverage': [
            r'Maximum\s+Coverage[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Max(?:imum)?\s+Limit[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Deductible patterns
        'deductible': [
            r'(?:Annual\s+)?Deductible(?:\s+Amount)?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Out[-\s]of[-\s]Pocket\s+(?:Maximum|Limit)[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'copayment_percentage': [
            r'Co[-\s]?payment(?:\s+Percentage)?[:\s]+([\d.]+)%',
            r'Co[-\s]?pay[:\s]+([\d.]+)%',
        ],
        'copayment_maximum': [
            r'Co[-\s]?payment\s+Maximum[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Tax and fees
        'gst': [
            r'(?:GST|Goods\s+and\s+Services\s+Tax)[^:]*@?\s*[\d.]+%[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Tax\s+Amount[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'admin_fee': [
            r'(?:Policy\s+)?Administration\s+Fee[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Admin\s+Charges?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'service_charge': [
            r'Service\s+Charges?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'total_amount_paid': [
            r'TOTAL\s+AMOUNT\s+PAID[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
            r'Total\s+Premium\s+Paid[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Claim information
        'claim_amount_submitted': [
            r'Claim\s+Amount\s+Submitted[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'claim_amount_approved': [
            r'Claim\s+Amount\s+Approved[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'total_claims_paid': [
            r'Total\s+Claim\s+Payouts?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Specific benefits
        'maternity_coverage': [
            r'Maternity\s+Coverage(?:\s+Limit)?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'critical_illness_coverage': [
            r'Critical\s+Illness\s+(?:Sum\s+Assured|Coverage)[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'ambulance_charges': [
            r'Ambulance\s+Charges?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Room limits
        'room_limit_per_day': [
            r'Room\s+Limit[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)\s*per\s+day',
            r'Per\s+(?:Hospitalization\s+)?Room\s+Limit[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        'icu_limit_per_day': [
            r'ICU\s+Room\s+Limit[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Renewal
        'renewal_premium': [
            r'(?:Estimated\s+)?Renewal\s+Premium[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
        
        # Bonus
        'no_claim_bonus': [
            r'No\s+Claim\s+Bonus\s+Discount(?:\s+Amount)?[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)',
        ],
    }
    
    def __init__(self, document_text: str):
        """
        Initialize parser with document text.
        
        Args:
            document_text: Raw text content of the insurance document
        """
        self.document_text = document_text
        self.lines = document_text.split('\n')
        self.parsed_fields: List[FinancialField] = []
        
    def extract_number(self, text: str) -> Optional[float]:
        """
        Extract numeric value from text, handling Indian number format.
        
        Args:
            text: Text containing number
            
        Returns:
            Extracted number as float, or None if not found
        """
        # Remove commas and convert to float
        cleaned = text.replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def detect_currency(self, text: str) -> str:
        """
        Detect currency from surrounding text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Currency code (default: INR)
        """
        for symbol, code in self.CURRENCY_SYMBOLS.items():
            if symbol in text:
                return code
        return 'INR'  # Default for Indian documents
    
    def calculate_confidence(self, field_name: str, value: float, context: str) -> float:
        """
        Calculate confidence score based on multiple factors.
        
        Args:
            field_name: Name of the field
            value: Extracted value
            context: Surrounding text
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence if multiple indicators present
        indicators = [
            ('₹' in context or 'Rs' in context, 0.1),
            (field_name.lower().replace('_', ' ') in context.lower(), 0.2),
            (value > 0, 0.1),
            (re.search(r'\d{1,3}(,\d{3})*(\.\d{2})?', context), 0.1),
        ]
        
        for condition, boost in indicators:
            if condition:
                confidence += boost
                
        return min(confidence, 1.0)
    
    def categorize_field(self, field_name: str) -> FieldCategory:
        """
        Categorize a field based on its name.
        
        Args:
            field_name: Name of the field
            
        Returns:
            FieldCategory enum value
        """
        name_lower = field_name.lower()
        
        if 'premium' in name_lower:
            return FieldCategory.PREMIUM
        elif 'claim' in name_lower:
            return FieldCategory.CLAIM
        elif 'deductible' in name_lower or 'copay' in name_lower:
            return FieldCategory.DEDUCTIBLE
        elif 'tax' in name_lower or 'gst' in name_lower:
            return FieldCategory.TAX
        elif 'fee' in name_lower or 'charge' in name_lower:
            return FieldCategory.FEE
        elif 'coverage' in name_lower or 'insured' in name_lower or 'benefit' in name_lower:
            return FieldCategory.COVERAGE
        elif 'limit' in name_lower or 'maximum' in name_lower:
            return FieldCategory.LIMIT
        else:
            return FieldCategory.BENEFIT
    
    def parse_with_patterns(self) -> List[FinancialField]:
        """
        Primary parsing method using regex patterns.
        
        Returns:
            List of extracted financial fields
        """
        results = []
        
        for field_name, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, self.document_text, re.IGNORECASE)
                
                for match in matches:
                    # Extract the numeric value
                    value_str = match.group(1)
                    value = self.extract_number(value_str)
                    
                    if value is None:
                        continue
                    
                    # Get context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(self.document_text), match.end() + 50)
                    context = self.document_text[start:end].replace('\n', ' ')
                    
                    # Detect currency
                    currency = self.detect_currency(context)
                    
                    # Calculate confidence
                    confidence = self.calculate_confidence(field_name, value, context)
                    
                    # Find line number
                    line_num = self.document_text[:match.start()].count('\n') + 1
                    
                    # Create financial field
                    field = FinancialField(
                        field_name=field_name,
                        value=value,
                        currency=currency,
                        category=self.categorize_field(field_name),
                        context=context.strip(),
                        confidence=confidence,
                        line_number=line_num,
                        extraction_method="pattern_matching"
                    )
                    
                    results.append(field)
                    break  # Take first match for each pattern
                    
                if results and results[-1].field_name == field_name:
                    break  # Found a match, move to next field
        
        return results
    
    def parse_context_aware(self) -> List[FinancialField]:
        """
        Secondary parsing method using contextual analysis.
        Looks for currency amounts near financial keywords.
        
        Returns:
            List of extracted financial fields
        """
        results = []
        
        # Financial keywords to look for
        keywords = [
            'premium', 'deductible', 'coverage', 'claim', 'fee', 'charge',
            'limit', 'benefit', 'tax', 'payment', 'amount', 'total'
        ]
        
        # Pattern to find amounts
        amount_pattern = r'(?:₹|Rs\.?|INR)?\s*([\d,]+\.?\d*)'
        
        for i, line in enumerate(self.lines, 1):
            line_lower = line.lower()
            
            # Check if line contains financial keywords
            for keyword in keywords:
                if keyword in line_lower:
                    # Search for amounts in this line
                    matches = re.finditer(amount_pattern, line)
                    
                    for match in matches:
                        value = self.extract_number(match.group(1))
                        
                        if value and value > 0:
                            # Check if already extracted by pattern matching
                            already_extracted = any(
                                f.line_number == i and abs(f.value - value) < 0.01
                                for f in self.parsed_fields
                            )
                            
                            if not already_extracted:
                                field_name = f"{keyword}_line_{i}"
                                currency = self.detect_currency(line)
                                confidence = self.calculate_confidence(field_name, value, line)
                                
                                field = FinancialField(
                                    field_name=field_name,
                                    value=value,
                                    currency=currency,
                                    category=self.categorize_field(keyword),
                                    context=line.strip(),
                                    confidence=confidence * 0.8,  # Lower confidence for context-based
                                    line_number=i,
                                    extraction_method="context_aware"
                                )
                                
                                results.append(field)
        
        return results
    
    def parse_all_amounts(self) -> List[FinancialField]:
        """
        Tertiary parsing method: Extract all monetary amounts for comprehensive analysis.
        
        Returns:
            List of all found monetary amounts
        """
        results = []
        
        # Enhanced pattern to catch all amounts
        amount_pattern = r'(?:₹|Rs\.?|INR|USD|\$|EUR|€)\s*([\d,]+\.?\d*)'
        
        for i, line in enumerate(self.lines, 1):
            matches = re.finditer(amount_pattern, line, re.IGNORECASE)
            
            for match in matches:
                value = self.extract_number(match.group(1))
                
                if value and value > 0:
                    # Check if already extracted
                    already_extracted = any(
                        f.line_number == i and abs(f.value - value) < 0.01
                        for f in self.parsed_fields
                    )
                    
                    if not already_extracted:
                        currency = self.detect_currency(match.group(0))
                        
                        field = FinancialField(
                            field_name=f"amount_line_{i}",
                            value=value,
                            currency=currency,
                            category=FieldCategory.BENEFIT,  # Generic category
                            context=line.strip(),
                            confidence=0.5,  # Lower confidence for generic extraction
                            line_number=i,
                            extraction_method="all_amounts"
                        )
                        
                        results.append(field)
        
        return results
    
    def parse(self, include_all_amounts: bool = False) -> Dict[str, Any]:
        """
        Main parsing method that orchestrates all strategies.
        
        Args:
            include_all_amounts: Whether to include all amounts (can be noisy)
            
        Returns:
            Dictionary containing parsed results and metadata
        """
        # Strategy 1: Pattern-based extraction (highest confidence)
        pattern_results = self.parse_with_patterns()
        self.parsed_fields.extend(pattern_results)
        
        # Strategy 2: Context-aware extraction (medium confidence)
        context_results = self.parse_context_aware()
        self.parsed_fields.extend(context_results)
        
        # Strategy 3: All amounts extraction (lowest confidence, optional)
        if include_all_amounts:
            all_amounts = self.parse_all_amounts()
            self.parsed_fields.extend(all_amounts)
        
        # Sort by confidence
        self.parsed_fields.sort(key=lambda x: x.confidence, reverse=True)
        
        # Compile results
        results = {
            'metadata': {
                'total_fields_extracted': len(self.parsed_fields),
                'pattern_matches': len(pattern_results),
                'context_matches': len(context_results),
                'extraction_date': datetime.now().isoformat(),
                'parser_version': '1.0.0'
            },
            'fields': [field.to_dict() for field in self.parsed_fields],
            'summary': self._generate_summary()
        }
        
        return results
    
    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics of parsed fields.
        
        Returns:
            Dictionary with summary information
        """
        summary = {
            'by_category': {},
            'by_currency': {},
            'high_confidence_fields': 0,
            'total_premium_amount': 0,
            'total_coverage_amount': 0,
            'total_claims_amount': 0
        }
        
        # Count by category
        for field in self.parsed_fields:
            category = field.category.value
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count by currency
            summary['by_currency'][field.currency] = summary['by_currency'].get(field.currency, 0) + 1
            
            # High confidence fields
            if field.confidence >= 0.8:
                summary['high_confidence_fields'] += 1
            
            # Sum important categories
            if field.category == FieldCategory.PREMIUM and field.confidence >= 0.7:
                summary['total_premium_amount'] += field.value
            elif field.category == FieldCategory.COVERAGE and field.confidence >= 0.7:
                summary['total_coverage_amount'] += field.value
            elif field.category == FieldCategory.CLAIM and field.confidence >= 0.7:
                summary['total_claims_amount'] += field.value
        
        return summary
    
    def export_to_json(self, filepath: str, include_all_amounts: bool = False):
        """
        Parse and export results to JSON file.
        
        Args:
            filepath: Path to output JSON file
            include_all_amounts: Whether to include all amounts
        """
        results = self.parse(include_all_amounts=include_all_amounts)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    def export_to_csv(self, filepath: str, include_all_amounts: bool = False):
        """
        Parse and export results to CSV file.
        
        Args:
            filepath: Path to output CSV file
            include_all_amounts: Whether to include all amounts
        """
        import csv
        
        results = self.parse(include_all_amounts=include_all_amounts)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Field Name', 'Value', 'Currency', 'Category', 
                'Confidence', 'Line Number', 'Context', 'Extraction Method'
            ])
            
            # Write data
            for field_dict in results['fields']:
                writer.writerow([
                    field_dict['field_name'],
                    field_dict['value'],
                    field_dict['currency'],
                    field_dict['category'],
                    field_dict['confidence'],
                    field_dict['line_number'],
                    field_dict['context'],
                    field_dict['extraction_method']
                ])
    
    def get_field_by_name(self, field_name: str) -> Optional[FinancialField]:
        """
        Retrieve a specific field by name.
        
        Args:
            field_name: Name of the field to retrieve
            
        Returns:
            FinancialField if found, None otherwise
        """
        for field in self.parsed_fields:
            if field.field_name == field_name:
                return field
        return None
    
    def get_fields_by_category(self, category: FieldCategory) -> List[FinancialField]:
        """
        Retrieve all fields of a specific category.
        
        Args:
            category: FieldCategory enum value
            
        Returns:
            List of matching fields
        """
        return [field for field in self.parsed_fields if field.category == category]


def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python insurance_parser.py <input_file> [output_format]")
        print("Output formats: json (default), csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'json'
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            document_text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    
    # Create parser and extract fields
    parser = InsuranceParser(document_text)
    
    # Generate output filename
    base_name = input_file.rsplit('.', 1)[0]
    
    if output_format.lower() == 'csv':
        output_file = f"{base_name}_parsed.csv"
        parser.export_to_csv(output_file)
    else:
        output_file = f"{base_name}_parsed.json"
        parser.export_to_json(output_file)
    
    print(f"✓ Parsing completed successfully")
    print(f"✓ Results saved to: {output_file}")
    
    # Display summary
    results = parser.parse()
    print(f"\nSummary:")
    print(f"  Total fields extracted: {results['metadata']['total_fields_extracted']}")
    print(f"  Pattern matches: {results['metadata']['pattern_matches']}")
    print(f"  Context matches: {results['metadata']['context_matches']}")
    print(f"  High confidence fields: {results['summary']['high_confidence_fields']}")


if __name__ == "__main__":
    main()