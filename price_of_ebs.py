#!/usr/bin/env python3

# -*- coding: utf-8 -*-
# Copyright: (c) 2018, Stefan Roman <stefan.roman@katapult.cloud>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# import modules
import boto3
import sys
import argparse
import json
from beautifultable import BeautifulTable

# colors!!
class bcolors:
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


# adding positional and optional arguments
def resolve_arguments():
    parser = argparse.ArgumentParser(
        description='Calculate price of EBS volumes in given region')
    # argument to specify the region where to pull EBS volumes from 
    parser.add_argument('aws_region', help='aws region code e.g. "us-east-1"')
    # support for authentication using custom or default AWS profile
    parser.add_argument(
        '-p',
        '--profile',
        default='default',
        help='aws profile to use, "default" profile is used if not specified')
    # support for authentication using AWS access id and secret access key
    parser.add_argument(
        '-i', '--aws-id', default=None, help='aws access key id to use')
    parser.add_argument(
        '-k',
        '--aws-secret-key',
        default=None,
        help='aws secret access key to use')
    # verbosity switch, by default this is turned off
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help='display verbose output including pricing for each storage type')

    arguments = parser.parse_args()

    # adding mutual inclusivity for awd-id and secret-key-key
    if arguments.aws_id and not arguments.aws_secret_key:
        parser.error('aws-id requires aws-secret-key')
    elif not arguments.aws_id and arguments.aws_secret_key:
        parser.error('aws-secret-key requires aws-id')

    aws_region = arguments.aws_region
    # build credentials dict
    credentials = {
        'profile': arguments.profile,
        'aws_access_key_id': arguments.aws_id,
        'aws_secret_access_key': arguments.aws_secret_key
    }

    verbose_mode = arguments.verbose
    return aws_region, credentials, verbose_mode


# return two auth sessions since "pricing" is accessible ony from two regions
def authenticate(region, creds):
    aws_pricing_region = "us-east-1"
    # if credentials were specified with -k and -i option use them to authenticate
    if creds['aws_access_key_id'] and creds['aws_secret_access_key']:
        session = boto3.session.Session(
            aws_access_key_id=creds['aws_access_key_id'],
            aws_secret_access_key=creds['aws_secret_access_key'])
    # if not use specified profile or use "default" if not declared
    else:
        session = boto3.session.Session(profile_name=creds['profile'])
    # return session for fetching EBS volumes from AWS API
    ec2_auth = session.resource('ec2', region_name=region)
    # return session for fetching EBS prices
    pricing_auth = session.client('pricing', region_name=aws_pricing_region)
    return ec2_auth, pricing_auth


# obtain all EBS volumes from a particular region form AWS API
def get_all_volumes(auth):
    # fetch all EBS volumes from AWS API
    ebs_volumes = auth.volumes.all()
    return ebs_volumes


# extract and add up EBS sizes based on type of EBS
def extract_and_calculate_size(ebs_volumes):
    final_sizes = {"gp2": 0, "gp3": 0, "standard": 0, "sc1": 0, "io1": 0, "st1": 0}
    ebs_list = []
    # extract type and size of each particular EBS volumes
    for volume in ebs_volumes:
        ebs_list.append({'type': volume.volume_type, 'size': volume.size})
    # add up EBS volumes based on their type
    for ebs_volume in ebs_list:
        final_sizes[ebs_volume[
            'type']] = final_sizes[ebs_volume['type']] + ebs_volume['size']
    return final_sizes


# extract unused EBS volumes and add them up based on EBS type
def determine_unused_ebs(ebs_volumes):
    final_sizes = {"gp2": 0, "standard": 0, "sc1": 0, "io1": 0, "st1": 0}
    ebs_list = []
    unused_ebs = []
    # extract type, size, id and attachments from each EBS volume
    for volume in ebs_volumes:
        ebs_list.append({
            'id': volume.id,
            'attachments': volume.attachments,
            'type': volume.volume_type,
            'size': volume.size
        })
    # determine whether EBS has an attachment
    # if not it's added to the list and it's size added to the dict based on EBS type
    for ebs_volume in ebs_list:
        if ebs_volume['attachments'] == []:
            unused_ebs.append(ebs_volume['id'])
            final_sizes[ebs_volume[
                'type']] = final_sizes[ebs_volume['type']] + ebs_volume['size']
    return unused_ebs, final_sizes


# resolve a region to verbose region name (this is due to pricing API not using region codes e.g. eu-west-1)
def resolve_region(region):
    aws_region_map = {
        'ca-central-1': 'Canada (Central)',
        'ap-northeast-3': 'Asia Pacific (Osaka-Local)',
        'us-east-1': 'US East (N. Virginia)',
        'ap-northeast-2': 'Asia Pacific (Seoul)',
        'us-gov-west-1': 'AWS GovCloud (US)',
        'us-east-2': 'US East (Ohio)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)',
        'ap-south-1': 'Asia Pacific (Mumbai)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'sa-east-1': 'South America (Sao Paulo)',
        'us-west-2': 'US West (Oregon)',
        'eu-west-1': 'EU (Ireland)',
        'eu-west-3': 'EU (Paris)',
        'eu-west-2': 'EU (London)',
        'us-west-1': 'US West (N. California)',
        'eu-central-1': 'EU (Frankfurt)'
    }
    # if region is not found return an error and exit the program
    try:
        resolved_region = aws_region_map[region]
        return resolved_region
    except KeyError:
        print('ERROR: Region \'' + region + '\' does not exist!')
        exit(1)


