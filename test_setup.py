#!/usr/bin/env python3
"""
Test script to validate the OpenShift Pod Log Watcher setup.

This script checks:
1. Python dependencies are installed
2. Kubernetes configuration is accessible
3. Basic API connectivity works
"""

import sys
import os
from pathlib import Path

def test_dependencies():
    """Test if required dependencies are installed."""
    print("Testing dependencies...")
    
    try:
        import kubernetes
        print("✓ kubernetes library is installed")
        return True
    except ImportError:
        print("✗ kubernetes library not found")
        print("  Install with: pip install -r requirements.txt")
        return False

def test_kubernetes_config():
    """Test if Kubernetes configuration is accessible."""
    print("\nTesting Kubernetes configuration...")
    
    try:
        from kubernetes import config
        
        # Try to load configuration
        try:
            config.load_incluster_config()
            print("✓ In-cluster configuration loaded")
            return True
        except config.ConfigException:
            try:
                config.load_kube_config()
                print("✓ Kubeconfig loaded from default location")
                return True
            except config.ConfigException as e:
                print(f"✗ Failed to load Kubernetes configuration: {e}")
                print("  Make sure you have a valid kubeconfig file or are running in a cluster")
                return False
    except Exception as e:
        print(f"✗ Error testing Kubernetes configuration: {e}")
        return False

def test_api_connectivity():
    """Test basic API connectivity."""
    print("\nTesting API connectivity...")
    
    try:
        from kubernetes import client, config
        
        # Load config (already tested above, but needed here)
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        # Create API client
        v1 = client.CoreV1Api()
        
        # Try to list namespaces (basic API call)
        namespaces = v1.list_namespace(limit=1)
        print("✓ API connectivity successful")
        print(f"  Found {len(namespaces.items)} namespace(s)")
        return True
        
    except Exception as e:
        print(f"✗ API connectivity failed: {e}")
        print("  Check your cluster connection and permissions")
        return False

def test_namespace_access(namespace):
    """Test access to a specific namespace."""
    print(f"\nTesting access to namespace '{namespace}'...")
    
    try:
        from kubernetes import client, config
        
        # Load config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        v1 = client.CoreV1Api()
        
        # Try to list pods in the namespace
        pods = v1.list_namespaced_pod(namespace=namespace, limit=1)
        print(f"✓ Access to namespace '{namespace}' successful")
        print(f"  Found {len(pods.items)} pod(s)")
        return True
        
    except Exception as e:
        print(f"✗ Cannot access namespace '{namespace}': {e}")
        print("  Check if the namespace exists and you have the required permissions")
        return False

def main():
    """Main test function."""
    print("OpenShift Pod Log Watcher - Setup Test")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test dependencies
    if not test_dependencies():
        all_tests_passed = False
    
    # Test Kubernetes config
    if not test_kubernetes_config():
        all_tests_passed = False
        # Skip remaining tests if config fails
        print("\n" + "=" * 50)
        print("Setup test completed with errors")
        print("Please fix the configuration issues above before using the pod watcher")
        sys.exit(1)
    
    # Test API connectivity
    if not test_api_connectivity():
        all_tests_passed = False
    
    # Test namespace access if provided
    if len(sys.argv) > 1:
        namespace = sys.argv[1]
        if not test_namespace_access(namespace):
            all_tests_passed = False
    else:
        print("\nSkipping namespace test (no namespace provided)")
        print("  Run with: python test_setup.py <namespace> to test specific namespace access")
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("✓ All tests passed! The pod watcher should work correctly.")
        if len(sys.argv) > 1:
            print(f"\nYou can now run the watcher with:")
            print(f"  python pod_log_watcher.py {sys.argv[1]}")
    else:
        print("✗ Some tests failed. Please fix the issues above before using the pod watcher.")
        sys.exit(1)

if __name__ == '__main__':
    main()
