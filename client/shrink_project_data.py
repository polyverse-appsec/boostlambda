import json
import argparse


def compress_data(input_data):
    compressed_data = {
        "projectSummary": {
            "project": input_data["summary"].get("projectName"),
            "files": {
                "total": input_data["summary"].get("filesToAnalyze"),
                "analyzed": input_data["summary"].get("filesAnalyzed"),
                "ignored": input_data["summary"].get("filesIgnored"),
            },
            "analysisState": input_data["uiState"].get("analysisState"),
            "analysisMode": input_data["uiState"]["activityBarState"].get("summaryViewState", {}).get("analysisMode"),
            "types": input_data["uiState"]["activityBarState"]["summaryViewState"].get("analysisTypesState"),
            "issues": input_data["summary"].get("issues", [])
        },
        "account": input_data.get("account"),
    }

    # Compress sectionSummary
    compressed_data["analysisSummary"] = {
        "keys": ["status", "blocksCompleted", "analysisErrors", "blocksWithIssues", "totalBlocks", "filesAnalyzed"]
    }
    for section, values in input_data["sectionSummary"].items():
        if section in ["summary", "bugAnalysis", "complianceCode", "performance", "flowDiagram"]:
            continue
        compressed_data["analysisSummary"][section] = [
            values.get("status"),
            values.get("completedCells"),
            values.get("errorCells"),
            values.get("issueCells"),
            values.get("totalCells"),
            values.get("filesAnalyzed")
        ]

    # Compress files
    compressed_data["fileDetails"] = {}
    for file_name, file_data in input_data["files"].items():
        status_set = set()

        for section, section_data in file_data["sections"].items():
            if section in ["summary", "bugAnalysis", "complianceCode", "performance", "flowDiagram"]:
                continue

            status_set.add(section_data.get("status"))

        # Determine the final status for the file
        if len(status_set) == 0:
            final_status = "not-started"
        elif len(status_set) == 1 and "completed" in status_set:
            final_status = "completed"
        else:
            final_status = "incomplete"

        compressed_data["files"][file_name] = final_status

    return compressed_data


def main(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)

    compressed_data = compress_data(data)

    # Write the compressed JSON to the output file
    with open(output_file, 'w') as f:
        json.dump(compressed_data, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compress JSON data format.')
    parser.add_argument('input', help='Path to the input JSON file')
    parser.add_argument('output', help='Path to the output JSON file')
    args = parser.parse_args()

    main(args.input, args.output)
