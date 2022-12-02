import os
import time
import pytz
import datetime
import boto3
import feedparser
from mastodon import Mastodon
from boto3 import DynamoDB


def determine_if_posted(ddb_client: DynamoDB.Client, id:str) -> bool:

    """checks if the article has been posted to mastodon

    Arguments:
        ddb_client {DynamoDB.Client} -- boto3 dynamodb client
        id {str} -- the id of the article

    Returns:
        bool: True if the article has been posted, False if not
    """

    result = ddb_client.get_item(
        TableName=os.environ['DYNAMODB_TABLE_NAME'],
        Key={
            "id": {
                "S": id
            }
        })

    if "Item" in result:
        return True
    else:
        return False


def mark_as_posted(ddb_client:boto3.DynamoDB.Client, id:str)->bool:

    """Saves the ID of the article to dynamodb
    Note: If two rss feeds have the same ID, then the ID will be duplicated,
    and thus only one of the rss feeds will be saved in dynamo

    Arguments:
        ddb_client {boto3.DynamoDB.Client} -- boto3 dynamodb client
        id {str} -- the id of the article
    
    Returns:
        bool: True if the article was posted to mastodon, False if not
    """

    result = ddb_client.put_item(
        TableName=os.environ['DYNAMODB_TABLE_NAME'],
        Item={
            "id": {
                "S": id
            }}
    )

    # check for errors
    if "ResponseMetadata" in result:
        if "HTTPStatusCode" in result["ResponseMetadata"]:
            if result["ResponseMetadata"]["HTTPStatusCode"] == 200:
                return True
            else:
                return False
        else:
            return False
    else:
        return False


def post_to_mastodon(mastodon_client:Mastodon, entry:dict)->bool:

    """Posts the article to mastodon

    Arguments:
        mastodon_client {Mastodon} -- the mastodon client
        entry {dict} -- the entry from the rss feed

    Raises:
        Exception: if the article was not posted to mastodon

    Returns:
        bool: True if the article was posted to mastodon, False if not
    """

    entry_title = entry["title"]
    entry_url = entry["link"]

    # create new mastodon post
    try:

        mastodon_client.toot(f"{entry_title}\n\n{entry_url}")

        return True

    except Exception as e:
        print("error posting to mastodon: ", e, " for entry: ", entry)
        return False


def is_article_published_today(entry: dict)->bool:
    
    
    """Checks if the article was published today

    Arguments:
        entry {dict} -- the entry from the rss feed

    Returns:
        bool: True if the article was published today, False if not
    """
    
    published_parsed = entry["published_parsed"]
    published_month = published_parsed.tm_mon
    published_day = published_parsed.tm_mday
  
    nyc_datetime = datetime.datetime.now(pytz.timezone('US/Eastern'))
    
    todays_nyc_time_month = nyc_datetime.month
    todays_nyc_time_day = nyc_datetime.day
    
    if published_month == todays_nyc_time_month and published_day == todays_nyc_time_day:
        return True
    else: 
        return False
    

def check_and_post(entry:dict, mastodon_client:Mastodon, ddb_client:boto3.DynamoDB.Client)->None:

    """Checks if the article has been posted to mastodon, and if not, posts it
    
    Arguments:
        entry {dict} -- the entry from the rss feed
        mastodon_client {Mastodon} -- the mastodon client
        ddb_client {boto3.DynamoDB.Client} -- boto3 dynamodb client
        
    Returns:
        None
    
    """    

    print("checking entry: ", entry['title'])
    if determine_if_posted(ddb_client, entry["id"]):
        print("already posted: ", entry["title"])
        return
    else:
        print("not posted: ", entry["title"])
        
    if is_article_published_today(entry):
        print("article published today: ", entry["title"])
    else:
        print("article is not published today, posting to mastodon")
        return
    
    was_posted = post_to_mastodon(mastodon_client, entry)
    
    print("was posted: ", was_posted)
    
    if was_posted:
        print("marking as posted: ", entry["title"])
        mark_as_posted(ddb_client, entry["id"])
        print("marked as posted: ", entry["title"])
    else:
        print("error posting to mastodon: ", entry["title"])


