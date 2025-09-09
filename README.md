# OpenShift Pod Log Watcher

A Python script that monitors an OpenShift project for pod failures and automatically saves their logs to local files.

## Features

- **Real-time monitoring**: Watches for pod events in real-time using Kubernetes API
- **Comprehensive failure detection**: Detects various pod failure scenarios including crashes, evictions, and container errors
- **Automatic log extraction**: Saves logs from all containers in failed pods
- **Timestamped files**: Creates uniquely named log files with timestamps
- **Robust error handling**: Handles API errors and network issues gracefully
- **Configurable**: Supports environment variables and command-line arguments
- **Multi-container support**: Extracts logs from all containers in a pod

## Prerequisites

1. **Python 3.7+**
2. **Access to OpenShift cluster**: Valid kubeconfig file or in-cluster configuration
3. **Permissions**: Read access to pods and logs in the target namespace

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Monitor a specific OpenShift project:

```bash
python pod_log_watcher.py my-project-name
```

### Advanced Usage

```bash
# Specify custom log directory
python pod_log_watcher.py my-project --log-dir /path/to/logs

# Use specific kubeconfig file
python pod_log_watcher.py my-project --kubeconfig /path/to/kubeconfig

# Enable verbose logging
python pod_log_watcher.py my-project --verbose
```

### Environment Variables

You can also configure the script using environment variables:

```bash
export POD_LOG_DIR=/path/to/logs
export KUBECONFIG=/path/to/kubeconfig
python pod_log_watcher.py my-project
```

## Configuration

### Command Line Arguments

- `namespace`: OpenShift project/namespace to monitor (required)
- `--log-dir`: Directory to save pod logs (default: `./pod_logs`)
- `--kubeconfig`: Path to kubeconfig file (optional)
- `--verbose`: Enable verbose logging

### Authentication

The script uses the standard Kubernetes authentication methods:

1. **In-cluster config**: If running inside a pod with a service account
2. **Kubeconfig file**: From `~/.kube/config` or specified path
3. **Environment variables**: `KUBECONFIG` environment variable

## Output

### Log Files

Failed pod logs are saved to files with the following naming convention:
```
{pod_name}_{timestamp}.log
```

Each log file contains:
- Pod metadata (name, namespace, failure reason, timestamp)
- Logs from all containers in the pod
- Clear separation between different containers

### Example Log File Structure

```
Pod: my-app-pod-12345
Namespace: my-project
Failure Reason: Container terminated: Error (exit code: 1)
Timestamp: 2024-01-15T10:30:45.123456
================================================================================

Container: my-app
----------------------------------------
2024-01-15 10:30:40 INFO Starting application...
2024-01-15 10:30:42 ERROR Database connection failed
2024-01-15 10:30:43 FATAL Application shutting down


Container: sidecar
----------------------------------------
2024-01-15 10:30:40 INFO Sidecar starting...
2024-01-15 10:30:45 WARN Main container stopped
```

## Pod Failure Detection

The script detects various types of pod failures:

- **Pod phase failures**: `Failed` or `Succeeded` phases
- **Container crashes**: Non-zero exit codes
- **Container errors**: `CrashLoopBackOff`, `ImagePullBackOff`, etc.
- **Pod deletions**: When pods are manually or automatically deleted
- **Resource evictions**: When pods are evicted due to resource constraints

## Logging

The script maintains its own log file (`watcher.log`) in the log directory, containing:
- Startup and configuration information
- Pod failure events and reasons
- Error messages and warnings
- Processing statistics

## Troubleshooting

### Common Issues

1. **Authentication errors**: Ensure your kubeconfig is valid and you have access to the namespace
2. **Permission denied**: Verify you have read access to pods and logs in the target namespace
3. **Network timeouts**: The script will retry and continue watching after temporary network issues

### Debug Mode

Enable verbose logging to see detailed information:
```bash
python pod_log_watcher.py my-project --verbose
```

## Security Considerations

- The script only requires read access to pods and logs
- Log files may contain sensitive information - secure the log directory appropriately
- Consider using a dedicated service account with minimal required permissions

## Examples

### Running in OpenShift

Create a deployment that runs the watcher:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pod-log-watcher
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pod-log-watcher
  template:
    metadata:
      labels:
        app: pod-log-watcher
    spec:
      serviceAccountName: pod-log-watcher
      containers:
      - name: watcher
        image: python:3.9
        command: ["python", "/app/pod_log_watcher.py", "my-project"]
        volumeMounts:
        - name: logs
          mountPath: /app/pod_logs
        - name: script
          mountPath: /app
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: log-storage
      - name: script
        configMap:
          name: watcher-script
```

### Local Development

For local development and testing:

```bash
# Set up environment
export KUBECONFIG=~/.kube/config
export POD_LOG_DIR=./logs

# Run watcher
python pod_log_watcher.py my-development-project --verbose
```

## License

This project is provided as-is for educational and operational purposes.
