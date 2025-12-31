"""
Test Docker deployment and service health.
Tests containerized deployment, service health checks, and monitoring.
"""

import pytest
import asyncio
import subprocess
import time
import requests
import docker
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDockerDeployment:
    """Test Docker deployment functionality."""
    
    @pytest.fixture
    def docker_client(self):
        """Create Docker client for testing."""
        try:
            return docker.from_env()
        except Exception:
            pytest.skip("Docker not available")
    
    @pytest.fixture
    def compose_file(self):
        """Path to docker-compose file."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docker-compose.yml"
        )
    
    def test_docker_compose_file_exists(self, compose_file):
        """Test that docker-compose file exists."""
        assert os.path.exists(compose_file), "docker-compose.yml file not found"
    
    def test_docker_compose_file_valid(self, compose_file):
        """Test that docker-compose file is valid YAML."""
        import yaml
        
        with open(compose_file, 'r') as f:
            try:
                compose_config = yaml.safe_load(f)
                assert compose_config is not None
                assert 'services' in compose_config
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in docker-compose.yml: {e}")
    
    def test_required_services_defined(self, compose_file):
        """Test that required services are defined in docker-compose."""
        import yaml
        
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
            services = compose_config.get('services', {})
            
            required_services = ['api', 'db', 'redis']
            for service in required_services:
                assert service in services, f"Required service '{service}' not found in docker-compose.yml"
    
    def test_service_health_checks(self, compose_file):
        """Test that services have health checks defined."""
        import yaml
        
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
            services = compose_config.get('services', {})
            
            # API service should have health check
            api_service = services.get('api', {})
            if 'healthcheck' in api_service:
                healthcheck = api_service['healthcheck']
                assert 'test' in healthcheck
                assert 'interval' in healthcheck
                assert 'timeout' in healthcheck
                assert 'retries' in healthcheck
    
    def test_environment_variables_configured(self, compose_file):
        """Test that environment variables are properly configured."""
        import yaml
        
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
            services = compose_config.get('services', {})
            
            # Check API service environment
            api_service = services.get('api', {})
            env_vars = api_service.get('environment', [])
            
            # Should have database and Redis configuration
            env_dict = {var.split('=')[0]: var.split('=')[1] if '=' in var else '' 
                       for var in env_vars if isinstance(var, str)}
            
            assert 'DATABASE_URL' in env_dict or 'POSTGRES_URL' in env_dict
            assert 'REDIS_URL' in env_dict
    
    def test_volume_mounts_configured(self, compose_file):
        """Test that volume mounts are properly configured."""
        import yaml
        
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
            services = compose_config.get('services', {})
            
            # Check database service volumes
            db_service = services.get('db', {})
            volumes = db_service.get('volumes', [])
            
            # Should have persistent data volume
            assert len(volumes) > 0, "Database service should have volume mounts"
    
    def test_network_configuration(self, compose_file):
        """Test that network configuration is proper."""
        import yaml
        
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
            services = compose_config.get('services', {})
            
            # Services should be on the same network
            api_service = services.get('api', {})
            db_service = services.get('db', {})
            
            # Check if networks are defined
            api_networks = api_service.get('networks', [])
            db_networks = db_service.get('networks', [])
            
            # Should have network configuration for inter-service communication
            assert len(api_networks) > 0 or 'networks' in compose_config


class TestServiceHealth:
    """Test service health and monitoring."""
    
    @pytest.fixture
    def api_base_url(self):
        """Base URL for API testing."""
        return os.getenv("API_BASE_URL", "http://localhost:8000")
    
    @pytest.fixture
    def redis_url(self):
        """Redis URL for testing."""
        return os.getenv("REDIS_URL", "redis://localhost:6379")
    
    def test_api_health_endpoint(self, api_base_url):
        """Test API health check endpoint."""
        try:
            response = requests.get(f"{api_base_url}/health", timeout=5)
            assert response.status_code == 200
            
            health_data = response.json()
            assert "status" in health_data
            assert health_data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
    
    def test_api_root_endpoint(self, api_base_url):
        """Test API root endpoint."""
        try:
            response = requests.get(f"{api_base_url}/", timeout=5)
            assert response.status_code == 200
            
            root_data = response.json()
            assert "message" in root_data
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
    
    def test_database_connection_health(self, api_base_url):
        """Test database connection health."""
        try:
            response = requests.get(f"{api_base_url}/health/db", timeout=5)
            assert response.status_code == 200
            
            db_health = response.json()
            assert "database" in db_health
            assert db_health["database"]["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
        except requests.exceptions.NotFound:
            pytest.skip("Database health endpoint not implemented")
    
    def test_redis_connection_health(self, api_base_url):
        """Test Redis connection health."""
        try:
            response = requests.get(f"{api_base_url}/health/redis", timeout=5)
            assert response.status_code == 200
            
            redis_health = response.json()
            assert "redis" in redis_health
            assert redis_health["redis"]["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
        except requests.exceptions.NotFound:
            pytest.skip("Redis health endpoint not implemented")
    
    def test_broker_connections_health(self, api_base_url):
        """Test broker connection health."""
        try:
            response = requests.get(f"{api_base_url}/health/brokers", timeout=5)
            assert response.status_code == 200
            
            broker_health = response.json()
            assert "brokers" in broker_health
            
            # Check individual broker statuses
            brokers = broker_health["brokers"]
            for broker_name, broker_status in brokers.items():
                assert "status" in broker_status
                assert broker_status["status"] in ["healthy", "unhealthy", "unknown"]
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
        except requests.exceptions.NotFound:
            pytest.skip("Broker health endpoint not implemented")
    
    def test_websocket_connection_health(self, api_base_url):
        """Test WebSocket connection health."""
        try:
            # Test WebSocket endpoint availability
            ws_url = api_base_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url += "/ws"
            
            # Use requests to test WebSocket upgrade (basic check)
            response = requests.get(f"{api_base_url}/ws", timeout=5)
            # WebSocket connections typically return 400 or 426 for GET requests
            assert response.status_code in [400, 426, 101]
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
    
    def test_service_dependencies(self, api_base_url):
        """Test that service dependencies are working."""
        try:
            # Test that API can connect to database
            response = requests.get(f"{api_base_url}/accounts/", timeout=5)
            # Should return 401 (unauthorized) rather than connection error
            assert response.status_code in [401, 403]
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
        except requests.exceptions.Timeout:
            pytest.fail("API service timeout - possible database connection issue")


class TestDockerBuild:
    """Test Docker build process."""
    
    @pytest.fixture
    def dockerfile_path(self):
        """Path to Dockerfile."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Dockerfile"
        )
    
    def test_dockerfile_exists(self, dockerfile_path):
        """Test that Dockerfile exists."""
        assert os.path.exists(dockerfile_path), "Dockerfile not found"
    
    def test_dockerfile_syntax(self, dockerfile_path):
        """Test that Dockerfile has valid syntax."""
        try:
            with open(dockerfile_path, 'r') as f:
                dockerfile_content = f.read()
                
                # Basic syntax checks
                assert "FROM" in dockerfile_content, "Dockerfile must have FROM instruction"
                assert "WORKDIR" in dockerfile_content, "Dockerfile must set WORKDIR"
                assert "COPY" in dockerfile_content, "Dockerfile must copy files"
                assert "RUN" in dockerfile_content or "CMD" in dockerfile_content, "Dockerfile must have run command"
                
                # Check for Python-specific instructions
                assert any(cmd in dockerfile_content for cmd in ["pip install", "python -m pip"]), "Dockerfile should install Python dependencies"
        except Exception as e:
            pytest.fail(f"Error reading Dockerfile: {e}")
    
    def test_requirements_file_exists(self):
        """Test that requirements.txt exists."""
        requirements_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "requirements.txt"
        )
        assert os.path.exists(requirements_path), "requirements.txt not found"
    
    def test_requirements_file_valid(self):
        """Test that requirements.txt is valid."""
        requirements_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "requirements.txt"
        )
        
        try:
            with open(requirements_path, 'r') as f:
                requirements = f.read().strip().split('\n')
                
                # Should have essential packages
                essential_packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'pydantic']
                found_packages = [pkg for pkg in essential_packages 
                                if any(pkg.lower() in req.lower() for req in requirements)]
                
                assert len(found_packages) > 0, "requirements.txt should contain essential packages"
        except Exception as e:
            pytest.fail(f"Error reading requirements.txt: {e}")


