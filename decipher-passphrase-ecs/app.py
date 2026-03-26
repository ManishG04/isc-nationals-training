import boto3
import json
from datetime import datetime
import re
import os

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
dict_table = dynamodb.Table('Dictionary')
checks_table = dynamodb.Table('Checks')
matches_table = dynamodb.Table('Matches')
sqs = boto3.client('sqs')

QUEUE_URL = os.environ.get('QUEUE_URL')

words = []
items = dict_table.scan()['Items']
for item in items:
    words.append(item['passphrase'])
    
def decipher(word):
    trimmed_word = word[2:-2]
    reversed_word = trimmed_word[::-1]
    lower_word = reversed_word.lower()
    a_z = list(map(chr, range(ord('a'), ord('z')+1)))
    z_a = sorted(a_z, reverse=True)
    mapped = dict(zip(a_z, z_a))
    s = list(lower_word)
    for i, val in enumerate(s):
        s[i] = mapped[val]
    return ''.join(s)

def is_valid_filename(filename):
    """Check if filename matches frp-<number>.txt format"""
    pattern = r'^frp-\d+\.txt$'
    return re.match(pattern, filename) is not None

def process_file(s3_key, s3_bucket):
    """Process single file"""
    try:
        if not is_valid_filename(s3_key):
            print(f"Skipping invalid filename: {s3_key}")
            return

        content = s3.get_object(Bucket=s3_bucket, Key=s3_key)['Body'].read().decode().strip()
        
        processed = decipher(content)
        file_index = s3_key[:-4]  
        print(f"{file_index} -> {processed}")
        
        checks_table.put_item(Item={
            'timestamp': datetime.now().isoformat(),
            'file-index': file_index,
            'processed_string': processed
        })
        
        if processed in words:
            matches_table.put_item(Item={
                'timestamp': datetime.now().isoformat(),
                'file-index': file_index,
                'processed_string': processed
            })
            print(f"✅ MATCH: {s3_key} -> {processed}")
        else:
            print(f"No match: {s3_key} -> {processed}")
            
    except Exception as e:
        print(f"Error processing {s3_key}: {e}")

while True:
    try:
        messages = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10, WaitTimeSeconds=20).get('Messages', [])
        
        if not messages:
            print("No messages, waiting...")
            continue
            
        for msg in messages:
            for record in json.loads(msg['Body'])['Records']:
                if record['eventSource'] == 'aws:s3':
                    process_file(record['s3']['object']['key'], record['s3']['bucket']['name'])
                    
            # CRITICAL: Delete message to prevent infinite loop
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
            print("Message processed and deleted")
    
    except Exception as e:
        print(f"Error in main loop: {e}")
        import time
        time.sleep(5)