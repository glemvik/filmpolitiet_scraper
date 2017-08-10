# -*- coding: utf-8 -*-

from requests import get
from bs4 import BeautifulSoup
import os
import logging
import dataset
import datetime
import pandas as pd

HTML_BASE = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
<!-- choose a theme file -->
<link rel="stylesheet" href="http://tablesorter.com/themes/blue/style.css">
<!-- load jQuery and tablesorter scripts -->
<script src="http://code.jquery.com/jquery-3.2.1.min.js" integrity="sha256-hwg4gsxgFZhOsEEamdOYGBf13FyQuiTwlAQgxVSNgt4=" crossorigin="anonymous"></script>
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery.tablesorter/2.28.15/js/jquery.tablesorter.js"></script>

  </head>
  <body>
    CONTENT
  </body>
  
  <script type="text/javascript">
  $(document).ready(function() 
    { 
        $("#myTable").tablesorter(); 
    } 
); 
    
    </script>
</html>
"""

# Set up constants and the like
time_format = '%Y-%m-%d-%H-%M-%S'
dir_of_file = os.path.abspath(os.path.dirname(__file__))
log_filename = os.path.join(dir_of_file, 'scraping_log.log')
logging.basicConfig(filename = log_filename,  level = logging.INFO)
DB_NAME = 'review_db'
connect_str = 'sqlite:///{}.db'.format(os.path.join(dir_of_file, DB_NAME))

def inftyrage(start = 1, step = 1):
    """
    Yield numbers to infty.
    """
    
    yield start
    while True:
        start += step
        yield start


def split_on_first(string, char):
    """
    Split on first occurence.
    """
    if char not in string:
        raise ValueError('character not in string')
    i = string.index(char)
    return string[:i], string[i+1:]


def get_facts(url):
    """
    Visits 'url' (which is an movie/series/game page) and returns all the facts
    describing the movie/series/game.
    """
    soup = BeautifulSoup(get(url).text, 'lxml')
    
    # GET REVIEW
    review = soup.find('div', attrs = {'class':'anmeldelse entry-excerpt'}).text.strip()
    part_reviewed = soup.find('h1', attrs = {'class':'anmeldelse entry-title'}).text.strip()
    
    # GET BOX OF FACTS
    facts = soup.find('div', attrs = {'class':'anmelderboks'})
    
    if facts is not None:
        lis = [li.text.strip() for li in facts.ul.find_all('li')]
    
        # RETRIEVE FACTS
        title = lis[0]
        splitted = [split_on_first(li,':') for li in lis[1:]]
        
        # SAVE INFORMATION IN DICTIONARY
        data = {key.strip().lower():value.strip() for key, value in splitted}
    
    # IF BOX OF FACTS DOES NOT EXIST
    else:
        data = dict()
        title = soup.find('h1', attrs = {'class':'anmeldelse entry-title'}).text.strip()

    data['Tittel'.lower()] = title
    data['Anmeldelse'.lower()] = review
    data['Anmeldt_del'.lower()] = part_reviewed

    return data

def reviews_urls(base_url):
    """
    Iterate over all dies,
    then iterate over all pages,
    and yield every (url, die) pair.
    """
    
    # COMPLETE 1 OF 2 FILL-INS IN THE WORKING URL
    for die in range(1, 7):
        
        # COMPLETE 2 0F 2 FILL-INS IN THE WORKING URL
        for page in inftyrage():
            url = base_url.format(die, page)
            
            soup = BeautifulSoup(get(url).text, 'lxml')
            
            # CHECK IF WE HAVE MOVED PAST THE FINAL PAGE, BY GETTING ERROR404 
            status = soup.find('body', attrs = {'class':'error404'})
            if status is not None:
                break
    
            # GET ALL MEDIA (MOVIES/SERIES/GAMES) ON PAGE
            media = soup.find_all('article')

            for article in media:
    
                # GET ARTICLE URL FOR RETRIEVING FACTS
                url = article.find('h2').a['href']
                yield url, die
            

def data_from_reviews(base_url):
    """
    Iterate over all dies,
    then iterate over all pages,
    go to every review
    and yield a dictionary with data.
    """

    # COMPLETE 1 OF 2 FILL-INS IN THE WORKING URL
    for die in range(1, 7):
        
        # COMPLETE 2 0F 2 FILL-INS IN THE WORKING URL
        for page in inftyrage():
            url = base_url.format(die, page)
            
            soup = BeautifulSoup(get(url).text, 'lxml')
            
            # CHECK IF WE HAVE MOVED PAST THE FINAL PAGE, BY GETTING ERROR404 
            status = soup.find('body', attrs = {'class':'error404'})
            if status is not None:
                break
    
            # GET ALL MEDIA (MOVIES/SERIES/GAMES) ON PAGE
            media = soup.find_all('article')

            for article in media:
    
                # GET ARTICLE URL FOR RETRIEVING FACTS
                url = article.find('h2').a['href']

                # GET FACTS
                data = get_facts(url)
                data['terningkast'] = die
                yield data


def update_db():
    """
    Update the data base.
    """

    series_url = r'http://p3.no/filmpolitiet/category/\
    tv-serieanmeldelser/terningkast-{}-tv-serieanmeldelser/page/{}/'
    
    movies_url = r'http://p3.no/filmpolitiet/category/\
    filmanmeldelser/terningkast-{}-filmanmeldelser/page/{}/'
    
    games_url = r'http://p3.no/filmpolitiet/category/\
    spillanmeldelser/terningkast-{}/page/{}/'
    
    base_urls = [('series', series_url), 
                 ('movies', movies_url), 
                 ('games', games_url)]
    
    
    
    db = dataset.connect(connect_str)
    
    for name, url in base_urls:
        db_table = db[name]
        for (url, die) in reviews_urls(url):
            
            found = db_table.find_one(url=url)
            if found is not None:
                continue

            #This url has never been seen
            data = get_facts(url)
            data['terningkast'] = die
            data['url'] = url
            db_table.insert(data)
            
            timestamp = datetime.datetime.now().strftime(time_format)
            log_msg = '{} - > {}'.format(timestamp, 'Added url' + str(url))
            logging.info(log_msg)

            
            
def db_to_html():
    
    html_dir = ''
    
    cols = dict()
    common = ['tittel','anmeldelse','terningkast']
    cols['series'] = ['sesong', 'sjanger', 'anmeldt_del', 
        'originaltittel', 'url'] + common
    cols['movies'] = ['regi','originaltittel','sjanger'] + common
    cols['games'] = ['utgiver','slippdato','plattformer'] +  common 
    
    
    db = dataset.connect(connect_str)
    
    for name in ['series', 'movies', 'games']:
        db_table = db[name]
        df = pd.DataFrame([row for row in db_table])

        args = {'classes':'tablesorter" id = "myTable', 'columns': cols[name]}
        html = HTML_BASE.replace('CONTENT', df.to_html(**args))
        
        filename = os.path.join(html_dir, '{}.html'.format(name))
        with open('{}.html'.format(name), 'w', encoding = 'utf-8') as file:
            file.write(html.replace('dataframe ', ''))
            timestamp = datetime.datetime.now().strftime(time_format)
            log_msg = '{} - > {}'.format(timestamp, 'Created file:' + filename)
            logging.info(log_msg)

if __name__ == '__main__':
    update_db()
    db_to_html()

 