#!/usr/bin/env python3
"""
Health Check Script for automacaoGLPI
Verifica: DB, SMTP, Zabbix, Disk Space, Logs
"""

import sys
import os
import shutil
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

class HealthChecker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.issues = []
    
    def check_env_file(self):
        """Verifica se .env existe"""
        try:
            if os.path.exists(os.path.join(BASE_DIR, '.env')):
                self.passed += 1
                return True
            else:
                self.issues.append(".env file not found")
                self.failed += 1
                return False
        except Exception as e:
            self.issues.append(f"Error checking .env: {e}")
            self.failed += 1
            return False
    
    def check_database(self):
        """Verifica conexão com GLPI"""
        try:
            from services.database import executar_query
            executar_query("SELECT 1")
            self.passed += 1
            return True
        except Exception as e:
            self.issues.append(f"Database: {str(e)[:80]}")
            self.failed += 1
            return False
    
    def check_smtp(self):
        """Verifica SMTP"""
        try:
            from services.mailer import conectar
            server = conectar()
            server.quit()
            self.passed += 1
            return True
        except Exception as e:
            self.issues.append(f"SMTP: {str(e)[:80]}")
            self.failed += 1
            return False
    
    def check_disk_space(self, min_mb=100):
        """Verifica espaço em disco"""
        try:
            stat = shutil.disk_usage('/')
            free_mb = stat.free / (1024 * 1024)
            
            if free_mb < min_mb:
                self.issues.append(f"Low disk: {free_mb:.0f}MB")
                self.failed += 1
                return False
            
            self.passed += 1
            return True
        except Exception as e:
            self.issues.append(f"Disk check: {e}")
            self.failed += 1
            return False
    
    def check_logs_directory(self):
        """Verifica diretório de logs"""
        try:
            log_dir = Path(BASE_DIR) / 'logs'
            if not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)
            
            test_file = log_dir / '.healthcheck'
            test_file.touch()
            test_file.unlink()
            
            self.passed += 1
            return True
        except Exception as e:
            self.issues.append(f"Logs dir: {e}")
            self.failed += 1
            return False
    
    def run(self):
        """Executa todos os checks"""
        print("\n🔍 Health Check - automacaoGLPI")
        print("=" * 60)
        
        checks = [
            ("📋 .env file", self.check_env_file()),
            ("🗄️  Database", self.check_database()),
            ("📧 SMTP", self.check_smtp()),
            ("💾 Disk Space", self.check_disk_space()),
            ("📝 Logs Dir", self.check_logs_directory()),
        ]
        
        for name, result in checks:
            status = "✅" if result else "❌"
            print(f"{name:.<40} {status}")
        
        print("=" * 60)
        print(f"\nResult: {self.passed}✅ {self.failed}❌")
        
        if self.issues:
            print("\n⚠️  Issues:")
            for issue in self.issues:
                print(f"   - {issue}")
        
        if self.failed == 0:
            print("\n✅ All checks passed!")
            return 0
        else:
            print(f"\n❌ {self.failed} checks failed!")
            return 1

if __name__ == '__main__':
    checker = HealthChecker()
    sys.exit(checker.run())
