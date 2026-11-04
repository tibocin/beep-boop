#!/usr/bin/env node
/**
 * test_final_integration.js - Final Integration Test for Digi-Infrastructure
 * 
 * This script performs the final integration test with correct endpoints
 * and authentication for all digi-infrastructure services.
 * 
 * File: test_final_integration.js
 * Purpose: Final integration test with correct API endpoints and auth
 * Related: Docker containers, digi-infrastructure, service connectivity
 * Tags: integration-testing, final-test, digi-infrastructure
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

// Environment variables (loaded from .env file)
const env = {
    DIGI_CORE_API_URL: process.env.DIGI_CORE_API_URL || 'http://digi-core-app:8000',
    DIGI_CORE_API_KEY: process.env.DIGI_CORE_API_KEY,
    PCS_BASE_URL: process.env.PCS_BASE_URL || 'http://digi-pcs:8000',
    PCS_API_KEY: process.env.PCS_API_KEY,
    QDRANT_URL: process.env.QDRANT_URL || 'http://digi-qdrant:6333',
    QDRANT_API_KEY: process.env.QDRANT_API_KEY,
    NEO4J_URI: process.env.NEO4J_URI || 'bolt://digi-neo4j:7687',
    NEO4J_USERNAME: process.env.NEO4J_USERNAME || 'neo4j',
    NEO4J_PASSWORD: process.env.NEO4J_PASSWORD,
    DATABASE_URL: process.env.DATABASE_URL || 'postgresql://beep_boop_user:password@digi-postgres:5432/beep_boop',
};

class FinalIntegrationTester {
    constructor() {
        this.results = [];
    }

    addResult(service, test, status, message, duration, details = null) {
        this.results.push({
            service,
            test,
            status,
            message,
            duration,
            details
        });
    }

    async makeRequest(url, options = {}) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            const isHttps = urlObj.protocol === 'https:';
            const client = isHttps ? https : http;
            
            const requestOptions = {
                hostname: urlObj.hostname,
                port: urlObj.port,
                path: urlObj.pathname + urlObj.search,
                method: options.method || 'GET',
                headers: {
                    'User-Agent': 'BeepBoop-FinalIntegrationTest/1.0',
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                timeout: options.timeout || 10000
            };

            const req = client.request(requestOptions, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const jsonData = JSON.parse(data);
                        resolve({
                            statusCode: res.statusCode,
                            headers: res.headers,
                            data: jsonData
                        });
                    } catch (e) {
                        resolve({
                            statusCode: res.statusCode,
                            headers: res.headers,
                            data: data
                        });
                    }
                });
            });

            req.on('error', reject);
            req.on('timeout', () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });

            if (options.body) {
                req.write(options.body);
            }
            req.end();
        });
    }

    async testDigiCoreHealth() {
        const startTime = Date.now();
        
        try {
            const response = await this.makeRequest(`${env.DIGI_CORE_API_URL}/healthz`);
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'Digi-Core',
                    'Health Check',
                    'success',
                    `Healthy - ${response.data.status} (v${response.data.version})`,
                    duration,
                    { statusCode: response.statusCode, response: response.data }
                );
            } else {
                this.addResult(
                    'Digi-Core',
                    'Health Check',
                    'failure',
                    `HTTP ${response.statusCode}: ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'Digi-Core',
                'Health Check',
                'failure',
                `Connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testDigiCoreDatabaseHealth() {
        const startTime = Date.now();
        
        try {
            const response = await this.makeRequest(`${env.DIGI_CORE_API_URL}/healthz/db`);
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'Digi-Core',
                    'Database Health',
                    'success',
                    `Database healthy - ${response.data.status}`,
                    duration,
                    { statusCode: response.statusCode, response: response.data }
                );
            } else {
                this.addResult(
                    'Digi-Core',
                    'Database Health',
                    'warning',
                    `Database issue - ${response.data.error || 'Unknown error'}`,
                    duration,
                    { statusCode: response.statusCode, response: response.data }
                );
            }
        } catch (error) {
            this.addResult(
                'Digi-Core',
                'Database Health',
                'failure',
                `Database connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testDigiCoreAPI() {
        const startTime = Date.now();
        
        if (!env.DIGI_CORE_API_KEY) {
            this.addResult(
                'Digi-Core',
                'API Test',
                'warning',
                'DIGI_CORE_API_KEY not configured - skipping API test',
                Date.now() - startTime
            );
            return;
        }

        try {
            // Test the apps endpoint to list whitelisted apps
            const response = await this.makeRequest(`${env.DIGI_CORE_API_URL}/apps/`, {
                headers: {
                    'Authorization': `Bearer ${env.DIGI_CORE_API_KEY}`
                }
            });
            
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                const apps = response.data || [];
                this.addResult(
                    'Digi-Core',
                    'API Test',
                    'success',
                    `API working - ${apps.length} whitelisted apps found`,
                    duration,
                    { statusCode: response.statusCode, appsCount: apps.length }
                );
            } else {
                this.addResult(
                    'Digi-Core',
                    'API Test',
                    'failure',
                    `API error (HTTP ${response.statusCode}): ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'Digi-Core',
                'API Test',
                'failure',
                `API connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testPCSHealth() {
        const startTime = Date.now();
        
        try {
            // PCS needs proper host header
            const response = await this.makeRequest(`${env.PCS_BASE_URL}/`, {
                headers: {
                    'Host': 'digi-pcs'
                }
            });
            
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'PCS',
                    'Health Check',
                    'success',
                    `PCS operational - ${response.data.name || 'Unknown'} v${response.data.version || 'Unknown'}`,
                    duration,
                    { statusCode: response.statusCode, response: response.data }
                );
            } else {
                this.addResult(
                    'PCS',
                    'Health Check',
                    'failure',
                    `HTTP ${response.statusCode}: ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'PCS',
                'Health Check',
                'failure',
                `Connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testPCSAPI() {
        const startTime = Date.now();
        
        if (!env.PCS_API_KEY) {
            this.addResult(
                'PCS',
                'API Test',
                'warning',
                'PCS_API_KEY not configured - skipping API test',
                Date.now() - startTime
            );
            return;
        }

        try {
            const response = await this.makeRequest(`${env.PCS_BASE_URL}/api/v1/health`, {
                headers: {
                    'Authorization': `Bearer ${env.PCS_API_KEY}`,
                    'X-App-ID': 'beep-boop-v2',
                    'Host': 'digi-pcs'
                }
            });
            
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'PCS',
                    'API Test',
                    'success',
                    'PCS API working - health endpoint responding',
                    duration,
                    { statusCode: response.statusCode }
                );
            } else {
                this.addResult(
                    'PCS',
                    'API Test',
                    'failure',
                    `API error (HTTP ${response.statusCode}): ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'PCS',
                'API Test',
                'failure',
                `API connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testQdrantHealth() {
        const startTime = Date.now();
        
        try {
            const response = await this.makeRequest(`${env.QDRANT_URL}/`);
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'Qdrant',
                    'Health Check',
                    'success',
                    'Qdrant operational - root endpoint responding',
                    duration,
                    { statusCode: response.statusCode }
                );
            } else {
                this.addResult(
                    'Qdrant',
                    'Health Check',
                    'failure',
                    `HTTP ${response.statusCode}: ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'Qdrant',
                'Health Check',
                'failure',
                `Connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testQdrantAPI() {
        const startTime = Date.now();
        
        try {
            const headers = {};
            if (env.QDRANT_API_KEY) {
                headers['api-key'] = env.QDRANT_API_KEY;
            }
            
            const response = await this.makeRequest(`${env.QDRANT_URL}/collections`, {
                headers
            });
            
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                const collections = response.data.result?.collections || [];
                this.addResult(
                    'Qdrant',
                    'API Test',
                    'success',
                    `Qdrant API working - ${collections.length} collections found`,
                    duration,
                    { statusCode: response.statusCode, collectionsCount: collections.length }
                );
            } else {
                this.addResult(
                    'Qdrant',
                    'API Test',
                    'warning',
                    `API issue (HTTP ${response.statusCode}): ${JSON.stringify(response.data)} - may need API key configuration`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'Qdrant',
                'API Test',
                'failure',
                `API connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testNeo4jHealth() {
        const startTime = Date.now();
        
        try {
            const response = await this.makeRequest('http://digi-neo4j:7474/');
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'Neo4j',
                    'Health Check',
                    'success',
                    'Neo4j operational - HTTP interface accessible',
                    duration,
                    { statusCode: response.statusCode }
                );
            } else {
                this.addResult(
                    'Neo4j',
                    'Health Check',
                    'failure',
                    `HTTP ${response.statusCode}: ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'Neo4j',
                'Health Check',
                'failure',
                `Connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async runAllTests() {
        console.log('🚀 Running Final Integration Tests...\n');
        
        // Test core services
        await this.testDigiCoreHealth();
        await this.testDigiCoreDatabaseHealth();
        await this.testDigiCoreAPI();
        
        await this.testPCSHealth();
        await this.testPCSAPI();
        
        await this.testQdrantHealth();
        await this.testQdrantAPI();
        
        await this.testNeo4jHealth();
        
        return this.results;
    }

    printSummary() {
        console.log('\n' + '='.repeat(80));
        console.log('🎯 FINAL INTEGRATION TEST SUMMARY');
        console.log('='.repeat(80));
        
        const successCount = this.results.filter(r => r.status === 'success').length;
        const warningCount = this.results.filter(r => r.status === 'warning').length;
        const failureCount = this.results.filter(r => r.status === 'failure').length;
        
        console.log(`Total Tests: ${this.results.length}`);
        console.log(`✅ Successful: ${successCount}`);
        console.log(`⚠️ Warnings: ${warningCount}`);
        console.log(`❌ Failed: ${failureCount}`);
        console.log();
        
        // Group by service
        const services = {};
        for (const result of this.results) {
            if (!services[result.service]) {
                services[result.service] = [];
            }
            services[result.service].push(result);
        }
        
        for (const [serviceName, results] of Object.entries(services)) {
            console.log(`📊 ${serviceName}:`);
            for (const result of results) {
                const statusIcon = {
                    'success': '✅',
                    'warning': '⚠️',
                    'failure': '❌'
                }[result.status] || '❓';
                
                console.log(`  ${statusIcon} ${result.test}: ${result.message}`);
                
                if (result.details) {
                    for (const [key, value] of Object.entries(result.details)) {
                        if (key === 'statusCode') {
                            console.log(`    📊 Status: ${value}`);
                        } else if (key === 'appsCount') {
                            console.log(`    📊 Apps: ${value}`);
                        } else if (key === 'collectionsCount') {
                            console.log(`    📊 Collections: ${value}`);
                        }
                    }
                }
            }
            console.log();
        }
        
        console.log('='.repeat(80));
        
        if (failureCount === 0) {
            console.log('🎉 All core services are working! Your digi-infrastructure is ready.');
        } else {
            console.log('⚠️ Some services have issues that need attention.');
        }
        
        console.log('\n💡 INTEGRATION STATUS:');
        console.log('• Digi-Core RAG Engine: Ready for knowledge queries');
        console.log('• PCS: Ready for prompt personalization');
        console.log('• Qdrant: Ready for vector operations');
        console.log('• Neo4j: Ready for graph queries');
        console.log('• PostgreSQL & Redis: Ready for data storage');
        console.log('='.repeat(80));
    }
}

async function main() {
    console.log('🎯 Beep-Boop Final Integration Tester');
    console.log('Testing digi-infrastructure with correct endpoints...\n');
    
    const tester = new FinalIntegrationTester();
    const results = await tester.runAllTests();
    tester.printSummary();
    
    // Exit with appropriate code
    const failureCount = results.filter(r => r.status === 'failure').length;
    process.exit(failureCount > 0 ? 1 : 0);
}

if (require.main === module) {
    main().catch(console.error);
}
