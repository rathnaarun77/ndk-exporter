import time
import datetime
from kubernetes import client, config
from prometheus_client import start_http_server, Gauge

# Load in-cluster config
config.load_incluster_config()
api = client.CustomObjectsApi()

# Define metrics
application_info = Gauge(
    'ndk_application_info',
    'Information about NDK Applications',
    ['app_name', 'namespace']
)

application_snapshot_info = Gauge(
    'ndk_application_snapshot_info',
    'Information about NDK Application Snapshots',
    ['snapshot_name', 'namespace', 'application', 'ready_to_use']
)

application_snapshot_creation_timestamp = Gauge(
    'ndk_application_snapshot_creation_timestamp_seconds',
    'Creation time of ApplicationSnapshot as Unix timestamp',
    ['snapshot_name', 'namespace']
)

application_snapshot_expiration_timestamp = Gauge(
    'ndk_application_snapshot_expiration_timestamp_seconds',
    'Expiration time of ApplicationSnapshot as Unix timestamp',
    ['snapshot_name', 'namespace']
)


application_restore_info = Gauge(
    'ndk_application_restore_info',
    'Information about NDK Application Restores',
    ['restore_name', 'namespace', 'snapshot_name', 'completed', 'start_time', 'end_time']
)

application_restore_start_timestamp = Gauge(
    'ndk_application_restore_start_timestamp_seconds',
    'Start time of ApplicationRestore as Unix timestamp',
    ['restore_name', 'namespace']
)

application_restore_end_timestamp = Gauge(
    'ndk_application_restore_end_timestamp_seconds',
    'End time of ApplicationRestore as Unix timestamp',
    ['restore_name', 'namespace']
)

remote_info = Gauge(
    'ndk_remote_info', 
    'Status of remote resources', 
    ['remote_name', 'clusterName', 'ndkServiceIp', 'status'])

replicationtarget_info = Gauge(
    'ndk_replicationtarget_info', 
    'Information about the replication target resources', 
    labelnames=['replicationtarget_name', 'source_namespace', 'remote_namespace', 'remotename', 'status']
)

application_snapshot_replication_info = Gauge(
    'ndk_applicationsnapshotreplication_info',
    'Information about ApplicationSnapshotReplication resources',
    labelnames=['application_snapshot_replication_name', 'namespace', 'applicationsnapshotname', 'replicationtargetname', 'available_status']
)

jobscheduler_info = Gauge(
    'ndk_jobscheduler_info',
    'Information about JobScheduler CRs with schedule type and value',
    labelnames=['jobscheduler_name', 'namespace', 'schedule_type', 'schedule_value', 'timezone']
)

# One gauge for basic plan info
protectionplan_info = Gauge(
    'ndk_protectionplan_info',
    'Protection plan info including retention count',
    ['protectionplan_name', 'namespace', 'retention_count']
)

# Two condition status gauges
protectionplan_available_status = Gauge(
    'ndk_protectionplan_status_available',
    'Availability condition of the ProtectionPlan (1 for True, 0 for False)',
    ['protectionplan_name', 'namespace']
)

protectionplan_degraded_status = Gauge(
    'ndk_protectionplan_status_degraded',
    'Degraded condition of the ProtectionPlan (1 for True, 0 for False)',
    ['protectionplan_name', 'namespace']
)

# Metric to expose app protection plan info
appprotection_plan_info = Gauge(
    'ndk_appprotection_plan_info',
    'Information about AppProtectionPlans',
    ['appprotectionplan_name', 'namespace', 'protectionplans']
)

# Conditions
appprotection_plan_available_status = Gauge(
    'ndk_appprotection_plan_status_available',
    'Availability condition of the AppProtectionPlan (1 for True, 0 for False)',
    ['appprotectionplan_name', 'namespace']
)

appprotection_plan_degraded_status = Gauge(
    'ndk_appprotection_plan_status_degraded',
    'Degraded condition of the AppProtectionPlan (1 for True, 0 for False)',
    ['appprotectionplan_name', 'namespace']
)

