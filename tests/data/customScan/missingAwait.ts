
registerProjectLevelCommands(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand(
        boostnb.NOTEBOOK_TYPE + "." + BoostCommands.processProject,
        async (kernelCommand?: string) => {
            // we only process project level analysis at summary level for now
            const projectBoostFile = getBoostFile(
                undefined,
                BoostFileType.summary,
                false
            );
            // create the Boost file, if it doesn't exist
            if (!fs.existsSync(projectBoostFile.fsPath)) {
                boostLogging.warn(
                    `Unable to open Project-level Boost Notebook [${projectBoostFile.fsPath}]; check the Polyverse Boost Output channel for details`
                );
                return;
            }

            const likelyViaUI =
                !kernelCommand || typeof kernelCommand !== "string";
            if (likelyViaUI) {
                kernelCommand = BoostConfiguration.currentKernelCommand;
            }

            const targetedKernel = this.getCurrentKernel(kernelCommand);
            if (targetedKernel === undefined) {
                boostLogging.warn(
                    `Unable to match analysis kernel for ${kernelCommand}`,
                    likelyViaUI
                );
                return;
            }

            if (
                ![
                    quickBlueprintKernelName,
                    quickComplianceSummaryKernelName,
                    quickSecuritySummaryKernelName,
                    quickPerformanceSummaryKernelName,
                ].includes(targetedKernel.command)
            ) {
                boostLogging.error(
                    "Currently, only Quick Analysis is supported at Project-level",
                    likelyViaUI
                );
                return;
            }

            let notebook = new boostnb.BoostNotebook();
            notebook.load(projectBoostFile.fsPath);
            targetedKernel
                .executeAllWithAuthorization(notebook.cells, notebook, true)
                .then(() => {
                    // ensure we save the notebook if we successfully processed it
                    notebook.flushToFS();
                    switch (targetedKernel.command) {
                        case quickBlueprintKernelName:
                            this.blueprint?.refresh();
                            break;
                        case quickComplianceSummaryKernelName:
                            this.compliance?.refresh();
                            break;
                        case quickSecuritySummaryKernelName:
                            this.security?.refresh();
                            break;
                        case quickPerformanceSummaryKernelName:
                            this.performance?.refresh();
                            break;
                        default:
                            throw new Error(
                                `Unknown Project Level command ${targetedKernel.command}`
                            );
                            break;
                    }

                    boostLogging.info(
                        `Saved Updated Notebook for ${kernelCommand} in file:[${projectBoostFile.fsPath}]`,
                        likelyViaUI
                    );

                    if (
                        targetedKernel.command !== quickBlueprintKernelName
                    ) {
                        return;
                    }

                    // if the quick-blueprint provided recommended file exclusion list
                    //      then let's add those to the ignore file for future analysis
                    const blueprintCell = findCellByKernel(
                        notebook,
                        targetedKernel.outputType
                    );
                    // we only use recommendation from quick-blueprint
                    if (
                        blueprintCell?.metadata?.blueprintType !== "quick"
                    ) {
                        return;
                    }

                    //if we don't have a boostignore file, then do the update and create one
                    //if we have one, then already generated it and skip this step.
                    const boostIgnoreFile = getBoostIgnoreFile();
                    if (
                        boostIgnoreFile === undefined ||
                        !fs.existsSync(boostIgnoreFile.fsPath)
                    ) {
                        blueprintCell?.outputs.forEach((output) => {
                            if (
                                output.metadata.outputType !==
                                    targetedKernel.outputType ||
                                !output?.metadata?.details
                                    ?.recommendedListOfFilesToExcludeFromAnalysis
                            ) {
                                return;
                            }

                            output.metadata.details.recommendedListOfFilesToExcludeFromAnalysis.forEach(
                                (filename: string) => {
                                    updateBoostIgnoreForTarget(
                                        filename,
                                        false
                                    );
                                }
                            );
                        });
                    }
                })
                .catch((error) => {
                    boostLogging.warn(
                        `Skipping Notebook save - due to Error Processing ${kernelCommand} on file:[${projectBoostFile.fsPath}] due to error:${error}`,
                        likelyViaUI
                    );
                });
        }
    );
    context.subscriptions.push(disposable);
}