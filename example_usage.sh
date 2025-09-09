#!/bin/bash

# Example usage script for OpenShift Pod Log Watcher

echo "OpenShift Pod Log Watcher - Example Usage"
echo "========================================"

# Check if namespace argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <openshift-namespace>"
    echo ""
    echo "Examples:"
    echo "  $0 my-project"
    echo "  $0 production-app"
    exit 1
fi

NAMESPACE=$1

# Set up environment
export POD_LOG_DIR="./pod_logs"

echo "Monitoring namespace: $NAMESPACE"
echo "Log directory: $POD_LOG_DIR"
echo ""

# Create log directory if it doesn't exist
mkdir -p "$POD_LOG_DIR"

# Check if we have kubectl/oc access
if ! command -v kubectl &> /dev/null && ! command -v oc &> /dev/null; then
    echo "Error: Neither kubectl nor oc command found. Please install OpenShift CLI tools."
    exit 1
fi

# Check if we can access the namespace
if command -v oc &> /dev/null; then
    if ! oc get pods -n "$NAMESPACE" &> /dev/null; then
        echo "Error: Cannot access namespace '$NAMESPACE'. Please check your login and permissions."
        exit 1
    fi
else
    if ! kubectl get pods -n "$NAMESPACE" &> /dev/null; then
        echo "Error: Cannot access namespace '$NAMESPACE'. Please check your kubeconfig and permissions."
        exit 1
    fi
fi

echo "✓ Access to namespace '$NAMESPACE' confirmed"
echo ""

# Install dependencies if needed
if ! python3 -c "import kubernetes" &> /dev/null; then
    echo "Installing required dependencies..."
    pip3 install -r requirements.txt
fi

echo "Starting pod log watcher..."
echo "Press Ctrl+C to stop"
echo ""

# Run the watcher
python3 pod_log_watcher.py "$NAMESPACE" --verbose
