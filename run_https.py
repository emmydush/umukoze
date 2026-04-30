#!/usr/bin/env python3
"""
HTTPS Development Server for PWA Testing
Run this script to start the app with HTTPS support
"""

import os
import ssl
from app import app

def create_ssl_context():
    """Create SSL context for HTTPS development"""
    # Generate self-signed certificate if it doesn't exist
    cert_file = 'cert.pem'
    key_file = 'key.pem'
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("🔐 Generating self-signed SSL certificate...")
        os.system(f'openssl req -x509 -newkey rsa:4096 -keyout {key_file} -out {cert_file} -days 365 -nodes -subj "/C=RW/ST=Kigali/L=Kigali/O=Umukozi/CN=localhost"')
        print("✅ SSL certificate generated successfully!")
    
    # Create SSL context
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_file, key_file)
    return context

if __name__ == '__main__':
    print("🚀 Starting Umukozi PWA with HTTPS...")
    print("📱 Open https://localhost:5000 in your browser")
    print("⚠️  Accept the security warning (it's self-signed for development)")
    print("🔧 PWA install prompt should now appear!")
    
    try:
        context = create_ssl_context()
        app.run(host='localhost', port=5000, ssl_context=context, debug=True)
    except Exception as e:
        print(f"❌ Error starting HTTPS server: {e}")
        print("💡 Make sure OpenSSL is installed and in your PATH")
        print("🔄 Falling back to HTTP (PWA may not work properly)...")
        app.run(host='127.0.0.1', port=5000, debug=True)
