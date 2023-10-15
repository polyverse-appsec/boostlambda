import boto3
import os
from botocore.exceptions import ClientError

file_contents_cache = {}
s3_storage_bucket_name = "polyverse-boost"

LOCAL_BASE_FOLDER = 'chalicelib'

SEARCH_STAGES = ['dev', 'test', 'staging', 'prod', 'local']


def get_file(filename) -> str:
    CHALICE_STAGE = os.environ.get("CHALICE_STAGE", "local")

    # first read the file cache
    cached_file_contents = file_contents_cache.get(filename)
    if cached_file_contents is not None:
        return cached_file_contents

    # Find where to start searching based on the CHALICE_STAGE
    start_index = SEARCH_STAGES.index(CHALICE_STAGE)

    # Search in stages starting from the CHALICE_STAGE and beyond
    for stage in SEARCH_STAGES[start_index:]:
        if stage == "local":
            with open(os.path.join(LOCAL_BASE_FOLDER, filename), 'r') as f:
                file_content = f.read()
                break
        elif file_exists_in_s3(s3_storage_bucket_name, os.path.join(stage, filename)):
            s3 = boto3.client('s3')
            s3_object = s3.get_object(Bucket=s3_storage_bucket_name, Key=os.path.join(stage, filename))
            file_content = s3_object['Body'].read().decode('utf-8')
            break
    else:
        raise FileNotFoundError(f"File {filename} not found in any of the specified stages or locally.")

    # Cache the file contents globally for all services to use it, saving further S3 or filesystem calls
    file_contents_cache[filename] = file_content
    return file_content


def file_exists_in_s3(bucket_name, key_name):
    s3 = boto3.client('s3')

    try:
        # This only retrieves metadata and doesn't download the object
        s3.head_object(Bucket=bucket_name, Key=key_name)
        return True
    except ClientError as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the object does not exist.
        if e.response['Error']['Code'] == '404':
            return False
        else:
            # If it was a different error, then raise the error
            raise
