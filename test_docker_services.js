#!/usr/bin/env node
/**
 * test_docker_services.js - Test Docker Container Services (Node.js version)
 * 
 * This script tests connections to the digi-infrastructure Docker containers
 * using their container names and proper network connectivity.
 * 
 * File: test_docker_services.js
 * Purpose: Test Docker container services with proper container names
 * Related: Docker containers, digi-net network, service connectivity
 * Tags: docker, containers, digi-infrastructure, network-testing
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

// Docker container configurations
const dockerServices = {
    'digi-core-app': {
        type: 'Digi-Core RAG Engine',
        internalPort: 8000,
        externalPort: 2000,
        healthEndpoints: ['/', '/health', '/api/health', '/status'],
        apiEndpoints: ['/api/knowledge/query', '/api/health']
    },
    'digi-pcs': {
        type: 'PCS (Prompt Context Service)',
        internalPort: 8000,
        externalPort: 8000,
        healthEndpoints: ['/', '/health', '/api/v1/health', '/status'],
        apiEndpoints: ['/api/v1/prompts', '/api/v1/health']
    },
    'digi-qdrant': {
        type: 'Qdrant Vector Database',
        internalPort: 6333,
        externalPort: 6333,
        healthEndpoints: ['/', '/collections', '/health', '/metrics'],
        apiEndpoints: ['/collections', '/metrics', '/cluster']
    },
    'digi-neo4j': {
        type: 'Neo4j Graph Database',
        internalPort: 7474,
        externalPort: 7474,
        healthEndpoints: ['/', '/browser/', '/db/data/'],
        apiEndpoints: ['/db/data/', '/db/manage/']
    },
    'digi-postgres': {
        type: 'PostgreSQL Database',
        internalPort: 5432,
        externalPort: 5432,
        healthEndpoints: [], // PostgreSQL doesn't have HTTP endpoints
        apiEndpoints: []
    },
    'digi-redis': {
        type: 'Redis Cache',
        internalPort: 6379,
        externalPort: 6379,
        healthEndpoints: [], // Redis doesn't have HTTP endpoints
        apiEndpoints: []
    }
};

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

class DockerServiceTester {
    constructor() {
        this.results = [];
    }

    addResult(containerName, serviceType, test, status, message, duration, details = null) {
        this.results.push({
            containerName,
            serviceType,
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
                    'User-Agent': 'BeepBoop-DockerServiceTest/1.0',
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                timeout: options.timeout || 5000
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

    async testContainerConnectivity(containerName, serviceConfig) {
        const startTime = Date.now();
        
        // Test internal connectivity
        const internalUrl = `http://${containerName}:${serviceConfig.internalPort}`;
        try {
            const response = await this.makeRequest(`${internalUrl}/`);
            const duration = Date.now() - startTime;
            
            if (response.statusCode < 400) {
                this.addResult(
                    containerName,
                    serviceConfig.type,
                    'Internal Connectivity',
                    'success',
                    `Internal connection successful (HTTP ${response.statusCode})`,
                    duration,
                    { url: internalUrl, statusCode: response.statusCode }
                );
            } else {
                this.addResult(
                    containerName,
                    serviceConfig.type,
                    'Internal Connectivity',
                    'failure',
                    `Internal connection failed (HTTP ${response.statusCode})`,
                    duration,
                    { url: internalUrl, statusCode: response.statusCode }
                );
            }
        } catch (error) {
            this.addResult(
                containerName,
                serviceConfig.type,
                'Internal Connectivity',
                'failure',
                `Internal connection error: ${error.message}`,
                Date.now() - startTime,
                { url: internalUrl }
            );
        }

        // Test external connectivity
        const externalStartTime = Date.now();
        const externalUrl = `http://localhost:${serviceConfig.externalPort}`;
        try {
            const response = await this.makeRequest(`${externalUrl}/`);
            const duration = Date.now() - externalStartTime;
            
            if (response.statusCode < 400) {
                this.addResult(
                    containerName,
                    serviceConfig.type,
                    'External Connectivity',
                    'success',
                    `External connection successful (HTTP ${response.statusCode})`,
                    duration,
                    { url: externalUrl, statusCode: response.statusCode }
                );
            } else {
                this.addResult(
                    containerName,
                    serviceConfig.type,
                    'External Connectivity',
                    'failure',
                    `External connection failed (HTTP ${response.statusCode})`,
                    duration,
                    { url: externalUrl, statusCode: response.statusCode }
                );
            }
        } catch (error) {
            this.addResult(
                containerName,
                serviceConfig.type,
                'External Connectivity',
                'failure',
                `External connection error: ${error.message}`,
                Date.now() - externalStartTime,
                { url: externalUrl }
            );
        }
    }

    async testServiceHealth(containerName, serviceConfig) {
        if (!serviceConfig.healthEndpoints.length) {
            this.addResult(
                containerName,
                serviceConfig.type,
                'Health Check',
                'warning',
                'No HTTP health endpoints available',
                0
            );
            return;
        }

        const internalUrl = `http://${containerName}:${serviceConfig.internalPort}`;
        const workingEndpoints = [];
        const failedEndpoints = [];

        for (const endpoint of serviceConfig.healthEndpoints) {
            try {
                const response = await this.makeRequest(`${internalUrl}${endpoint}`);
                if (response.statusCode < 400) {
                    workingEndpoints.push(`${endpoint} (HTTP ${response.statusCode})`);
                } else {
                    failedEndpoints.push(`${endpoint} (HTTP ${response.statusCode})`);
                }
            } catch (error) {
                failedEndpoints.push(`${endpoint} (Error: ${error.message})`);
            }
        }

        if (workingEndpoints.length > 0) {
            this.addResult(
                containerName,
                serviceConfig.type,
                'Health Check',
                'success',
                `Found ${workingEndpoints.length} working health endpoints`,
                0,
                { workingEndpoints, failedEndpoints }
            );
        } else {
            this.addResult(
                containerName,
                serviceConfig.type,
                'Health Check',
                'failure',
                'No working health endpoints found',
                0,
                { failedEndpoints }
            );
        }
    }

    async testDigiCoreApi() {
        const startTime = Date.now();
        
        if (!env.DIGI_CORE_API_KEY) {
            this.addResult(
                'digi-core-app',
                'Digi-Core RAG Engine',
                'API Test',
                'warning',
                'DIGI_CORE_API_KEY not configured',
                Date.now() - startTime
            );
            return;
        }

        try {
            const response = await this.makeRequest(`${env.DIGI_CORE_API_URL}/health`, {
                headers: {
                    'Authorization': `Bearer ${env.DIGI_CORE_API_KEY}`
                }
            });
            
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'digi-core-app',
                    'Digi-Core RAG Engine',
                    'API Test',
                    'success',
                    `API working - ${response.data.status || 'unknown status'}`,
                    duration,
                    { statusCode: response.statusCode, response: response.data }
                );
            } else {
                this.addResult(
                    'digi-core-app',
                    'Digi-Core RAG Engine',
                    'API Test',
                    'failure',
                    `API error (HTTP ${response.statusCode}): ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'digi-core-app',
                'Digi-Core RAG Engine',
                'API Test',
                'failure',
                `API connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testPcsApi() {
        const startTime = Date.now();
        
        if (!env.PCS_API_KEY) {
            this.addResult(
                'digi-pcs',
                'PCS (Prompt Context Service)',
                'API Test',
                'warning',
                'PCS_API_KEY not configured',
                Date.now() - startTime
            );
            return;
        }

        try {
            const response = await this.makeRequest(`${env.PCS_BASE_URL}/api/v1/health`, {
                headers: {
                    'Authorization': `Bearer ${env.PCS_API_KEY}`,
                    'X-App-ID': 'beep-boop-v2'
                }
            });
            
            const duration = Date.now() - startTime;
            
            if (response.statusCode === 200) {
                this.addResult(
                    'digi-pcs',
                    'PCS (Prompt Context Service)',
                    'API Test',
                    'success',
                    'API working - health endpoint responding',
                    duration,
                    { statusCode: response.statusCode }
                );
            } else {
                this.addResult(
                    'digi-pcs',
                    'PCS (Prompt Context Service)',
                    'API Test',
                    'failure',
                    `API error (HTTP ${response.statusCode}): ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'digi-pcs',
                'PCS (Prompt Context Service)',
                'API Test',
                'failure',
                `API connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async testQdrantApi() {
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
                    'digi-qdrant',
                    'Qdrant Vector Database',
                    'API Test',
                    'success',
                    `API working - ${collections.length} collections found`,
                    duration,
                    { statusCode: response.statusCode, collectionsCount: collections.length }
                );
            } else {
                this.addResult(
                    'digi-qdrant',
                    'Qdrant Vector Database',
                    'API Test',
                    'failure',
                    `API error (HTTP ${response.statusCode}): ${JSON.stringify(response.data)}`,
                    duration
                );
            }
        } catch (error) {
            this.addResult(
                'digi-qdrant',
                'Qdrant Vector Database',
                'API Test',
                'failure',
                `API connection error: ${error.message}`,
                Date.now() - startTime
            );
        }
    }

    async runAllTests() {
        console.log('🐳 Testing Docker Container Services...\n');
        
        // Test each container
        for (const [containerName, serviceConfig] of Object.entries(dockerServices)) {
            console.log(`🔍 Testing ${containerName} (${serviceConfig.type})...`);
            
            // Test basic connectivity
            await this.testContainerConnectivity(containerName, serviceConfig);
            
            // Test health endpoints
            await this.testServiceHealth(containerName, serviceConfig);
        }
        
        // Test specific API functionality
        await this.testDigiCoreApi();
        await this.testPcsApi();
        await this.testQdrantApi();
        
        return this.results;
    }

    printSummary() {
        console.log('\n' + '='.repeat(80));
        console.log('🐳 DOCKER CONTAINER SERVICES TEST SUMMARY');
        console.log('='.repeat(80));
        
        const successCount = this.results.filter(r => r.status === 'success').length;
        const warningCount = this.results.filter(r => r.status === 'warning').length;
        const failureCount = this.results.filter(r => r.status === 'failure').length;
        
        console.log(`Total Tests: ${this.results.length}`);
        console.log(`✅ Successful: ${successCount}`);
        console.log(`⚠️ Warnings: ${warningCount}`);
        console.log(`❌ Failed: ${failureCount}`);
        console.log();
        
        // Group by container
        const containers = {};
        for (const result of this.results) {
            if (!containers[result.containerName]) {
                containers[result.containerName] = [];
            }
            containers[result.containerName].push(result);
        }
        
        for (const [containerName, results] of Object.entries(containers)) {
            const serviceType = results[0].serviceType;
            console.log(`📦 ${containerName} (${serviceType}):`);
            console.log('-'.repeat(60));
            
            for (const result of results) {
                const statusIcon = {
                    'success': '✅',
                    'warning': '⚠️',
                    'failure': '❌'
                }[result.status] || '❓';
                
                console.log(`  ${statusIcon} ${result.test}: ${result.message}`);
                
                if (result.details) {
                    for (const [key, value] of Object.entries(result.details)) {
                        if (key === 'url') {
                            console.log(`    🔗 URL: ${value}`);
                        } else if (key === 'statusCode') {
                            console.log(`    📊 Status: ${value}`);
                        } else if (key === 'workingEndpoints') {
                            console.log(`    ✅ Working: ${value.join(', ')}`);
                        } else if (key === 'failedEndpoints') {
                            console.log(`    ❌ Failed: ${value.join(', ')}`);
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
            console.log('🎉 All Docker container services are working correctly!');
        } else {
            console.log('⚠️ Some Docker container services have issues.');
        }
        
        console.log('\n💡 DOCKER NETWORK RECOMMENDATIONS:');
        console.log('• Ensure beep-boop is connected to the digi-net network');
        console.log('• Use container names for internal communication');
        console.log('• Use localhost:port for external access');
        console.log('• Verify all required environment variables are set');
        console.log('='.repeat(80));
    }
}

async function main() {
    console.log('🐳 Beep-Boop Docker Container Services Tester');
    console.log('Testing digi-infrastructure Docker containers...\n');
    
    const tester = new DockerServiceTester();
    const results = await tester.runAllTests();
    tester.printSummary();
    
    // Exit with appropriate code
    const failureCount = results.filter(r => r.status === 'failure').length;
    process.exit(failureCount > 0 ? 1 : 0);
}

if (require.main === module) {
    main().catch(console.error);
}
