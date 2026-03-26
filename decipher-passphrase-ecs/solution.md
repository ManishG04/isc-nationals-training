## Unziping a million files
```bash
tar -xf archive.tar -C /target/directory --checkpoint=10000 --checkpoint-action=echo="%u%T" --warning=no-timestamp
```

## Uploading a million files to S3

### 1. s5cmd
This utility is in Go and gives very very fast upload speeds with the help of multi-threading

Commands to get it and run it:-

```bash
wget https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz
tar -xvzf s5cmd_2.2.2_Linux-64bit.tar.gz
```
(Make sure you are in the directory where s5cmd was extracted, or move it to your /usr/local/bin/ if you prefer).

```bash
./s5cmd cp '/path/to/your/extracted/files/*' s3://your-staging-bucket-name/ #if in the directory

s5cmd cp '/path/to/your/extracted/files/*' s3://your-staging-bucket-name/ #if added to path
```

### 2. AWS set configuration
It is the AWS native way but not that much fast, it will be faster than standard upload but not as much as s5cmd, use it when no 3rd party tools are allowed

```bash
aws configure set default.s3.max_concurrent_requests 500
aws configure set default.s3.max_queue_size 10000
```
No they aren't account wide, they just change configuration in the ec2 itself

### 3. S3 Transfer Acceleration
It is also a very fast way but for transferring files from one region to another region fast, it is just a toggle in S3 bucket properties and has a good amount of cost associated with it.

### 4. AWS DataSync
Used for data migration from on prem to AWS servers needs some provisioning so the provisioning time in the competition could be the bottleneck, else it's the fastest. 


## Checking if extracted files matched number of files available in the .tar

```bash
# Count files in archive (before extraction)
ARCHIVE_COUNT=$(tar -tf frps.tar | wc -l)
echo "Files in archive: $ARCHIVE_COUNT"

# Count extracted files (streaming approach)
EXTRACTED_COUNT=$(find extracted -type f -print0 | tr -cd '\0' | wc -c)
echo "Files extracted: $EXTRACTED_COUNT"

# Compare
if [ "$ARCHIVE_COUNT" -eq "$EXTRACTED_COUNT" ]; then
    echo "✅ SUCCESS: All files extracted correctly"
else
    echo "❌ ERROR: File count mismatch!"
fi
```