from flask import Flask, request
from dotenv import load_dotenv
from regex import R
load_dotenv()
import os
import tweepy
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')
nltk.download('wordnet')
stop_words = stopwords.words('english')
from urllib.parse import unquote

from textblob import TextBlob, Word
from profanity_check import predict

app = Flask(__name__)
client = tweepy.Client(bearer_token = os.getenv("BEARER_TOKEN"), wait_on_rate_limit=True)

def preprocess_tweets(tweet):
    processed_tweet = tweet
    processed_tweet.replace('[^\w\s]', '')
    processed_tweet = " ".join(word for word in processed_tweet.split() if word not in stop_words)
    # processed_tweet = " ".join(Word(word).lemmatize() for word in processed_tweet.split())
    return(processed_tweet)


@app.route("/handle")
def userTimeline():
    username = unquote(request.args.get('username'))
    data = client.get_user(
            username=username, 
            user_fields = 
            ['profile_image_url',
            'protected',
            'created_at',
            'description',
            'location',
            'public_metrics']).data
    
    if not data:
        return {"type": "handle",
            "error" : 
        "There is no twitter account with this handle",
        "author": False,
        "tweets": False}

    user_id = data.id

    author = {"type": "handle",
        "name": data.name,
        "username": data.username,
        "image": data.profile_image_url
    }

    if data.protected:
        return{"type": "handle",
            "error": 
        "This account is private, Social Scout can only scan public accounts",
        "author": author,
        "tweets": False}

    Alltweets = tweepy.Paginator(
            client.get_users_tweets, 
            max_results = 100,
            id = user_id, 
            tweet_fields = 
                ["text", 
                "created_at", 
                "public_metrics"]).flatten()

    tweets = []
    avgSentiment = 0
    avgPopularity = 0
    count = 0
    sentimentGraph = []

    for tweet in Alltweets:
        count +=1 
        ptweet = preprocess_tweets(tweet.text)
        sentiment = TextBlob(ptweet).sentiment[0]
        avgSentiment = (avgSentiment + sentiment)/ count
        popularity = tweet.public_metrics["like_count"]
        avgPopularity = (avgPopularity+popularity)/count
        date = tweet.created_at.strftime("%d %b, %Y")
        sentimentGraph.append(
        {"sentiment": popularity,
        # "popularity": popularity,
        "date": date})


        if predict([tweet.text])[0] == 1:
            tweetInfo = {
                "tweet": tweet.text,
                "id": tweet.id,
                "permalink": "https://twitter.com/twitter/statuses/" + str(tweet.id),
                "time": tweet.created_at,
                "engagement": {
                    "replies": tweet.public_metrics["reply_count"],
                    "retweets": tweet.public_metrics["retweet_count"],
                    "likes": tweet.public_metrics["like_count"]
                }
            }
            tweets.append(tweetInfo)

    if not tweets:
        return{"type": "handle",
            "error": 
            "This user has no tweets",
            "author": author,
            "tweets": False}

    sentimentGraph.reverse()

    return {"type": "handle",
            "error": False,
            "author": author,
            "tweets": tweets,
            "sentiment": sentimentGraph}
    

@app.route("/query")
def searchTimeline():
    query = unquote(request.args.get('search'))
    print(query)
    Alltweets = tweepy.Paginator(
                    client.search_recent_tweets, 
                    max_results = 100,
                    query = query,
                    tweet_fields = 
                            ["text", 
                            "created_at", 
                            "public_metrics",],
                    # user_fields = 
                    #         [
                    #         'username',
                    #         'name',
                    #         'profile_image_url'],
                    expansions='author_id'
                    ).flatten(limit = 1000)

    tweets = []
    avgSentiment = 0
    i = 0
    

    for tweet in Alltweets:
        i+=1
        if i <= 5:

            user = client.get_user(
                    id = tweet.author_id, 
                    user_fields = 
                    ['profile_image_url']).data

            author = {
                "username": user.username,
                "name": user.name,
                "image": user.profile_image_url
            }

            # author = {
            #         "username": "jeff",
            #         "name": "jeff",
            #         "image": ""
            # }

            tweetInfo = {
                    "tweet": tweet.text,
                    "author": author,
                    "id": tweet.id,
                    "permalink": "https://twitter.com/twitter/statuses/" + str(tweet.id),
                    "time": tweet.created_at,
                    "engagement": {
                        "replies": tweet.public_metrics["reply_count"],
                        "retweets": tweet.public_metrics["retweet_count"],
                        "likes": tweet.public_metrics["like_count"]
                    }
                }
            tweets.append(tweetInfo)

    if not tweets:
        return{"type": "query",
            "error": "No tweets for this query",
            "tweets": False}

    return {"type": "query",
            "error": False,
            "tweets": tweets}



if __name__ == "__main__":
    app.run(debug=True)