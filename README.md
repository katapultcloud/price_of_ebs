# price_of_ebs
This script provides a pricing and capacity summary of EBS volumes in a specified region. The script is also capable of recognising unused EBS volumes, print their utilisation and costs.

## How it works
The script fetches all EBS volumes in specified region counts them into categories based on EBS type. Then the script fetches current EBS prices from AWS Pricing API for specified region and calculates EBS monthly expenditures. 

## Requirements
* boto3
* argparse
* json

## Options
This is the help output from the script. 
```
$ ./price_of_ebs.py --help
usage: price_of_ebs.py [-h] [-p PROFILE] [-i AWS_ID] [-k AWS_SECRET_KEY] [-v]
                       aws_region

Calculate price of EBS volumes in given region

positional arguments:
  aws_region            aws region code e.g. "us-east-1"

optional arguments:
  -h, --help            show this help message and exit
  -p PROFILE, --profile PROFILE
                        aws profile to use, "default" profile is used if not
                        specified
  -i AWS_ID, --aws-id AWS_ID
                        aws access key id to use
  -k AWS_SECRET_KEY, --aws-secret-key AWS_SECRET_KEY
                        aws secret access key to use
  -v, --verbose         display verbose output including pricing for each
                        storage type
```

### Authentication
The script is able to utilise multiple authentication methods, first using profiles from `~/.aws/credentials` (preffered) and second using direct credentials as arguments to the script (not preffered). Third method will be using environmental variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` this will not be preffered also.

## Examples
### Examples with no unused EBS
Using the script in non-verbose mode with `default` profile.
```
$ ./price_of_ebs.py eu-west-1
total: $247
```

Using the script in verbose mode with different AWS profile.
```
$ ./price_of_ebs.py --verbose --profile ebs_user eu-west-1 


Total expenditures per EBS type
+----------+-------+
|   type   | price |
+----------+-------+
|   gp2    |  $2   |
+----------+-------+
| standard |  $0   |
+----------+-------+
|   sc1    |  $0   |
+----------+-------+
|   io1    |  $0   |
+----------+-------+
|   st1    |  $0   |
+----------+-------+


Total sizes per EBS type
+----------+--------+
|   type   |  size  |
+----------+--------+
|   gp2    | 20 GiB |
+----------+--------+
| standard | 0 GiB  |
+----------+--------+
|   sc1    | 0 GiB  |
+----------+--------+
|   io1    | 0 GiB  |
+----------+--------+
|   st1    | 0 GiB  |
+----------+--------+
```

### Examples with unused EBS
Using the script in non-verbose mode with `default` profile.
```
$ ./price_of_ebs.py eu-west-1
total: $41
unused:$38
```

Using the script in verbose mode with different AWS profile.
```
./price_of_ebs.py --verbose --profile ebs_user eu-west-1 


Total expenditures per EBS type
+----------+-------+
|   type   | price |
+----------+-------+
|   gp2    |  $11  |
+----------+-------+
| standard |  $0   |
+----------+-------+
|   sc1    |  $0   |
+----------+-------+
|   io1    |  $0   |
+----------+-------+
|   st1    |  $30  |
+----------+-------+


Total sizes per EBS type
+----------+---------+
|   type   |  size   |
+----------+---------+
|   gp2    | 96 GiB  |
+----------+---------+
| standard |  0 GiB  |
+----------+---------+
|   sc1    |  0 GiB  |
+----------+---------+
|   io1    |  0 GiB  |
+----------+---------+
|   st1    | 600 GiB |
+----------+---------+


There are unused EBS volumes
+----------+-------+
|   type   | price |
+----------+-------+
|   gp2    |  $8   |
+----------+-------+
| standard |  $0   |
+----------+-------+
|   sc1    |  $0   |
+----------+-------+
|   io1    |  $0   |
+----------+-------+
|   st1    |  $30  |
+----------+-------+


Total sizes per EBS type
+----------+---------+
|   type   |  size   |
+----------+---------+
|   gp2    | 76 GiB  |
+----------+---------+
| standard |  0 GiB  |
+----------+---------+
|   sc1    |  0 GiB  |
+----------+---------+
|   io1    |  0 GiB  |
+----------+---------+
|   st1    | 600 GiB |
+----------+---------+


Here are unused volume IDs
------------------------
vol-04836d64ae4837e93
vol-0f5d4bced12ee5a86
```

## Recommendations
Utilize profile or access keys with minimal privileges to AWS resources. Following priviliges are required to make this work.
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeVolumes",
                "pricing:GetProducts"
            ],
            "Resource": "*"
        }
    ]
}
```

## Future development
* Addition of another authentication method using environmental variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
* Addition of new options that could calculate daily, weekly and anual expenditures. Now the script only monthly by default. This could be specified with `-y` or `--year`, `-w` or `--week` and so on.

## Licence
GPL-v3

## Author Information
Stefan Roman (stefan.roman@katapult.cloud)