def to_unix_timestamp(timestr):
    try:
        dt = datetime.datetime.fromisoformat(timestr.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0

def application_collect():
    group = 'dataservices.nutanix.com'
    version = 'v1alpha1'
    plural = 'applications'

    try:
        resp = api.list_cluster_custom_object(group, version, plural)
        application_info.clear() 

        for item in resp.get('items', []):
            metadata = item.get('metadata', {})
            app_name = metadata.get('name', 'unknown')
            namespace = metadata.get('namespace', 'default')

            # Set the application_info metric
            application_info.labels(app_name=app_name, namespace=namespace).set(1)

            print(f"Retrieved application: {app_name}, Namespace: {namespace}")

    except Exception as e:
        print(f"Error collecting application data: {e}")

def application_snapshot_collect():
    try:
        snapshots = api.list_cluster_custom_object(
            group='dataservices.nutanix.com',
            version='v1alpha1',
            plural='applicationsnapshots'
        )

        # Clear all metrics
        application_snapshot_info.clear()
        application_snapshot_creation_timestamp.clear()
        application_snapshot_expiration_timestamp.clear()

        for item in snapshots.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            status = item.get('status', {})

            snapshotname = metadata.get('name')
            namespace = metadata.get('namespace')
            application_name = spec.get('source', {}).get('applicationRef', {}).get('name', 'unknown')
            ready_to_use = str(status.get('readyToUse', False)).lower()

            creation_raw = status.get('creationTime')
            expiration_raw = status.get('expirationTime')

            creation_ts = to_unix_timestamp(creation_raw) if creation_raw else 0
            expiration_ts = to_unix_timestamp(expiration_raw) if expiration_raw else 0

            # Set metrics
            application_snapshot_info.labels(
                snapshot_name=snapshotname,
                namespace=namespace,
                application=application_name,
                ready_to_use=ready_to_use
            ).set(1)

            application_snapshot_creation_timestamp.labels(
                snapshot_name=snapshotname,
                namespace=namespace
            ).set(creation_ts)

            application_snapshot_expiration_timestamp.labels(
                snapshot_name=snapshotname,
                namespace=namespace
            ).set(expiration_ts)

    except Exception as e:
        print(f"Error collecting snapshot data: {e}")


def application_restore_collect():
    try:
        # Fetch ApplicationSnapshotRestore resources
        restores = api.list_cluster_custom_object(
            group='dataservices.nutanix.com',
            version='v1alpha1',
            plural='applicationsnapshotrestores'  # Correct plural name for the resource
        )

        # Clear any previous metrics
        application_restore_info.clear()
        application_restore_start_timestamp.clear()
        application_restore_end_timestamp.clear()

        # Process each restore resource
        for item in restores.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            status = item.get('status', {})

            # Extract relevant fields
            restore_name = metadata.get('name')  # Restore name
            namespace = metadata.get('namespace')  # Namespace
            snapshot_name = spec.get('applicationSnapshotName', 'unknown')  # Snapshot name from spec
            completed = str(status.get('completed', False)).lower()  # Whether the restore is completed

            # Extract start and finish times from status
            start_raw = status.get('startTime')
            finish_raw = status.get('finishTime')

            # Convert start and finish times to Unix timestamps
            start_ts = to_unix_timestamp(start_raw) if start_raw else 0
            finish_ts = to_unix_timestamp(finish_raw) if finish_raw else 0


            # Set the application_restore_info metric
            application_restore_info.labels(
                restore_name=restore_name,
                namespace=namespace,
                snapshot_name=snapshot_name,
                completed=completed,
                start_time=str(start_ts),
                end_time=str(finish_ts)
            ).set(1)

            # Set the start and end time timestamps
            application_restore_start_timestamp.labels(
                restore_name=restore_name,
                namespace=namespace
            ).set(start_ts)

            application_restore_end_timestamp.labels(
                restore_name=restore_name,
                namespace=namespace
            ).set(finish_ts)

    except Exception as e:
        print(f"Error collecting restore data: {e}")

def remote_collect():
    group = 'dataservices.nutanix.com'
    version = 'v1alpha1'
    plural = 'remotes'

    try:
        # Retrieve the list of Remote resources
        resp = api.list_cluster_custom_object(group, version, plural)
        
        # Clear previous data
        remote_info.clear()

        # Iterate through the items in the response (which is a list of Remote objects)
        for item in resp.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            status_conditions = item.get('status', {}).get('conditions', [])

            name = metadata.get('name', 'unknown')
            cluster_name = spec.get('clusterName', 'unknown')
            ndk_service_ip = spec.get('ndkServiceIp', 'unknown')

            # Extract the status from the first condition (if available)
            status = 'unknown'
            if status_conditions:
                status_condition = status_conditions[0]  # Get the first condition
                status = status_condition.get('status', 'unknown')  # Extract the status

            # Set the metric for the remote resource
            remote_info.labels(remote_name= name, clusterName=cluster_name, ndkServiceIp=ndk_service_ip, status=status).set(1)
    
    except Exception as e:
        print(f"Error collecting remote data: {e}")


def replicationtarget_collect():
    group = 'dataservices.nutanix.com'
    version = 'v1alpha1'
    plural = 'replicationtargets'

    try:
        # Retrieve the list of ReplicationTarget resources
        resp = api.list_cluster_custom_object(group, version, plural)
        
        # Clear previous data
        replicationtarget_info.clear()

        # Iterate through the items in the response (which is a list of ReplicationTarget objects)
        for item in resp.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            status_conditions = item.get('status', {}).get('conditions', [])

            reptarget_name = metadata.get('name', 'unknown')
            reptarget_namespace = metadata.get('namespace', 'unknown')
            namespace_name = spec.get('namespaceName', 'unknown')
            remote_name = spec.get('remoteName', 'unknown')

            # Extract the status from the first condition (if available)
            status = 'unknown'
            if status_conditions:
                status_condition = status_conditions[0]  # Get the first condition
                status = status_condition.get('status', 'unknown')  # Extract the status

            # Set the metric for the replication target resource
            replicationtarget_info.labels(replicationtarget_name=reptarget_name, source_namespace=reptarget_namespace, remote_namespace=namespace_name, remotename=remote_name, status=status).set(1)
    
    except Exception as e:
        print(f"Error collecting replication target data: {e}")

def application_snapshot_replication_collect():
    group = 'dataservices.nutanix.com'
    version = 'v1alpha1'
    plural = 'applicationsnapshotreplications'

    try:
        # Retrieve the list of ApplicationSnapshotReplication resources
        resp = api.list_cluster_custom_object(group, version, plural)

        # Clear old metric values
        application_snapshot_replication_info.clear()

        for item in resp.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            conditions = item.get('status', {}).get('conditions', [])

            name = metadata.get('name', 'unknown')
            namespace = metadata.get('namespace', 'unknown')
            app_snap_name = spec.get('applicationSnapshotName', 'unknown')
            replication_target_name = spec.get('replicationTargetName', 'unknown')

            # Look for condition of type "Available"
            available_status = 'unknown'
            for condition in conditions:
                if condition.get('type') == 'Available':
                    available_status = condition.get('status', 'unknown')
                    break

            # Set the metric
            application_snapshot_replication_info.labels(
                application_snapshot_replication_name=name,
                namespace=namespace,
                applicationsnapshotname=app_snap_name,
                replicationtargetname=replication_target_name,
                available_status=available_status
            ).set(1)

    except Exception as e:
        print(f"Error in application_snapshot_replication_collect: {e}")

def jobscheduler_collect():
    group = 'scheduler.nutanix.com'
    version = 'v1alpha1'
    plural = 'jobschedulers'

    try:
        # Fetch all JobScheduler CRs
        resp = api.list_cluster_custom_object(group, version, plural)

        # Clear existing metrics
        jobscheduler_info.clear()

        for item in resp.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})

            name = metadata.get('name', 'unknown')
            namespace = metadata.get('namespace', 'default')
            timezone = spec.get('timeZoneName', 'unknown')

            # Determine schedule type and value
            schedule_type = 'unknown'
            schedule_value = 'unknown'

            if 'interval' in spec:
                schedule_type = 'interval'
                schedule_value = f"{spec['interval'].get('minutes', 'unknown')}m"
            elif 'daily' in spec:
                schedule_type = 'daily'
                schedule_value = spec['daily'].get('time', 'unknown')
            elif 'weekly' in spec:
                schedule_type = 'weekly'
                days = spec['weekly'].get('days', 'unknown')
                time = spec['weekly'].get('time', 'unknown')
                schedule_value = f"{days} at {time}"
            elif 'monthly' in spec:
                schedule_type = 'monthly'
                dates = spec['monthly'].get('dates', 'unknown')
                time = spec['monthly'].get('time', 'unknown')
                schedule_value = f"{dates} at {time}"
            elif 'cronSchedule' in spec:
                schedule_type = 'cron'
                schedule_value = spec.get('cronSchedule', 'unknown')
            elif 'startTime' in spec:
                schedule_type = 'one-time'
                schedule_value = spec.get('startTime', 'unknown')

            # Set the metric with namespace
            jobscheduler_info.labels(
                jobscheduler_name=name,
                namespace=namespace,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                timezone=timezone
            ).set(1)

    except Exception as e:
        print(f"Error in jobscheduler_collect: {e}")


