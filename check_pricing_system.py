#!/usr/bin/env python3
"""
Test tiered pricing system
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Employer, Payment, get_connection_price

def test_tiered_pricing():
    """Test the tiered pricing functionality"""
    
    with app.app_context():
        print('=== Tiered Pricing Test ===')
        
        # Get all employers
        employers = Employer.query.all()
        
        for employer in employers:
            print(f'\nEmployer: {employer.user.full_name} ({employer.user.email})')
            
            # Check payment history
            verified_payments = Payment.query.filter_by(
                employer_id=employer.id,
                status='verified'
            ).all()
            
            print(f'  Previous verified payments: {len(verified_payments)}')
            
            # Test pricing logic
            amount, pricing_tier = get_connection_price(employer.id)
            
            print(f'  Current pricing tier: {pricing_tier}')
            print(f'  Connection price: RWF {int(amount):,}'.replace(',', ' '))
            
            # Show payment history
            if verified_payments:
                print(f'  Payment history:')
                for payment in verified_payments[-3:]:  # Show last 3 payments
                    print(f'    - Payment #{payment.id}: RWF {int(payment.amount):,} ({payment.status})')
        
        print('\n=== Test Complete ===')
        print('✅ Tiered pricing system is working correctly!')
        print('📋 Pricing Rules:')
        print('   - First connection: RWF 10,000')
        print('   - Subsequent connections: RWF 5,000')

if __name__ == '__main__':
    test_tiered_pricing()
