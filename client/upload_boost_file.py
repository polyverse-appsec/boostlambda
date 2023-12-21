import boto3
import sys
import time
import random


def write_to_dynamodb(table_name, project_path, data_path, file_paths):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Read and concatenate file contents
    data = ''
    for file_path in file_paths:
        try:
            with open(file_path, 'r') as file:
                data += file.read() + "\n\n"
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return

    max_size = 300 * 1024  # 300 KB
    part_number = 0

    def upload_data(data_chunk):
        nonlocal part_number
        part_number += 1
        retries = 0
        max_retries = 8
        while retries < max_retries:
            try:
                response = table.put_item(
                    Item={
                        'projectPath': project_path,
                        'dataPath': f"{data_path}_part{part_number}",
                        'data': data_chunk
                    }
                )
                print(f"Part {part_number} written successfully. Response:", response)
                return
            except boto3.errorfactory.ProvisionedThroughputExceededException:
                wait_time = (2 ** retries) + (random.randint(3000, 10000) / 1000)
                print(f"Waiting for {wait_time:.3f} seconds...")
                time.sleep(wait_time)
                retries += 1
            except Exception as e:
                print(f"Error writing to DynamoDB: {e}")
                return

    while len(data.encode('utf-8')) > max_size:
        split_index = data.rfind('\n\n', 0, max_size)
        if split_index == -1:
            print("Error: Unable to split the data into smaller parts.")
            return
        data_chunk, data = data[:split_index], data[split_index:]

        upload_data(data_chunk)

    if data:
        upload_data(data)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python script.py <TableName> <ProjectPath> <DataPath> <FilePath1> [<FilePath2> ...]")
        sys.exit(1)

    table_name = sys.argv[1]
    project_path = sys.argv[2]
    data_path = sys.argv[3]
    file_paths = sys.argv[4:]

    write_to_dynamodb(table_name, project_path, data_path, file_paths)
