#!/usr/bin/env python3
"""
OpenShift Pod Log Watcher

This script monitors an OpenShift project for pod failures and automatically
saves the logs of terminated pods to local files.

Features:
- Watches for pod events in real-time
- Detects various pod failure scenarios (crashes, evictions, etc.)
- Saves logs with timestamps and pod information
- Configurable via environment variables or command line arguments
- Robust error handling and logging
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Suppress InsecureRequestWarning from urllib3
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from kubernetes import client, config, watch
    from kubernetes.client.rest import ApiException
except ImportError:
    print("Error: kubernetes library not found. Install it with: pip install kubernetes")
    sys.exit(1)


class PodLogWatcher:
    """Watches OpenShift pods and saves logs when they terminate."""
    
    def __init__(self, namespace: str, log_dir: str = "./pod_logs", 
                 kubeconfig_path: Optional[str] = None):
        """
        Initialize the pod log watcher.
        
        Args:
            namespace: OpenShift project/namespace to monitor
            log_dir: Directory to save pod logs
            kubeconfig_path: Path to kubeconfig file (optional)
        """
        self.namespace = namespace
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self._setup_logging()
        
        # Load Kubernetes configuration
        self._load_kube_config(kubeconfig_path)
        
        # Initialize Kubernetes API client
        self.v1 = client.CoreV1Api()
        
        # Track pods we've already processed to avoid duplicates
        self.processed_pods = set()
        
        self.logger.info(f"Initialized PodLogWatcher for namespace: {namespace}")
        self.logger.info(f"Log directory: {self.log_dir.absolute()}")
    
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.log_dir / 'watcher.log')
            ]
        )
        self.logger = logging.getLogger('PodLogWatcher')
    
    def _load_kube_config(self, kubeconfig_path: Optional[str]):
        """Load Kubernetes configuration."""
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
                self.logger.info(f"Loaded kubeconfig from: {kubeconfig_path}")
            else:
                # Try to load from default locations
                try:
                    config.load_incluster_config()
                    self.logger.info("Loaded in-cluster configuration")
                except config.ConfigException:
                    config.load_kube_config()
                    self.logger.info("Loaded kubeconfig from default location")
        except Exception as e:
            self.logger.error(f"Failed to load Kubernetes configuration: {e}")
            raise
    
    def _is_pod_failed(self, pod: client.V1Pod) -> bool:
        """
        Check if a pod has failed or terminated unexpectedly.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            True if pod has failed, False otherwise
        """
        if not pod.status:
            return False
            
        phase = pod.status.phase
        
        # Check for obvious failure states
        if phase in ['Failed', 'Succeeded']:
            return True
            
        # Check container statuses for crashes, errors, etc.
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if container_status.state:
                    # Check for terminated containers with non-zero exit codes
                    if (container_status.state.terminated and 
                        container_status.state.terminated.exit_code != 0):
                        return True
                    
                    # Check for waiting containers with error reasons
                    if (container_status.state.waiting and 
                        container_status.state.waiting.reason in 
                        ['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull']):
                        return True
        
        # Check pod conditions for failures
        if pod.status.conditions:
            for condition in pod.status.conditions:
                if (condition.type == 'PodReadyCondition' and 
                    condition.status == 'False' and
                    condition.reason in ['ContainersNotReady', 'PodCompleted']):
                    return True
        
        return False
    
    def _get_failure_reason(self, pod: client.V1Pod) -> str:
        """
        Get a human-readable reason for pod failure.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            String describing the failure reason
        """
        if not pod.status:
            return "Unknown"
            
        phase = pod.status.phase
        
        if phase == 'Failed':
            return f"Pod phase: {phase}"
        
        if phase == 'Succeeded':
            return "Pod completed successfully"
            
        # Check container statuses
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if container_status.state:
                    if container_status.state.terminated:
                        term = container_status.state.terminated
                        return f"Container terminated: {term.reason} (exit code: {term.exit_code})"
                    
                    if container_status.state.waiting:
                        wait = container_status.state.waiting
                        return f"Container waiting: {wait.reason} - {wait.message}"
        
        return "Pod failure detected"
    
    def save_pod_logs(self, pod_name: str, failure_reason: str) -> bool:
        """
        Save logs from a failed pod to a local file.
        
        Args:
            pod_name: Name of the pod
            failure_reason: Reason for pod failure
            
        Returns:
            True if logs were saved successfully, False otherwise
        """
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_pod_name = pod_name.replace('/', '_').replace(':', '_')
            log_filename = f"{safe_pod_name}_{timestamp}.log"
            log_file_path = self.log_dir / log_filename
            
            # Try to get logs from all containers in the pod
            logs_saved = False
            
            try:
                # Get pod details to check for multiple containers
                pod_details = self.v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
                containers = [container.name for container in pod_details.spec.containers]
            except ApiException:
                # If we can't get pod details, try with default container
                containers = [None]
            
            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                # Write header information
                log_file.write(f"Pod: {pod_name}\n")
                log_file.write(f"Namespace: {self.namespace}\n")
                log_file.write(f"Failure Reason: {failure_reason}\n")
                log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
                log_file.write("=" * 80 + "\n\n")
                
                for container_name in containers:
                    try:
                        # Retrieve pod logs
                        if container_name:
                            logs = self.v1.read_namespaced_pod_log(
                                name=pod_name, 
                                namespace=self.namespace,
                                container=container_name,
                                previous=True  # Get logs from previous container instance if crashed
                            )
                            log_file.write(f"Container: {container_name}\n")
                            log_file.write("-" * 40 + "\n")
                        else:
                            logs = self.v1.read_namespaced_pod_log(
                                name=pod_name, 
                                namespace=self.namespace,
                                previous=True
                            )
                        
                        if logs:
                            log_file.write(logs)
                            log_file.write("\n\n")
                            logs_saved = True
                        else:
                            log_file.write("No logs available\n\n")
                            
                    except ApiException as e:
                        # Try without previous=True if that fails
                        try:
                            if container_name:
                                logs = self.v1.read_namespaced_pod_log(
                                    name=pod_name, 
                                    namespace=self.namespace,
                                    container=container_name
                                )
                            else:
                                logs = self.v1.read_namespaced_pod_log(
                                    name=pod_name, 
                                    namespace=self.namespace
                                )
                            
                            if logs:
                                log_file.write(logs)
                                log_file.write("\n\n")
                                logs_saved = True
                            else:
                                log_file.write("No logs available\n\n")
                                
                        except ApiException as e2:
                            error_msg = f"Error retrieving logs for container {container_name}: {e2}\n\n"
                            log_file.write(error_msg)
                            self.logger.warning(error_msg.strip())
            
            if logs_saved:
                self.logger.info(f"Logs for pod {pod_name} saved to {log_file_path}")
                return True
            else:
                self.logger.warning(f"No logs could be retrieved for pod {pod_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving logs for pod {pod_name}: {e}")
            return False
    
    def watch_pods(self):
        """
        Watch for pod events and save logs when pods fail.
        """
        self.logger.info(f"Starting to watch pods in namespace: {self.namespace}")
        
        w = watch.Watch()
        
        try:
            # First, check for any already failed pods
            self.logger.info("Checking for existing failed pods...")
            try:
                pods = self.v1.list_namespaced_pod(namespace=self.namespace)
                for pod in pods.items:
                    if self._is_pod_failed(pod) and pod.metadata.name not in self.processed_pods:
                        failure_reason = self._get_failure_reason(pod)
                        self.logger.info(f"Found existing failed pod: {pod.metadata.name} - {failure_reason}")
                        self.save_pod_logs(pod.metadata.name, failure_reason)
                        self.processed_pods.add(pod.metadata.name)
            except ApiException as e:
                self.logger.error(f"Error checking existing pods: {e}")
            
            # Now watch for new events
            self.logger.info("Watching for pod events...")
            for event in w.stream(self.v1.list_namespaced_pod, namespace=self.namespace):
                try:
                    pod = event['object']
                    pod_name = pod.metadata.name
                    event_type = event['type']
                    
                    self.logger.debug(f"Pod event: {event_type} - {pod_name}")
                    
                    # Handle different event types
                    if event_type == 'DELETED':
                        if pod_name not in self.processed_pods:
                            self.logger.info(f"Pod {pod_name} was deleted")
                            self.save_pod_logs(pod_name, "Pod deleted")
                            self.processed_pods.add(pod_name)
                    
                    elif event_type in ['ADDED', 'MODIFIED']:
                        if self._is_pod_failed(pod) and pod_name not in self.processed_pods:
                            failure_reason = self._get_failure_reason(pod)
                            self.logger.info(f"Pod {pod_name} failed: {failure_reason}")
                            self.save_pod_logs(pod_name, failure_reason)
                            self.processed_pods.add(pod_name)
                
                except Exception as e:
                    self.logger.error(f"Error processing pod event: {e}")
                    continue
                    
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping watcher...")
        except Exception as e:
            self.logger.error(f"Error watching pods: {e}")
            raise
        finally:
            w.stop()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Watch OpenShift pods and save logs when they fail"
    )
    parser.add_argument(
        'namespace',
        help='OpenShift project/namespace to monitor'
    )
    parser.add_argument(
        '--log-dir',
        default=os.environ.get('POD_LOG_DIR', './pod_logs'),
        help='Directory to save pod logs (default: ./pod_logs)'
    )
    parser.add_argument(
        '--kubeconfig',
        default=os.environ.get('KUBECONFIG'),
        help='Path to kubeconfig file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create and start the watcher
        watcher = PodLogWatcher(
            namespace=args.namespace,
            log_dir=args.log_dir,
            kubeconfig_path=args.kubeconfig
        )
        
        watcher.watch_pods()
        
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
