import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
import fnmatch
import glob


file_contents_cache = {}
s3_storage_bucket_name = "polyverse-boost"

LOCAL_BASE_FOLDER = 'chalicelib'

SEARCH_STAGES = ['dev', 'test', 'staging', 'prod', 'local']


def get_file(filename) -> str:
    CHALICE_STAGE = os.environ.get("CHALICE_STAGE", "local")

    # Find where to start searching based on the CHALICE_STAGE
    start_index = SEARCH_STAGES.index(CHALICE_STAGE)

    # Search in stages starting from the CHALICE_STAGE and beyond
    for stage in SEARCH_STAGES[start_index:]:
        if stage == "local":
            fullLocalPath = os.path.join(os.path.abspath(os.path.curdir), LOCAL_BASE_FOLDER, filename)

            timestamp = os.path.getmtime(fullLocalPath)

            # first read the file cache
            cached_file_contents = file_contents_cache.get(filename)
            if cached_file_contents is not None:
                if cached_file_contents['time'] != timestamp:
                    # if the file has changed, then we need to reload it
                    print(f"Local File {filename} has changed, reloading.")
                else:
                    # if the file hasn't changed, then we can just return the cached contents
                    print(f"Local File {filename} has not changed, returning cached contents.")
                    return cached_file_contents['contents']

            print(f"Looking Locally for file: {filename} in {fullLocalPath}")
            with open(fullLocalPath, 'r') as f:

                file_content = f.read()

                break
        elif file_exists_in_s3(s3_storage_bucket_name, os.path.join(stage, filename)):
            print(f"Retrieving S3 file: {filename} in {stage}")
            s3 = boto3.client('s3')

            s3_object = s3.get_object(Bucket=s3_storage_bucket_name, Key=os.path.join(stage, filename))

            timestamp = s3_object['LastModified'].timestamp()

            # first read the file cache
            cached_file_contents = file_contents_cache.get(filename)
            if cached_file_contents is not None:
                if cached_file_contents['time'] != timestamp:
                    # if the file has changed, then we need to reload it
                    print(f"S3 File {filename} has changed, reloading.")
                else:
                    # if the file hasn't changed, then we can just return the cached contents
                    print(f"S3 File {filename} has not changed, returning cached contents.")
                    return cached_file_contents['contents']

            file_content = s3_object['Body'].read().decode('utf-8')

            break
    else:
        raise FileNotFoundError(f"File {filename} not found in any of the specified stages or locally.")

    # Cache the file contents globally for all services to use it, saving further S3 or filesystem calls
    file_contents_cache[filename] = {
        "contents": file_content,
        "time": timestamp
    }
    timestamp_pretty = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    print(f"File contents cached for {filename} - time: {timestamp_pretty}")
    return file_content


def get_file_time(filename):
    # note the cache is not aware of stages at this time, so if
    #   the timestamp represents the first stage it was loaded from
    #   if a different stage has a newer file at a later time, it won't
    #   be refreshed in the cache
    if filename in file_contents_cache:
        return file_contents_cache.get(filename).get("time")
    else:
        raise FileNotFoundError(f"File {filename} not found in cache.")


def file_exists_in_s3(bucket_name, key_name):
    s3 = boto3.client('s3')

    try:
        # This only retrieves metadata and doesn't download the object
        s3.head_object(Bucket=bucket_name, Key=key_name)
        print(f"File found in S3: {key_name}")
        return True
    except ClientError as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the object does not exist.
        if e.response['Error']['Code'] == '404':
            print(f"File not found in S3: {key_name}")
            return False
        else:
            # If it was a different error, then raise the error
            raise


def search_storage(prefix, pattern=None) -> list:
    CHALICE_STAGE = os.environ.get("CHALICE_STAGE", "local")

    # Find where to start searching based on the CHALICE_STAGE
    start_index = SEARCH_STAGES.index(CHALICE_STAGE)

    # Search in stages starting from the CHALICE_STAGE and beyond
    for stage in SEARCH_STAGES[start_index:]:
        matched_files = search_storage_with_stage(stage, prefix, pattern)

        # if we find any matches, we stop and return it
        if (len(matched_files) > 0):
            return matched_files

        # otherwise, we keep searching later stages - and ultimately local
    return []


def search_storage_with_stage(stage, prefix, pattern=None) -> list:
    if stage == "local":
        base_path = os.path.join(os.path.abspath(os.path.curdir), LOCAL_BASE_FOLDER, prefix)
        unsorted_paths = glob.glob(os.path.join(base_path, pattern))
        matched_files = [os.path.relpath(path, os.path.join(os.path.abspath(os.path.curdir), LOCAL_BASE_FOLDER)) for path in unsorted_paths]
    else:
        s3 = boto3.client('s3')
        paginator = s3.get_paginator('list_objects_v2')

        matched_files = []

        for page in paginator.paginate(Bucket=s3_storage_bucket_name,
                                       Prefix=os.path.join(stage, prefix),
                                       PaginationConfig={
                                           'MaxItems': 500,
                                           'PageSize': 50}
                                       ):
            for obj in page.get('Contents', []):
                actualFile = os.path.relpath(obj['Key'], stage)

                # using fnmatch to filter results
                if (pattern is None
                        or fnmatch.fnmatch(obj['Key'], os.path.join(stage, prefix, pattern))):
                    matched_files.append(actualFile)

    return sorted(matched_files)