def collect_rss_feed(feed: dict, ddb_client:boto3.DynamoDB.Client)->None:

    """ Collects the rss feed and posts the articles to mastodon
    
    Arguments:
        feed {dict} -- the rss feed
        ddb_client {boto3.DynamoDB.Client} -- boto3 dynamodb client
        
    Returns:
        None
    
    """    
    
    ## IMPORTANT NOTE: You should save the credentials
    ## created by this next function somewhere,
    ## and then use them to log in again later.
    
    ## If you are using AWS, a good place to put them is in AWS Secrets Manager,
    ## parameter store, or dynamodb
    
    ## If you implement this code without storing the credentials,
    ## your API token table on your Mastodon instance will fill up with
    ## tokens that you will never use again, and you will have to manually
    ## delete them from the database
    
    app_creds = Mastodon.create_app(
        'newsbot',
        scopes=['read', 'write', 'follow'],
        api_base_url=os.environ['MASTODON_INSTANCE_URL'],
    )

    # generate an api token
    api = Mastodon(app_creds[0], app_creds[1], api_base_url=os.environ['BASE_API_URL'])

    # create the login token
    login_creds = api.log_in(feed['account_name'], feed['password'], scopes=["read", "write"])

    print("creating mastodon client")
    mastodon_client = Mastodon(client_id=app_creds[0],client_secret=app_creds[1],access_token=login_creds,api_base_url=os.environ['MASTODON_INSTANCE_URL'])

    print("logging in to mastodon as: ", feed["account_name"], " with password ", feed["password"])

    rss_uri = feed["rss"]

    print("parsing rss feed: ", rss_uri)

    # parse the rss feed via feedparser
    parsed_feed = feedparser.parse(rss_uri)
    
    # collect the entries from the rssd feed
    parsed_feed_entries = parsed_feed["entries"]

    # for each entry, check if it has been posted to mastodon
    for entry in parsed_feed_entries:
        check_and_post(entry, mastodon_client, ddb_client)


def lambda_handler(event, context)->None:

    """Lambda handler
    
    Arguments:
        event {dict} -- the event
        context {dict} -- the context
        
    Returns:
        None
    
    """    

    ## Note: environment variables needs to be set in lambda, docker container or CLI

    # Check if we have our environment variables set
    if "RSS_FEED_URL" not in os.environ:
        raise("RSS_FEED_URL environment variable not set")

    if "MSTN_ACCOUNT_EMAIL" not in os.environ:
        raise("MSTN_ACCOUNT_EMAIL environment variable not set")

    if "MSTN_PASSWORD" not in os.environ:
        raise("MSTN_PASSWORD environment variable not set")

    if "DDB_TABLE_NAME" not in os.environ:
        raise("DDB_TABLE_NAME environment variable not set")

    if "DDB_REGION" not in os.environ:
        raise("DDB_REGION environment variable not set")

    if 'BASE_API_URL' not in os.environ:
        raise("BASE_API_URL environment variable not set")

    if 'MASTODON_INSTANCE_URL' not in os.environ:
        raise("MASTODON_INSTANCE_URL environment variable not set")

    print("starting lambda handler")

    feed = {
        "account_name" : os.environ['MSTN_ACCOUNT_EMAIL'],
        "password": os.environ['MSTN_PASSWORD'],
        "rss_feed": os.environ['RSS_FEED_URL'],
    }

    print("collecting rss feed: ", feed["rss_feed"])

    print("setting up boto3 dynamodb client")

    ddb_client = boto3.client('dynamodb',region_name=os.environ['DDB_REGION'])

    collect_rss_feed(feed, ddb_client)
