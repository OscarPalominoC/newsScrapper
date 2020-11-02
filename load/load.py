import pymongo
import logging
import pandas as pd
import re
import numpy as np
from client import client
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

db = client['news_db']
logger.info(f'Conecting to DB {db.name}.')
data_articles = []
data_categories = []


def clean_body(df):
    ''' This function ensure that the data type send to the DB is an array, as the df readed transform all the csv into string type. '''
    logger.info('Cleaning articles body.')
    df['body'] = df['body'].str.replace("',", "---")
    df['body'] = df['body'].str.replace("'", '')
    df['body'] = df['body'].str.replace("[", '')
    df['body'] = df['body'].str.replace("]", '')
    df['body'] = df['body'].str.split("---")
    
    return df

def clean_tags(df):
    ''' This function ensure that the data type send to the DB is an array, as the df readed transform all the csv into string type. '''
    logger.info('Cleaning articles tags.')
    df['tags'] = df['tags'].fillna(method = 'bfill')
    df['tags'] = df['tags'].str.replace('\',', '---')
    df['tags'] = df['tags'].str.replace('[', '')
    df['tags'] = df['tags'].str.replace('\'', '')
    df['tags'] = df['tags'].str.replace(']', '')
    df['tags'] = df['tags'].str.split("---")
            
    return df


def clean_images_list(df):
    ''' This function ensure that the data type send to the DB is an array, as the df readed transform all the csv into string type. '''
    logger.info('Cleaning articles images.')
    df['images'] = df['images'].fillna('')
    
    for img in range(len(df['images'])):
        df['images'][img] = df['images'][img].split(',')
        for item in range(len(df['images'][img])):
            df['images'][img][item] = df['images'][img][item].replace('\'', "")
            
    return df


def cleaning_vanguardia_images(df_articles):
    ''' This function ensure that the images from vanguardia newspaper has the correct form of an url, due to the scraper it returns the first two characters '//'. '''
    for df in range(len(df_articles)):
        if df_articles['host'][df] == 'https://www.vanguardia.com':
            for url in range(len(df_articles['images'][df])):
                df_articles['images'][df][url] = "".join(re.findall(r'[\w]{3}\.[\w\-\.\/]+\.[\w]{3}', df_articles['images'][df][url]))
    return df_articles


def clean_empty_spaces(df):
    ''' This function ensures that the data sent to the DB has no empty spaces, in order to not send an NA. '''
    logger.info('Cleaning empty spaces.')
    df['subtitle'] = df['subtitle'].fillna('')
    df['category_long'] = df['category_long'].fillna(method = 'bfill')
    df['author'].fillna(df['host'], inplace = True)
    
    return df

def string_to_datetime(df):
    ''' This function ensores that the data type of the publication_date is datetime type. '''
    logger.info('Cleaning datetime.')
    df['publication_date'] = pd.to_datetime(df['publication_date'])
    return df

def main():
    df_articles = pd.read_csv('clean_articles.csv')
    df_articles = clean_tags(df_articles)
    df_articles = clean_images_list(df_articles)
    df_articles = cleaning_vanguardia_images(df_articles)
    df_articles = clean_empty_spaces(df_articles)
    df_articles = clean_body(df_articles)
    df_articles = string_to_datetime(df_articles)
    df_categories = pd.read_csv('clean_categories.csv')

    logger.info(f'Accessing to collections.')
    collection_articles = db['news']
    collection_categories = db['categories']

    logger.info(f'Parsing article data.')
    for article in range(len(df_articles)):
        data_articles.append({
            'title': df_articles['title'][article],
            'subtitle': df_articles['subtitle'][article],
            'images': df_articles['images'][article],
            'body': df_articles['body'][article],
            'tags': df_articles['tags'][article],
            'author': df_articles['author'][article],
            'host': df_articles['host'][article],
            'news_url': df_articles['news_url'][article],
            'publication_date': df_articles['publication_date'][article],
            'category': df_articles['category_long'][article]
        })
    logger.info(f'Parsing Category data.')
    for category in range(len(df_categories)):
        data_categories.append({'categories':df_categories['categories'][category]})


    logger.info(f'Attempting to save data into database.')
    if data_articles:
        collection_articles.insert_many(data_articles)
        logger.info(f'{len(data_articles)} articles inserted into database.')
    if data_categories:
        collection_categories.insert_many(data_categories)
        logger.info(f'{len(data_categories)} categories inserted into database.')

    logger.info(f'Closing database {db.name}.')

    client.close()

if __name__ == "__main__":
    main()