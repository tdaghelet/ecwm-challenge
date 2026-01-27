#!/usr/bin/env python3
"""
Serveur web local pour tester le site

Usage:
    python3 serve.py

Puis ouvrir http://localhost:8000 dans le navigateur
"""
import http.server
import socketserver
import os

PORT = 8000
DIRECTORY = "docs"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    if not os.path.exists(DIRECTORY):
        print(f"❌ Le dossier '{DIRECTORY}' n'existe pas.")
        print("Exécutez d'abord 'python3 generate_site.py'")
        exit(1)

    print("🌐 Serveur web ECWM Challenge")
    print("=" * 50)
    print(f"📁 Dossier: {DIRECTORY}/")
    print(f"🔗 URL: http://localhost:{PORT}")
    print("\n💡 Appuyez sur Ctrl+C pour arrêter\n")
    print("=" * 50)

    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ Serveur arrêté")