def protectionplan_collect():
    group = 'dataservices.nutanix.com'
    version = 'v1alpha1'
    plural = 'protectionplans'

    try:
        # Fetch all ProtectionPlan CRs
        resp = api.list_cluster_custom_object(group, version, plural)

        # Clear existing metrics
        protectionplan_info.clear()
        protectionplan_available_status.clear()
        protectionplan_degraded_status.clear()

        for item in resp.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            status = item.get('status', {})

            name = metadata.get('name', 'unknown')
            namespace = metadata.get('namespace', 'default')
            retention_count = str(spec.get('retentionPolicy', {}).get('retentionCount', '0'))

            # Set base info metric
            protectionplan_info.labels(
                protectionplan_name=name,
                namespace=namespace,
                retention_count=retention_count
            ).set(1)

            # Parse conditions
            conditions = status.get('conditions', [])
            available = 0
            degraded = 0

            for condition in conditions:
                cond_type = condition.get('type', '')
                cond_status = condition.get('status', '').lower()

                if cond_type == 'Available':
                    available = 1 if cond_status == 'true' else 0
                elif cond_type == 'Degraded':
                    degraded = 1 if cond_status == 'true' else 0

            # Set condition metrics
            protectionplan_available_status.labels(
                protectionplan_name=name,
                namespace=namespace
            ).set(available)

            protectionplan_degraded_status.labels(
                protectionplan_name=name,
                namespace=namespace
            ).set(degraded)

    except Exception as e:
        print(f"Error in protectionplan_collect: {e}")

