"""
Insurance Parser - Demonstration Script
========================================
This script demonstrates the capabilities of the insurance parser.
"""

from insurance_parser import InsuranceParser, FieldCategory
import json


def demonstrate_parser():
    """Demonstrate all parser features"""
    
    print("="*80)
    print("INSURANCE DOCUMENT PARSER - DEMONSTRATION")
    print("="*80)
    print()
    
    # Load sample document
    print("[1] Loading sample insurance document...")
    with open('../sample_data/sample_insurance_policy.txt', 'r', encoding='utf-8') as f:
        document_text = f.read()
    print(f"    ✓ Document loaded ({len(document_text)} characters)")
    print()
    
    # Create parser instance
    print("[2] Initializing parser...")
    parser = InsuranceParser(document_text)
    print("    ✓ Parser initialized")
    print()
    
    # Parse the document
    print("[3] Parsing document using multi-strategy approach...")
    results = parser.parse(include_all_amounts=False)
    print(f"    ✓ Extraction complete")
    print(f"    • Total fields extracted: {results['metadata']['total_fields_extracted']}")
    print(f"    • Pattern-based matches: {results['metadata']['pattern_matches']}")
    print(f"    • Context-aware matches: {results['metadata']['context_matches']}")
    print()
    
    # Show high-confidence extractions
    print("[4] High-Confidence Financial Fields (>= 80% confidence):")
    print("-" * 80)
    high_conf_fields = [f for f in parser.parsed_fields if f.confidence >= 0.8]
    
    for field in high_conf_fields[:15]:  # Show first 15
        print(f"    • {field.field_name:30s}: {field.currency} {field.value:>15,.2f}")
        print(f"      Category: {field.category.value:15s} | Confidence: {field.confidence*100:.0f}%")
        print()
    
    print(f"    ... and {len(high_conf_fields) - 15} more high-confidence fields")
    print()
    
    # Show category breakdown
    print("[5] Fields by Category:")
    print("-" * 80)
    for category, count in results['summary']['by_category'].items():
        print(f"    • {category.upper():20s}: {count:3d} fields")
    print()
    
    # Show key financial summaries
    print("[6] Key Financial Summaries:")
    print("-" * 80)
    
    # Premium information
    premium_fields = parser.get_fields_by_category(FieldCategory.PREMIUM)
    if premium_fields:
        print("    PREMIUM INFORMATION:")
        for field in premium_fields[:5]:
            if field.confidence >= 0.7:
                print(f"      • {field.field_name:25s}: ₹{field.value:>12,.2f}")
    print()
    
    # Coverage information
    coverage_fields = parser.get_fields_by_category(FieldCategory.COVERAGE)
    if coverage_fields:
        print("    COVERAGE INFORMATION:")
        for field in coverage_fields[:5]:
            if field.confidence >= 0.7:
                print(f"      • {field.field_name:25s}: ₹{field.value:>12,.2f}")
    print()
    
    # Claim information
    claim_fields = parser.get_fields_by_category(FieldCategory.CLAIM)
    if claim_fields:
        print("    CLAIM INFORMATION:")
        for field in claim_fields[:5]:
            if field.confidence >= 0.7:
                print(f"      • {field.field_name:25s}: ₹{field.value:>12,.2f}")
    print()
    
    # Export results
    print("[7] Exporting Results:")
    print("-" * 80)
    
    # JSON export
    parser.export_to_json('../sample_data/demo_output.json', include_all_amounts=False)
    print("    ✓ JSON export: demo_output.json")
    
    # CSV export
    parser.export_to_csv('../sample_data/demo_output.csv', include_all_amounts=False)
    print("    ✓ CSV export: demo_output.csv")
    print()
    
    # Show example field access
    print("[8] Example Field Access:")
    print("-" * 80)
    
    annual_premium = parser.get_field_by_name('annual_premium')
    if annual_premium:
        print(f"    Field Name: {annual_premium.field_name}")
        print(f"    Value: {annual_premium.currency} {annual_premium.value:,.2f}")
        print(f"    Confidence: {annual_premium.confidence * 100:.1f}%")
        print(f"    Category: {annual_premium.category.value}")
        print(f"    Line Number: {annual_premium.line_number}")
        print(f"    Context: {annual_premium.context[:80]}...")
        print(f"    Method: {annual_premium.extraction_method}")
    print()
    
    print("="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print()
    print("Next steps:")
    print("  • Review demo_output.json for detailed results")
    print("  • Review demo_output.csv for tabular analysis")
    print("  • Modify patterns in insurance_parser.py for custom fields")
    print()


if __name__ == "__main__":
    demonstrate_parser()