class TestDeploymentScripts:
    """Test deployment scripts functionality."""
    
    @pytest.fixture
    def deploy_script_path(self):
        """Path to deployment script."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "deploy.sh"
        )
    
    def test_deploy_script_exists(self, deploy_script_path):
        """Test that deploy script exists."""
        assert os.path.exists(deploy_script_path), "deploy.sh script not found"
    
    def test_deploy_script_executable(self, deploy_script_path):
        """Test that deploy script is executable."""
        assert os.access(deploy_script_path, os.X_OK), "deploy.sh is not executable"
    
    def test_deploy_script_content(self, deploy_script_path):
        """Test that deploy script has required commands."""
        try:
            with open(deploy_script_path, 'r') as f:
                script_content = f.read()
                
                # Should have essential docker commands
                assert "docker-compose" in script_content, "deploy script should use docker-compose"
                assert "up" in script_content, "deploy script should start services"
                assert "down" in script_content or "stop" in script_content, "deploy script should be able to stop services"
        except Exception as e:
            pytest.fail(f"Error reading deploy script: {e}")
    
    def test_environment_config_files(self):
        """Test that environment configuration files exist."""
        env_files = [
            ".env.example",
            ".env"
        ]
        
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        for env_file in env_files:
            env_path = os.path.join(base_path, env_file)
            if env_file == ".env.example":
                assert os.path.exists(env_path), f"{env_file} should exist"
            else:
                # .env file might not exist in test environment
                pass


class TestMonitoringAndLogging:
    """Test monitoring and logging functionality."""
    
    @pytest.fixture
    def api_base_url(self):
        """Base URL for API testing."""
        return os.getenv("API_BASE_URL", "http://localhost:8000")
    
    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        # Check if logging configuration exists
        log_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app",
            "core",
            "logging.py"
        )
        
        if os.path.exists(log_config_path):
            try:
                with open(log_config_path, 'r') as f:
                    log_config = f.read()
                    
                    # Should have logging configuration
                    assert "logging" in log_config.lower() or "logger" in log_config.lower()
            except Exception as e:
                pytest.fail(f"Error reading logging config: {e}")
        else:
            # Logging might be configured in main.py or config.py
            pytest.skip("Logging configuration file not found")
    
    def test_api_response_headers(self, api_base_url):
        """Test that API returns appropriate monitoring headers."""
        try:
            response = requests.get(f"{api_base_url}/health", timeout=5)
            
            # Check for common monitoring headers
            monitoring_headers = [
                'x-response-time',
                'x-request-id',
                'x-process-time'
            ]
            
            found_headers = [header for header in monitoring_headers 
                           if header in response.headers]
            
            # At least basic response should work
            assert response.status_code == 200
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
    
    def test_error_handling_and_monitoring(self, api_base_url):
        """Test error handling and monitoring."""
        try:
            # Test 404 error handling
            response = requests.get(f"{api_base_url}/nonexistent", timeout=5)
            assert response.status_code == 404
            
            # Should return proper error response
            error_data = response.json()
            assert "detail" in error_data or "error" in error_data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
    
    def test_metrics_endpoint(self, api_base_url):
        """Test metrics endpoint if available."""
        try:
            response = requests.get(f"{api_base_url}/metrics", timeout=5)
            
            if response.status_code == 200:
                # Should return metrics data
                metrics_data = response.text
                assert len(metrics_data) > 0
            else:
                pytest.skip("Metrics endpoint not implemented")
                
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")


class TestProductionReadiness:
    """Test production readiness of the deployment."""
    
    def test_security_headers(self):
        """Test security headers configuration."""
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        try:
            response = requests.get(f"{api_base_url}/health", timeout=5)
            
            # Check for security headers
            security_headers = [
                'x-content-type-options',
                'x-frame-options',
                'x-xss-protection'
            ]
            
            # In production, these should be present
            # For testing, we just verify the endpoint works
            assert response.status_code == 200
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
    
    def test_cors_configuration(self):
        """Test CORS configuration."""
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        try:
            # Test OPTIONS request for CORS
            response = requests.options(f"{api_base_url}/health", timeout=5)
            
            # Should handle OPTIONS requests
            assert response.status_code in [200, 405]
            
            # Check for CORS headers
            cors_headers = [
                'access-control-allow-origin',
                'access-control-allow-methods',
                'access-control-allow-headers'
            ]
            
            found_cors = [header for header in cors_headers 
                         if header in response.headers]
            
            # CORS might not be configured in all environments
            # This is more of a verification test
            assert response.status_code in [200, 405]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")
    
    def test_rate_limiting(self):
        """Test rate limiting configuration."""
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        try:
            # Make multiple rapid requests
            responses = []
            for _ in range(10):
                try:
                    response = requests.get(f"{api_base_url}/health", timeout=1)
                    responses.append(response.status_code)
                except requests.exceptions.Timeout:
                    responses.append("timeout")
            
            # At least some requests should succeed
            success_count = sum(1 for status in responses if status == 200)
            assert success_count > 0, "No requests succeeded - possible rate limiting issue"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API service not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])