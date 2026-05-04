#!/usr/bin/env python3
"""
Error handling and logging utilities for Umukozi
"""

import logging
import traceback
from datetime import datetime
import os

def setup_logging():
    """Setup application logging"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def log_error(error, context=""):
    """Log error with context"""
    logger = setup_logging()
    error_msg = f"{context}: {str(error)}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    
    # Also save to error log file
    with open('logs/errors.log', 'a') as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"Timestamp: {datetime.now()}\n")
        f.write(f"Context: {context}\n")
        f.write(f"Error: {str(error)}\n")
        f.write(f"Traceback:\n{traceback.format_exc()}\n")

def test_critical_components():
    """Test critical application components"""
    logger = setup_logging()
    logger.info("Testing critical components...")
    
    try:
        # Test imports
        from app import app, db
        logger.info(" App imports successful")
        
        # Test database
        with app.app_context():
            from models import User
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            logger.info(" Database connection successful")
        
        # Test routes
        routes = list(app.url_map.iter_rules())
        logger.info(f" {len(routes)} routes loaded")
        
        return True
        
    except Exception as e:
        log_error(e, "Component Test")
        return False

if __name__ == '__main__':
    print("🔍 Testing application components...")
    if test_critical_components():
        print("✅ All components working correctly!")
    else:
        print("❌ Component test failed - check logs/errors.log")