def app_protectionplan_collect():
    group = 'dataservices.nutanix.com'
    version = 'v1alpha1'
    plural = 'appprotectionplans'

    try:
        # Fetch all AppProtectionPlan CRs
        resp = api.list_cluster_custom_object(group, version, plural)

        # Clear existing metrics
        appprotection_plan_info.clear()
        appprotection_plan_available_status.clear()
        appprotection_plan_degraded_status.clear()

        for item in resp.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            status = item.get('status', {})

            name = metadata.get('name', 'unknown')
            namespace = metadata.get('namespace', 'default')
            protectionplans = spec.get('protectionPlanNames', [])
            protectionplans_str = ",".join(protectionplans) if protectionplans else "none"

            # Set base info metric
            appprotection_plan_info.labels(
                appprotectionplan_name=name,
                namespace=namespace,
                protectionplans=protectionplans_str
            ).set(1)

            # Conditions
            conditions = status.get('conditions', [])
            available = 0
            degraded = 0

            for condition in conditions:
                cond_type = condition.get('type', '')
                cond_status = condition.get('status', '').lower()

                if cond_type == 'Available':
                    available = 1 if cond_status == 'true' else 0
                elif cond_type == 'Degraded':
                    degraded = 1 if cond_status == 'true' else 0

            # Set condition metrics
            appprotection_plan_available_status.labels(
                appprotectionplan_name=name,
                namespace=namespace
            ).set(available)

            appprotection_plan_degraded_status.labels(
                appprotectionplan_name=name,
                namespace=namespace
            ).set(degraded)

    except Exception as e:
        print(f"Error in appprotectionplan_collect: {e}")


if __name__ == '__main__':
    start_http_server(8000)
    while True:
        application_collect()
        application_snapshot_collect()
        application_restore_collect()
        remote_collect()
        replicationtarget_collect()
        application_snapshot_replication_collect()
        jobscheduler_collect()
        protectionplan_collect()
        app_protectionplan_collect()
        time.sleep(30)