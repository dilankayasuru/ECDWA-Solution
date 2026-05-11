"""
AquaSense Smart Utilities - Data Migration to AWS S3
====================================================
Simulates the data migration phase by uploading the exported
CSV files from the on premise database to the AWS S3 Data Lake.

In the production architecture, this would be done by AWS DMS (Database
Migration Service). For the POC, we upload CSVs directly to S3 to demonstrate
the migration data flow.

Pipeline:
  Local PostgreSQL -> CSV Export -> S3 Data Lake -> SageMaker (reads from S3)

Usage:
  # First generate data (creates exported_data/ folder)
  python generate_historical_data.py --csv-only

  # Then upload to S3 (set bucket name from terraform output)
  python upload_to_s3.py --bucket <S3_DATA_LAKE_BUCKET>

  # Or set as environment variable
  set S3_BUCKET=asu-data-lake-xxxxxxxx
  python upload_to_s3.py
"""

import argparse
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

DEFAULT_REGION = "ap-south-1"
DEFAULT_DATA_DIR = "exported_data"
S3_MIGRATION_PREFIX = "migration/historical-data"


def upload_file(s3_client, filepath, bucket, s3_key):
    # Upload a single file to S3
    file_size = os.path.getsize(filepath)
    try:
        s3_client.upload_file(
            filepath, bucket, s3_key,
            ExtraArgs={"ContentType": "text/csv", "ServerSideEncryption": "AES256"},
        )
        return True, file_size
    except ClientError as e:
        print(f"Upload failed for {filepath}: {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(description="AquaSense Data Migration to AWS S3")
    parser.add_argument(
        "--bucket",
        default=os.environ.get("S3_BUCKET", ""),
        help="S3 Data Lake bucket name (or set S3_BUCKET env var)",
    )
    parser.add_argument("--region", default=DEFAULT_REGION, help="AWS region")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="Local data directory")
    parser.add_argument("--prefix", default=S3_MIGRATION_PREFIX, help="S3 key prefix")

    args = parser.parse_args()

    if not args.bucket:
        print("ERROR: No S3 bucket specified.")
        print("Usage: python upload_to_s3.py --bucket <BUCKET_NAME>")
        print("   or: set S3_BUCKET=<BUCKET_NAME> && python upload_to_s3.py")
        print("\nGet bucket name: terraform -chdir=../infrastructure output s3_data_lake_bucket")
        sys.exit(1)

    if not os.path.isdir(args.data_dir):
        print(f"ERROR: Data directory not found: {args.data_dir}")
        print("Run generate_historical_data.py first to create the data.")
        sys.exit(1)

    # Find CSV files
    csv_files = [f for f in os.listdir(args.data_dir) if f.endswith(".csv")]
    if not csv_files:
        print(f"ERROR: No CSV files found in {args.data_dir}/")
        sys.exit(1)

    print("=" * 60)
    print("AquaSense Data Migration - Upload to S3 Data Lake")
    print("=" * 60)
    print(f"  Source:      {os.path.abspath(args.data_dir)}/")
    print(f"  Destination: s3://{args.bucket}/{args.prefix}/")
    print(f"  Region:      {args.region}")
    print(f"  Files:       {len(csv_files)}")
    print("=" * 60)

    try:
        s3_client = boto3.client("s3", region_name=args.region)
        # Verify bucket exists
        s3_client.head_bucket(Bucket=args.bucket)
    except NoCredentialsError:
        print("\nAWS credentials not configured.")
        print("Run: aws configure")
        sys.exit(1)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "404":
            print(f"\nBucket '{args.bucket}' does not exist.")
        elif code == "403":
            print(f"\nAccess denied to bucket '{args.bucket}'.")
        else:
            print(f"\nError accessing bucket: {e}")
        sys.exit(1)

    # Upload each CSV
    total_uploaded = 0
    total_bytes = 0
    start_time = time.time()

    for csv_file in sorted(csv_files):
        filepath = os.path.join(args.data_dir, csv_file)
        s3_key = f"{args.prefix}/{csv_file}"

        print(f"\nUploading {csv_file}...")
        success, size = upload_file(s3_client, filepath, args.bucket, s3_key)

        if success:
            total_uploaded += 1
            total_bytes += size
            print(f"s3://{args.bucket}/{s3_key} ({size:,} bytes)")

    elapsed = time.time() - start_time

    # Upload a migration manifest
    import json
    manifest = {
        "migration_type": "historical-data-migration",
        "source": "on-premise-postgresql",
        "destination": f"s3://{args.bucket}/{args.prefix}/",
        "migrated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": [
            {"name": f, "s3_key": f"{args.prefix}/{f}", "size_bytes": os.path.getsize(os.path.join(args.data_dir, f))}
            for f in sorted(csv_files)
        ],
        "total_files": total_uploaded,
        "total_bytes": total_bytes,
        "notes": "Migrated from on-premise PostgreSQL database. In production, AWS DMS (Database Migration Service) would perform continuous replication.",
    }

    s3_client.put_object(
        Bucket=args.bucket,
        Key=f"{args.prefix}/migration_manifest.json",
        Body=json.dumps(manifest, indent=2),
        ContentType="application/json",
    )

    print("\n" + "=" * 60)
    print(f"Migration Complete!")
    print(f"  Files uploaded:  {total_uploaded}/{len(csv_files)}")
    print(f"  Total data:      {total_bytes:,} bytes ({total_bytes / 1024 / 1024:.2f} MB)")
    print(f"  Duration:        {elapsed:.1f}s")
    print(f"  Manifest:        s3://{args.bucket}/{args.prefix}/migration_manifest.json")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Open SageMaker Notebook and load data from S3")
    print(f"     S3 path: s3://{args.bucket}/{args.prefix}/telemetry_readings.csv")
    print("  2. Verify in AWS Console -> S3 -> Browse bucket")
    print("  3. Take screenshots for Task 6 (Data Migration) evidence")


if __name__ == "__main__":
    main()
