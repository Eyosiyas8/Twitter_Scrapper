from elasticsearch import Elasticsearch, helpers
from profile_scraper import *
from tweet_scraper import *
from time import sleep
import tqdm
from pymongo import MongoClient
from datetime import datetime

basedir = os.path.dirname(os.path.abspath(__file__))
# Initializing mongo db client
db_connection = os.environ.get('DB_CONNECTION')
db_client = 'twitter_data'
db_collection = 'twitter'
client = MongoClient(db_connection)
print(db_connection)
db = client[db_client]
collection = db[db_collection]

# Initializing different variables
tweet_ids = set()
csv_row1 = []
data = []
es=Elasticsearch([{'host':'localhost:9200','port':9200,'scheme':"http"}])

# Generates the sentiment for a given tweet
key_word = os.path.join(basedir, '../Authentication/words.txt')


def sentiment_output(tweet):
    with open(key_word, "r",
              encoding='utf-8') as file:
        lines = file.readlines()
        lines = [line.rstrip() for line in lines]

        count = 0
        sentiment = ''
        for i in range(len(lines)):
            keyWord = lines[i]
            if keyWord in tweet.lower():
                print(keyWord + str(count))
                count += 1
        if count == 1:
            sentiment = 'low negative'
        elif count == 2:
            sentiment = 'negative'
        elif count == 3:
            sentiment = 'very negative'
        elif count >= 4:
            sentiment = 'extremely negative'
        else:
            sentiment = 'Unremarkable'

    return sentiment


# Structuring the data generated from the csv files to be inserted to the database
def data_structure(csv_file, csv_file2, csv_file3):
    with open(csv_file, 'r', encoding='utf-8') as f1, open(csv_file2, 'r', encoding='utf-8') as f2, open(csv_file3, 'r',
                                                                                                         encoding='utf-8') as f3:
        reader1 = csv.DictReader(f1)
        reader2 = csv.DictReader(f2)
        reader3 = csv.DictReader(f3)
        csv_row1 = []
        for row1 in reader1:
            row1['Fullname'] = row1['Fullname']
            row1['UserName'] = row1['UserName']
            row1['Description'] = row1['Description']
            row1['Tweets'] = row1['Tweets']
            row1['Number of Followings'] = row1['Number of Followings']
            row1['Number of Followers'] = row1['Number of Followers']
            row1['Joined_date'] = row1['Joined_date']
            csv_rows = []
            for row2 in reader2:
                tweet = row2['tweet']
                row2['id'] = row2['id']
                row2['conversation_id'] = row2['conversation_id']
                row2['username'] = row2['username']
                row2['name'] = row2['name']
                row2['tweet'] = row2['tweet']
                row2['mentions'] = row2['mentions']
                row2['photos'] = row2['photos']
                row2['replies_count'] = row2['replies_count']
                row2['retweets_count'] = row2['retweets_count']
                row2['likes_count'] = row2['likes_count']
                row2['hashtags'] = row2['hashtags']
                csv_row = []
                for row3 in reader3:
                    reply = row3['tweet']
                    if row2['id'] == row3['conversation_id']:
                        data = {
                            'id': row3['id'],
                            'conversation_id': row3['conversation_id'],
                            'username': row3['username'],
                            'name': row3['name'],
                            'reply': row3['tweet'],
                            'mentions': row3['mentions'],
                            'photos': row3['photos'],
                            'replies_count': row3['replies_count'],
                            'retweets_count': row3['retweets_count'],
                            'likes_count': row3['likes_count'],
                            'hashtags': row3['hashtags'],
                            'sentiment': sentiment_output(reply)

                        }
                        tweets_id = ''.join(row3['tweet'])
                        csv_row.append(data)
                tweets_id = ''.join(row2['tweet'])
                if tweets_id not in tweet_ids:
                    tweet_ids.add(tweets_id)
                    csv_rows.append(
                        {'sentiment': sentiment_output(tweet), 'id': row2['id'],
                         'conversation_id': row2['conversation_id'], 'username': row2['username'],
                         'name': row2['name'], 'tweet': row2['tweet'], 'mentions': row2['mentions'],
                         'photos': row2['photos'], 'replies_count': row2['replies_count'],
                         'retweets_count': row2['retweets_count'], 'likes_count': row2['likes_count'],
                         'hashtags': row2['hashtags'], 'replies': csv_row})
                f3.seek(0)
            f2.seek(0)
            csv_row1.append({
                'Date_of_Scraping': datetime.today(),
                'Fullname': row1['Fullname'],
                'UserName': row1['UserName'],
                'Description': row1['Description'],
                'Tweets': row1['Tweets'],
                'Number of Followings': row1['Number of Followings'],
                'Number of Followers': row1['Number of Followers'],
                'Joined_date': row1['Joined_date'],
                'tweets': csv_rows})
            print('almost')

    with open(csv_file2, encoding='utf-8') as file1, open(csv_file3, encoding='utf-8') as file2:
        read1 = csv.DictReader(file1)
        read2 = csv.DictReader(file2)
        helpers.bulk(es, read1, index="twitter")
        helpers.bulk(es, read2, index="twitter")
    collection.insert_many(csv_row1)
    print(csv_row1)


# Initialize the scraping process
acc_name = os.path.join(basedir, '../Authentication/Document.txt')
with open(acc_name, "r", encoding='utf-8') as file:
    lines = file.readlines()
    lines = [line.rstrip() for line in lines]
    for i in tqdm.tqdm(range(len(lines))):
        sleep(0.1)
        username = lines[i]
        url = "https://twitter.com/%s" % username
        print("current session is {}".format(driver.session_id))
        driver.get(url)
        print(url)
        csv_file = os.path.join(basedir, '../csv_files/') + username + ".csv"
        profile_scraper(username, csv_file)
        print(csv_file)
        csv_file1 = os.path.join(basedir, '../csv_files/raw_dump_') + username + ".csv"
        csv_file2 = os.path.join(basedir, '../csv_files/parent_tweet_') + username + ".csv"
        csv_file3 = os.path.join(basedir, '../csv_files/reply_of_') + username + ".csv"
        try:
            os.remove(csv_file1)
            os.remove(csv_file2)
            os.remove(csv_file3)
        except:
            print('No Such File!')
        scrapper(username, csv_file1)
        try:
            filter_username(username, csv_file1, csv_file2)
            f=open(csv_file2, 'r+', encoding='utf-8')
            reader = csv.DictReader(f)
            lines=len(list(reader))
            while lines < 10:
                filter_username(username, csv_file1, csv_file2)
                f=open(csv_file2, 'r+', encoding='utf-8')
                reader = csv.DictReader(f)
                lines=len(list(reader))
                f.close()

            filter_replies(username, csv_file1, csv_file3)
            sleep(2)
            data_structure(csv_file, csv_file2, csv_file3)
        except Exception as e:
            stylize(e, colored.fg("grey_46"))
            continue
        sleep(1)
driver.close()
'''out_file = open("file.json", "w", encoding='utf-8')

json.dump(csv_row1, out_file, indent=6)

out_file.close()'''

time.sleep(5)
