import os.path
import requests
import lxml.html as html
import re
import logging
import csv
from common import config
from requests.exceptions import HTTPError
from urllib3.exceptions import MaxRetryError

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
is_well_formed_link = re.compile(r'^https?://.+/.+$')
is_root_path = re.compile(r'^/.+$')
is_pdf = re.compile(r'^https?://.+\.pdf$')
config = config
data = {}

# Test para escapar comillas dobles.
def _replacer(objs):
    news_object = []
    for obj in objs:
        obj = obj.replace('\"', '')
        obj = obj.replace('\xa0', '')
        obj = obj.replace('\n', '')
        obj = obj.replace('\t', '')
        obj = obj.replace('\r', '')
        obj = obj.replace('-', ' ')
        news_object.append(obj)
    return news_object

# Test para construir enlaces.
def _build_link(host, link):
    ''' Function that builds properly a url '''
    if is_well_formed_link.match(link):
        return link
    elif is_root_path.match(link):
        return f'{host}{link}'
    else:
        return f'{host}/{link}'

def _recover_articles_urls(file):
    url = []
    file = open(file, 'r')
    for line in file:
        link = line.rstrip('\\n')
        link = link.replace('\n', '')
        url.append(link)
    file.close()
    return url

# Test para verificar que sea distinto a none
def _categories_urls_extraction(host, iterator):
    ''' Function that returns two list one for the category links and the other for the category names '''
    logger.info(f'Extracting category list for {host}')
    # Variables definition
    categories_links = config()['news_sites'][iterator]['categories_links']
    links_categories = []
    
    try:
        # Requesting info from the host
        news_page = requests.get(host)
        if news_page.status_code == 200:
            home = news_page.content.decode('utf-8')
            parsed = html.fromstring(home)
            # Extracting the links and the names for each category
            categories_tmp = parsed.xpath(categories_links)
            for link in categories_tmp:
                links_categories.append(_build_link(host, link))
        else:
            # In case if the server is down
            raise ValueError(f'Error {news_page.status_code}')
            logger.info(f'Server error: {news_page.status_code}')
    except ValueError as e:
        logger.info(f'Error scraping {host}')
    return list(set(links_categories))

# Test para verificar que no sea none
def _articles_urls_extraction(host, category_list, iterator):
    ''' Function that extracts the urls for each category, and returns it in a list. '''
    # Variables definition
    article_link = config()['news_sites'][iterator]['articles']
    article_list = []

    for category in category_list:
        try:
            logger.info(f'Extracting article links for {category}')
            # Requesting info from the categories list
            category_page = requests.get(category)
            if category_page.status_code == 200:
                home = category_page.content.decode('utf-8')
                parsed = html.fromstring(home)
                # Extracting the article links for each category
                article_list_tmp = parsed.xpath(article_link)
                for article in article_list_tmp:
                    if is_pdf.match(_build_link(host, article)):
                        continue
                    else:
                        article_list.append(_build_link(host, article))
                    
            else:
                # In case if the server is down
                raise ValueError(f'Error {category_page.status_code}')
                logger.info(f'Server error: {category_page.status_code}')
        except ValueError as e:
            logger.info(f'Error scraping {host}')
        
    return list(set(article_list))

