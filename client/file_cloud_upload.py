import boto3
import sys
import os


def upload_to_s3(stage, filepath, path):
    # Set up boto3 S3 client
    s3_client = boto3.client('s3')

    # Define your bucket name
    bucket_name = "polyverse-boost"

    # Extract the filename from the provided filepath
    filename = os.path.basename(filepath)

    # Construct the full path
    s3_key = f"{stage}/{path}/{filename}"

    try:
        # Upload file to the specified S3 path
        s3_client.upload_file(filepath, bucket_name, s3_key)
        print(f"File {filename} uploaded to {s3_key} in {bucket_name}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) != 4:
        print("Usage: python script_name.py <stage> <filename> <path>")
        sys.exit(1)

    # Get arguments
    stage_arg = sys.argv[1]
    filename_arg = sys.argv[2]
    path_arg = sys.argv[3]

    # Call function to upload file to S3
    upload_to_s3(stage_arg, filename_arg, path_arg)