# pull prices of EBS volume types relevant to the region specified 
def build_price_dict(auth, region):
    # EBS code to name is added since "pricing" endpoint does not understand EBS codes (same situation as regions)
    ebs_name_map = {
        'standard': 'Magnetic',
        'gp2': 'General Purpose',
        'io1': 'Provisioned IOPS',
        'st1': 'Throughput Optimized HDD',
        'sc1': 'Cold HDD'
    }

    price_dict = ebs_name_map

    # query get_products with a filter to loops through all EBS types in one specified region
    for ebs_code in ebs_name_map:
        response = auth.get_products(
            ServiceCode='AmazonEC2',
            Filters=[{
                'Type': 'TERM_MATCH',
                'Field': 'volumeType',
                'Value': ebs_name_map[ebs_code]
            }, 
            {
                'Type': 'TERM_MATCH',
                'Field': 'location',
                'Value': resolve_region(region)
            }])

        # magic to get through complex dict returned from the get_products api to get to the price value
        for result in response['PriceList']:
            json_result = json.loads(result)
            for json_result_level_1 in json_result['terms'][
                    'OnDemand'].values():
                for json_result_level_2 in json_result_level_1[
                        'priceDimensions'].values():
                    for price_value in json_result_level_2[
                            'pricePerUnit'].values():
                        continue
        # fill in the dictionary with prices pulled from the get_products api
        price_dict[ebs_code] = float(price_value)
    return price_dict


# function to calculate prices of each individual EBS type based on price dictionary returned from get_products api
def calculate_prices(size_dict, price_dict):
    price_per_ebs_type = {}
    for ebs_type in size_dict:
        price_per_ebs_type[ebs_type] = round(
            size_dict[ebs_type] * price_dict[ebs_type])
    return price_per_ebs_type


# small function to add up all EBS prices together to create a total
def calculate_total_ebs_price(price_dict):
    total_price = 0
    for price in price_dict.values():
        total_price = total_price + price
    return total_price


# crete tables from prices and storage sizes obtained for each EBS type (only triggered in verbose mode)
def create_table(price_data, size_data):
    # create a table for prices
    price_table = BeautifulTable()
    price_table.column_headers = ["type", "price"]
    for row in price_data.items():
        price_table.append_row([row[0], '$' + str(row[1])])

    # create a table for EBS sizes
    size_table = BeautifulTable()
    size_table.column_headers = ["type", "size"]
    for row in size_data.items():
        size_table.append_row([row[0], str(row[1]) + ' GiB'])
    return price_table, size_table


# print out results depending on verbosity
def print_output(ebs_sizes, unused_ebs_sizes, ebs_prices, unused_ebs_prices,
                 unused_volume_ids, verbose_mode):
    if verbose_mode:
        # if verbose mode is on print price and storage amount tables 
        price_table, size_table = create_table(ebs_prices, ebs_sizes)
        unused_price_table, unused_size_table = create_table(
            unused_ebs_prices, unused_ebs_sizes)

        print('\n')
        print(bcolors.WARNING + "Total expenditures per EBS type" +
              bcolors.ENDC)
        print(price_table)
        print('\n')
        print(bcolors.WARNING + "Total sizes per EBS type" + bcolors.ENDC)
        print(size_table)
        print('\n')

        # if any unused volumes were detected print unused volume ids and pricing and storage amount tables
        if not unused_volume_ids == []:
            print(bcolors.FAIL + "There are unused EBS volumes" + bcolors.ENDC)
            print(unused_price_table)
            print('\n')
            print(bcolors.FAIL + "Total sizes per EBS type" + bcolors.ENDC)
            print(unused_size_table)
            print('\n')
            print(bcolors.FAIL + "Here are unused volume IDs" + bcolors.ENDC)
            print('------------------------')
            for volume_id in unused_volume_ids:
                print(volume_id)
    else:
        # if verbose mode is not enabled, only print price sum of all EBS volumes
        print(bcolors.WARNING + 'total: ' + bcolors.ENDC + '$' +
              str(calculate_total_ebs_price(ebs_prices)))
        # if unused EBS volumes are detected print price sum of all unused EBS volumes
        if not unused_volume_ids == []:
            print(bcolors.FAIL + 'unused:' + bcolors.ENDC + '$' +
                  str(calculate_total_ebs_price(unused_ebs_prices)))


def main():
    # get credentials, region and verbose mode setting from arguments
    aws_region, credentials, verbose = resolve_arguments()
    # create two sessions, one for auth to AWS API and one to auth to pricing API
    ebs_auth, price_auth = authenticate(aws_region, credentials)
    # obtain all EBS volumes for specified region with AWS API auth
    all_ebs_volumes = get_all_volumes(ebs_auth)
    # extract and add up all EBS volume sizes based on EBS volume type
    ebs_sizes_dict = extract_and_calculate_size(all_ebs_volumes)
    # extract and add up all unused EBS volume sizes based on EBS volume type
    unused_ebs_volumes, unused_ebs_sizes_dict = determine_unused_ebs(
        all_ebs_volumes)
    # fetch pricing information from pricing API using pricing auth
    ebs_price_dict = build_price_dict(price_auth, aws_region)
    # calculate prices for each EBS volume type based on calculated EBS sizes
    ebs_prices = calculate_prices(ebs_sizes_dict, ebs_price_dict)
    # calculate prices for each unused EBS volume type based on calculated unused EBS sizes
    unused_prices = calculate_prices(unused_ebs_sizes_dict, ebs_price_dict)
    # pring output based on verbosity
    print_output(ebs_sizes_dict, unused_ebs_sizes_dict, ebs_prices,
                 unused_prices, unused_ebs_volumes, verbose)


if __name__ == "__main__":
    main()