# Test para verificar titulo, contenido, fecha, url y categoría
def _articles_and_categories_extraction(host, article_url, iterator):
    ''' Function that extracts the articles for each category, and returns it in a dictionary. '''
    # Variables definition
    title_query = config()['news_sites'][iterator]['queries']['title']
    subtitle_query = config()['news_sites'][iterator]['queries']['subtitle']
    body_query = config()['news_sites'][iterator]['queries']['content']
    images_query = config()['news_sites'][iterator]['queries']['images']
    category_long_query = config()['news_sites'][iterator]['queries']['category_long']
    tags_query = config()['news_sites'][iterator]['queries']['tags']
    author_query = config()['news_sites'][iterator]['queries']['author']
    publication_date_query = config()['news_sites'][iterator]['queries']['publication_date']
    categories_query = config()['news_sites'][iterator]['queries']['categories']
    data = {}
    try:
        logger.info(f'Extracting article and category content from {article_url}')
        # Requesting info from the categories list
        article_page = requests.get(article_url)
        if article_page.status_code == 200:
            home = article_page.content.decode('utf-8')
            parsed = html.fromstring(home)
            # Extracting the content for each article
            try:
                title = parsed.xpath(title_query)
                title = _replacer(title)
            except ValueError as e:
                logger.warning(f'there is no title')
                title = None
            try:
                subtitle = parsed.xpath(subtitle_query)
                subtitle = _replacer(subtitle)
            except ValueError as e:
                logger.warning('There is no subtitle')
                subtitle = None
            try:
                body = parsed.xpath(body_query)
                body = _replacer(body)
            except ValueError as e:
                logger.warning(f'there is no body')
                body = None
            try:
                category_long = parsed.xpath(category_long_query)
                category_long = _replacer(category_long)
            except ValueError as e:
                logger.warning(f'there is no category')
                category_long = None
            try:
                tags = parsed.xpath(tags_query)
                tags = _replacer(tags)
            except ValueError as e:
                logger.warning(f'there is no tags')
                tags = None
            try:
                author = parsed.xpath(author_query)
                author = _replacer(author)
            except ValueError as e:
                logger.warning(f'there is no author')
                author = None
            try:
                categories = parsed.xpath(categories_query)
                categories = _replacer(categories)
            except ValueError as e:
                logger.warning(f'there are no categories')
                categories = None
            try:
                images = parsed.xpath(images_query)
                images = _replacer(images)
            except ValueError as e:
                logger.warning(f'there are no images')
                images = None
            try:
                publication_date = parsed.xpath(publication_date_query)
                publication_date = _replacer(publication_date)
            except ValueError as e:
                logger.warning(f'there is no publication date')
                publication_date = None
            
            data = {
                'title': title,
                'subtitle': subtitle,
                'body': body,
                'images': parsed.xpath(images_query),
                'category_long': category_long,
                'tags': tags,
                'author': author,
                'publication_date': parsed.xpath(publication_date_query),
                'news_url': article_url,
                'host': host
            }
            category = "".join(categories)
        else:
            raise ValueError(f'Error.')
            logger.info(f'{article_url}: {article_page.status_code}')
    except (HTTPError, MaxRetryError) as e:
        logger.warning('Error while fetching article', exc_info=False)
    
    return data, category.capitalize()


if __name__ == '__main__':
    data['categories'] = []
    data['articles'] = []
    articles = []
    articles_recovered = []
    categories_recovered = []
    if os.path.isfile('urls.txt'):
        articles_recovered = _recover_articles_urls('urls.txt')
    if os.path.isfile('categories.txt'):
        categories_recovered = _recover_articles_urls('categories.txt')
    articles_to_scrape = []
    categories = []
    

    for i in range(7):
        host = config()['news_sites'][i]['url']
        logger.info(f'Begining scraper for {host}')
        categories_urls = _categories_urls_extraction(host, i)
        articles_links = _articles_urls_extraction(host, categories_urls, i)
        for article in articles_links:
            if article not in articles_recovered:
                articles_to_scrape.append(article)
                articles, category = _articles_and_categories_extraction(host, article, i)
                data['articles'].append(articles)
                categories.append(category)
    categories = list(set(categories))
    for category in categories:
            if category not in categories_recovered:
                data['categories'].append({'categories':category})

    with open('articles.csv', 'w+') as f:
        fieldnames = ['title', 'subtitle', 'body', 'images', 'category_long', 'tags', 'author','publication_date', 'news_url', 'host']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data['articles'])
        f.close()

    with open('categories.csv', 'w+') as f:
        writer = csv.DictWriter(f, fieldnames=['categories'])
        writer.writeheader()
        writer.writerows(data['categories'])

    with open('urls.txt', 'a+') as f:
        for article in articles_to_scrape:
            f.write(article + '\n')
        f.close
    
    with open('categories.txt', 'a+') as f:
        for category in categories:
            f.write(category + '\n')
        f.close