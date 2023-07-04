void commitBlockSynchronization(ExtendedBlock oldBlock,
      long newgenerationstamp, long newlength,
      boolean closeFile, boolean deleteblock, DatanodeID[] newtargets,
      String[] newtargetstorages) throws IOException {
    LOG.info("commitBlockSynchronization(oldBlock=" + oldBlock
             + ", newgenerationstamp=" + newgenerationstamp
             + ", newlength=" + newlength
             + ", newtargets=" + Arrays.asList(newtargets)
             + ", closeFile=" + closeFile
             + ", deleteBlock=" + deleteblock
             + ")");
    checkOperation(OperationCategory.WRITE);
    final String src;
    writeLock();
    boolean copyTruncate = false;
    BlockInfo truncatedBlock = null;
    try {
      checkOperation(OperationCategory.WRITE);
      // If a DN tries to commit to the standby, the recovery will
      // fail, and the next retry will succeed on the new NN.
  
      checkNameNodeSafeMode(
          "Cannot commitBlockSynchronization while in safe mode");
      final BlockInfo storedBlock = getStoredBlock(
          ExtendedBlock.getLocalBlock(oldBlock));
      if (storedBlock == null) {
        if (deleteblock) {
          // This may be a retry attempt so ignore the failure
          // to locate the block.
          LOG.debug("Block (={}) not found", oldBlock);
          return;
        } else {
          throw new IOException("Block (=" + oldBlock + ") not found");
        }
      }
      final long oldGenerationStamp = storedBlock.getGenerationStamp();
      final long oldNumBytes = storedBlock.getNumBytes();
      //
      // The implementation of delete operation (see @deleteInternal method)
      // first removes the file paths from namespace, and delays the removal
      // of blocks to later time for better performance. When
      // commitBlockSynchronization (this method) is called in between, the
      // blockCollection of storedBlock could have been assigned to null by
      // the delete operation, throw IOException here instead of NPE; if the
      // file path is already removed from namespace by the delete operation,
      // throw FileNotFoundException here, so not to proceed to the end of
      // this method to add a CloseOp to the edit log for an already deleted
      // file (See HDFS-6825).
      //
      if (storedBlock.isDeleted()) {
        throw new IOException("The blockCollection of " + storedBlock
            + " is null, likely because the file owning this block was"
            + " deleted and the block removal is delayed");
      }
      final INodeFile iFile = getBlockCollection(storedBlock);
      src = iFile.getFullPathName();
      if (isFileDeleted(iFile)) {
        throw new FileNotFoundException("File not found: "
            + src + ", likely due to delayed block removal");
      }
      if ((!iFile.isUnderConstruction() || storedBlock.isComplete()) &&
          iFile.getLastBlock().isComplete()) {
        if (LOG.isDebugEnabled()) {
          LOG.debug("Unexpected block (={}) since the file (={}) is not under construction",
              oldBlock, iFile.getLocalName());
        }

        return;
      }

      truncatedBlock = iFile.getLastBlock();
      final long recoveryId = truncatedBlock.getUnderConstructionFeature()
          .getBlockRecoveryId();
      copyTruncate = truncatedBlock.getBlockId() != storedBlock.getBlockId();
      if(recoveryId != newgenerationstamp) {
        throw new IOException("The recovery id " + newgenerationstamp
                              + " does not match current recovery id "
                              + recoveryId + " for block " + oldBlock);
      }

      if (deleteblock) {
        Block blockToDel = ExtendedBlock.getLocalBlock(oldBlock);
        boolean remove = iFile.removeLastBlock(blockToDel) != null;
        if (remove) {
          blockManager.removeBlock(storedBlock);
        }
      } else {
        // update last block
        if(!copyTruncate) {
          storedBlock.setGenerationStamp(newgenerationstamp);
          storedBlock.setNumBytes(newlength);
        }

        // Find the target DatanodeStorageInfos. If not found because of invalid
        // or empty DatanodeID/StorageID, the slot of same offset in dsInfos is
        // null
        final DatanodeStorageInfo[] dsInfos = blockManager.getDatanodeManager().
            getDatanodeStorageInfos(newtargets, newtargetstorages,
                "src=%s, oldBlock=%s, newgenerationstamp=%d, newlength=%d",
                src, oldBlock, newgenerationstamp, newlength);

        if (closeFile && dsInfos != null) {
          // the file is getting closed. Insert block locations into blockManager.
          // Otherwise fsck will report these blocks as MISSING, especially if the
          // blocksReceived from Datanodes take a long time to arrive.
          for (int i = 0; i < dsInfos.length; i++) {
            if (dsInfos[i] != null) {
              if(copyTruncate) {
                dsInfos[i].addBlock(truncatedBlock, truncatedBlock);
              } else {
                Block bi = new Block(storedBlock);
                if (storedBlock.isStriped()) {
                  bi.setBlockId(bi.getBlockId() + i);
                }
                dsInfos[i].addBlock(storedBlock, bi);
              }
            }
          }
        }

        // add pipeline locations into the INodeUnderConstruction
        if(copyTruncate) {
          iFile.convertLastBlockToUC(truncatedBlock, dsInfos);
        } else {
          iFile.convertLastBlockToUC(storedBlock, dsInfos);
          if (closeFile) {
            blockManager.markBlockReplicasAsCorrupt(oldBlock.getLocalBlock(),
                storedBlock, oldGenerationStamp, oldNumBytes,
                dsInfos);
          }
        }
      }

      if (closeFile) {
        if(copyTruncate) {
          closeFileCommitBlocks(src, iFile, truncatedBlock);
          if(!iFile.isBlockInLatestSnapshot(storedBlock)) {
            blockManager.removeBlock(storedBlock);
          }
        } else {
          closeFileCommitBlocks(src, iFile, storedBlock);
        }
      } else {
        // If this commit does not want to close the file, persist blocks
        FSDirWriteFileOp.persistBlocks(dir, src, iFile, false);
      }
      blockManager.successfulBlockRecovery(storedBlock);
    } finally {
      writeUnlock("commitBlockSynchronization");
    }
    getEditLog().logSync();
    if (closeFile) {
      LOG.info("commitBlockSynchronization(oldBlock=" + oldBlock
          + ", file=" + src
          + (copyTruncate ? ", newBlock=" + truncatedBlock
              : ", newgenerationstamp=" + newgenerationstamp)
          + ", newlength=" + newlength
          + ", newtargets=" + Arrays.asList(newtargets) + ") successful");
    } else {
      LOG.info("commitBlockSynchronization(" + oldBlock + ") successful");
    }
  }