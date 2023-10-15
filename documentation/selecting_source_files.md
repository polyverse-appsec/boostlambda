# Customizing the analysis file list

By default, Sara will prioritize all of your source files to analyze the most interesting files first.
If you want to customize the source file list, you can either select only the files you want to analyze, or you can provide an exclusion list from analysis.

## Selecting files to analyze
If you know which files you want to analyze, you can provide their names and/or folders in a .boostOnly file located in your project root folder. The format of the file is relative patterns or globs, one per line.

## Creating a custom exclusion list
If you know which files to exclude from analysis, you can add a .boostIgnore file to specify which files to ignore or exclude from analysis. The format of the file is the same as .gitignore, based on relative or glob patterns.

Sara will automatically create a .boostIgnore file based on files she believes are not interesting to analyze. You can further customize it any anytime.