#!/usr/bin/env python3
"""
diagnose_services.py - Service Connectivity Diagnostic Tool

This script helps diagnose connectivity issues with external services
by testing different endpoints and providing detailed troubleshooting information.

File: diagnose_services.py
Purpose: Detailed service connectivity diagnostics and troubleshooting
Related: test_connections.py, integration_test.py, service configuration
Tags: diagnostics, troubleshooting, connectivity, services
"""

import os
import sys
import requests
import time
import socket
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_env_file():
    """Load environment variables from .env file."""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value

# Load environment variables
load_env_file()

@dataclass
class DiagnosticResult:
    """Result of a diagnostic test"""
    service: str
    test: str
    status: str  # 'success', 'failure', 'warning'
    message: str
    details: Optional[Dict] = None

class ServiceDiagnostics:
    """
    Comprehensive service diagnostics for troubleshooting connectivity issues.
    """
    
    def __init__(self):
        """Initialize the diagnostics tool."""
        self.results: List[DiagnosticResult] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BeepBoop-Diagnostics/1.0',
            'Content-Type': 'application/json'
        })
        
        # Load environment variables
        self.env = {
            'DIGI_CORE_API_URL': os.getenv('DIGI_CORE_API_URL', 'http://localhost:8000'),
            'DIGI_CORE_API_KEY': os.getenv('DIGI_CORE_API_KEY'),
            'PCS_BASE_URL': os.getenv('PCS_BASE_URL', 'http://localhost:8000'),
            'PCS_API_KEY': os.getenv('PCS_API_KEY'),
            'QDRANT_URL': os.getenv('QDRANT_URL', 'http://localhost:6333'),
            'QDRANT_API_KEY': os.getenv('QDRANT_API_KEY'),
            'NEO4J_URI': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            'NEO4J_USERNAME': os.getenv('NEO4J_USERNAME', 'neo4j'),
            'NEO4J_PASSWORD': os.getenv('NEO4J_PASSWORD'),
        }
    
    def add_result(self, service: str, test: str, status: str, message: str, details: Optional[Dict] = None):
        """Add a diagnostic result."""
        self.results.append(DiagnosticResult(
            service=service,
            test=test,
            status=status,
            message=message,
            details=details
        ))
    
    def test_port_connectivity(self, host: str, port: int, service_name: str) -> bool:
        """Test if a port is open and accepting connections."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def test_http_endpoints(self, base_url: str, endpoints: List[str], service_name: str, headers: Dict = None):
        """Test multiple HTTP endpoints for a service."""
        if headers is None:
            headers = {}
        
        for endpoint in endpoints:
            try:
                url = f"{base_url}{endpoint}"
                response = self.session.get(url, headers=headers, timeout=5)
                
                self.add_result(
                    service_name,
                    f"HTTP {endpoint}",
                    "success" if response.status_code < 400 else "failure",
                    f"HTTP {response.status_code}",
                    {"url": url, "status_code": response.status_code, "headers": dict(response.headers)}
                )
                
            except requests.exceptions.ConnectionError:
                self.add_result(
                    service_name,
                    f"HTTP {endpoint}",
                    "failure",
                    "Connection refused",
                    {"url": url}
                )
            except requests.exceptions.Timeout:
                self.add_result(
                    service_name,
                    f"HTTP {endpoint}",
                    "failure",
                    "Connection timeout",
                    {"url": url}
                )
            except Exception as e:
                self.add_result(
                    service_name,
                    f"HTTP {endpoint}",
                    "failure",
                    f"Error: {str(e)}",
                    {"url": url}
                )
    
    def diagnose_digi_core(self):
        """Diagnose Digi-Core service connectivity."""
        print("🧠 Diagnosing Digi-Core service...")
        
        # Parse URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.env['DIGI_CORE_API_URL'])
            host = parsed.hostname or 'localhost'
            port = parsed.port or 8000
        except:
            host, port = 'localhost', 8000
        
        # Test port connectivity
        port_open = self.test_port_connectivity(host, port, "Digi-Core")
        self.add_result(
            "Digi-Core",
            "Port Connectivity",
            "success" if port_open else "failure",
            f"Port {port} on {host} is {'open' if port_open else 'closed'}"
        )
        
        if not port_open:
            self.add_result(
                "Digi-Core",
                "Service Status",
                "failure",
                f"Service appears to be down - port {port} is not accessible"
            )
            return
        
        # Test various endpoints
        endpoints = [
            "/",
            "/health",
            "/api/health",
            "/status",
            "/api/status",
            "/v1/health",
            "/docs",
            "/swagger",
            "/api/docs"
        ]
        
        headers = {}
        if self.env['DIGI_CORE_API_KEY']:
            headers['Authorization'] = f"Bearer {self.env['DIGI_CORE_API_KEY']}"
        
        self.test_http_endpoints(self.env['DIGI_CORE_API_URL'], endpoints, "Digi-Core", headers)
    
    def diagnose_pcs(self):
        """Diagnose PCS service connectivity."""
        print("🎯 Diagnosing PCS service...")
        
        # Parse URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.env['PCS_BASE_URL'])
            host = parsed.hostname or 'localhost'
            port = parsed.port or 8000
        except:
            host, port = 'localhost', 8000
        
        # Test port connectivity
        port_open = self.test_port_connectivity(host, port, "PCS")
        self.add_result(
            "PCS",
            "Port Connectivity",
            "success" if port_open else "failure",
            f"Port {port} on {host} is {'open' if port_open else 'closed'}"
        )
        
        if not port_open:
            self.add_result(
                "PCS",
                "Service Status",
                "failure",
                f"Service appears to be down - port {port} is not accessible"
            )
            return
        
        # Test various endpoints
        endpoints = [
            "/",
            "/health",
            "/api/health",
            "/status",
            "/api/status",
            "/v1/health",
            "/docs",
            "/swagger",
            "/api/docs",
            "/api/prompts/health"
        ]
        
        headers = {
            'X-App-ID': 'beep-boop-v2'
        }
        if self.env['PCS_API_KEY']:
            headers['Authorization'] = f"Bearer {self.env['PCS_API_KEY']}"
        
        self.test_http_endpoints(self.env['PCS_BASE_URL'], endpoints, "PCS", headers)
    
    def diagnose_qdrant(self):
        """Diagnose Qdrant service connectivity."""
        print("🔍 Diagnosing Qdrant service...")
        
        # Parse URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.env['QDRANT_URL'])
            host = parsed.hostname or 'localhost'
            port = parsed.port or 6333
        except:
            host, port = 'localhost', 6333
        
        # Test port connectivity
        port_open = self.test_port_connectivity(host, port, "Qdrant")
        self.add_result(
            "Qdrant",
            "Port Connectivity",
            "success" if port_open else "failure",
            f"Port {port} on {host} is {'open' if port_open else 'closed'}"
        )
        
        if not port_open:
            self.add_result(
                "Qdrant",
                "Service Status",
                "failure",
                f"Service appears to be down - port {port} is not accessible"
            )
            return
        
        # Test Qdrant-specific endpoints
        endpoints = [
            "/",
            "/collections",
            "/health",
            "/metrics",
            "/cluster"
        ]
        
        headers = {}
        if self.env['QDRANT_API_KEY']:
            headers['api-key'] = self.env['QDRANT_API_KEY']
        
        self.test_http_endpoints(self.env['QDRANT_URL'], endpoints, "Qdrant", headers)
    
    def diagnose_neo4j(self):
        """Diagnose Neo4j service connectivity."""
        print("🕸️ Diagnosing Neo4j service...")
        
        # Parse URI
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.env['NEO4J_URI'])
            host = parsed.hostname or 'localhost'
            port = parsed.port or 7687
        except:
            host, port = 'localhost', 7687
        
        # Test port connectivity
        port_open = self.test_port_connectivity(host, port, "Neo4j")
        self.add_result(
            "Neo4j",
            "Port Connectivity",
            "success" if port_open else "failure",
            f"Port {port} on {host} is {'open' if port_open else 'closed'}"
        )
        
        if not port_open:
            self.add_result(
                "Neo4j",
                "Service Status",
                "failure",
                f"Service appears to be down - port {port} is not accessible"
            )
            return
        
        # Test HTTP endpoints (Neo4j also has HTTP interface)
        http_port = 7474  # Default Neo4j HTTP port
        http_open = self.test_port_connectivity(host, http_port, "Neo4j")
        self.add_result(
            "Neo4j",
            "HTTP Port Connectivity",
            "success" if http_open else "failure",
            f"HTTP port {http_port} on {host} is {'open' if http_open else 'closed'}"
        )
        
        if http_open:
            # Test Neo4j HTTP endpoints
            http_url = f"http://{host}:{http_port}"
            endpoints = [
                "/",
                "/db/data/",
                "/db/manage/",
                "/browser/"
            ]
            self.test_http_endpoints(http_url, endpoints, "Neo4j")
    
    def run_all_diagnostics(self):
        """Run all diagnostic tests."""
        print("🔧 Starting comprehensive service diagnostics...\n")
        
        self.diagnose_digi_core()
        self.diagnose_pcs()
        self.diagnose_qdrant()
        self.diagnose_neo4j()
        
        return self.results
    
    def print_summary(self):
        """Print a comprehensive diagnostic summary."""
        print("\n" + "="*80)
        print("🔍 SERVICE DIAGNOSTIC SUMMARY")
        print("="*80)
        
        # Group results by service
        services = {}
        for result in self.results:
            if result.service not in services:
                services[result.service] = []
            services[result.service].append(result)
        
        for service_name, results in services.items():
            print(f"\n📊 {service_name}:")
            print("-" * 40)
            
            for result in results:
                status_icon = {
                    "success": "✅",
                    "failure": "❌",
                    "warning": "⚠️"
                }.get(result.status, "❓")
                
                print(f"  {status_icon} {result.test}: {result.message}")
                
                if result.details:
                    for key, value in result.details.items():
                        if key == "url":
                            print(f"    🔗 URL: {value}")
                        elif key == "status_code":
                            print(f"    📊 Status: {value}")
                        elif key == "headers":
                            print(f"    📋 Headers: {len(value)} headers")
        
        print("\n" + "="*80)
        print("💡 TROUBLESHOOTING RECOMMENDATIONS:")
        print("="*80)
        
        # Analyze results and provide recommendations
        failed_services = set()
        for result in self.results:
            if result.status == "failure" and "Port Connectivity" in result.test:
                failed_services.add(result.service)
        
        if failed_services:
            print(f"\n🚨 Services that appear to be down: {', '.join(failed_services)}")
            print("\nTo start these services:")
            
            if "Digi-Core" in failed_services:
                print("  • Digi-Core: Check if the service is running on port 8000")
                print("    - Start with: docker-compose up digi-core")
                print("    - Or check service status: systemctl status digi-core")
            
            if "PCS" in failed_services:
                print("  • PCS: Check if the service is running on port 8000")
                print("    - Start with: docker-compose up pcs")
                print("    - Or check service status: systemctl status pcs")
            
            if "Qdrant" in failed_services:
                print("  • Qdrant: Check if the service is running on port 6333")
                print("    - Start with: docker run -d -p 6333:6333 qdrant/qdrant")
                print("    - Or check service status: systemctl status qdrant")
            
            if "Neo4j" in failed_services:
                print("  • Neo4j: Check if the service is running on port 7687")
                print("    - Start with: docker run -d -p 7474:7474 -p 7687:7687 neo4j")
                print("    - Or check service status: systemctl status neo4j")
        
        # Check for API key issues
        api_key_issues = []
        for result in self.results:
            if "403" in result.message or "Invalid api-key" in result.message:
                api_key_issues.append(result.service)
        
        if api_key_issues:
            print(f"\n🔑 API Key issues detected: {', '.join(api_key_issues)}")
            print("  • Check your .env file for correct API keys")
            print("  • Verify API keys are valid and have proper permissions")
        
        print("\n" + "="*80)

def main():
    """Main function to run service diagnostics."""
    print("🔧 Beep-Boop Service Diagnostics")
    print("Comprehensive connectivity troubleshooting...\n")
    
    diagnostics = ServiceDiagnostics()
    results = diagnostics.run_all_diagnostics()
    diagnostics.print_summary()
    
    # Exit with appropriate code
    critical_failures = sum(1 for r in results if r.status == "failure" and "Port Connectivity" in r.test)
    if critical_failures > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
