# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

from requests import get
from bs4 import BeautifulSoup


def split_on_first(string, char):
    """
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
        #splitted = [li.split(':') for li in lis[1:]]
        
        # SAVE INFORMATION IN DICTIONARY
        data = {key.strip():value.strip() for key, value in splitted}
    
    # IF BOX OF FACTS DOES NOT EXIST
    else:
        data = dict()
        title = soup.find('h1', attrs = {'class':'anmeldelse entry-title'}).text.strip()

    data['Tittel'] = title
    data['Anmeldelse'] = review
    data['Anmeldt_del'] = part_reviewed

    return data


def main():
    
    working_url = r'http://p3.no/filmpolitiet/category/tv-serieanmeldelser/terningkast-TERNINGSKAST-tv-serieanmeldelser/page/SIDENUMMER/'
    
    collection = []
    
    # COMPLETE 1 OF 2 FILL-INS IN THE WORKING URL
    for die in range(1,7):
        die_url = working_url.replace('TERNINGSKAST', str(die))
        
        # COMPLETE 2 0F 2 FILL-INS IN THE WORKING URL
        for page in range(1,99):
            url = die_url.replace('SIDENUMMER',str(page))
            
            soup = BeautifulSoup(get(url).text, 'lxml')
            
            # CHECK IF WE HAVE MOVED PAST THE FINAL PAGE, BY GETTING ERROR404 
            status = soup.find('body', attrs = {'class':'error404'})
            if status is not None:
                break
            
            #print('*'*100)
            print(url)
            #print('*'*100)
    
            # GET ALL MEDIA (MOVIES/SERIES/GAMES) ON PAGE
            media = soup.find_all('article')

            for article in media:
    
                # GET ARTICLE URL FOR RETRIEVING FACTS
                url = article.find('h2').a['href']
                #print(url)

                # GET FACTS
                data = get_facts(url)
            
                collection.append(data)
               
                #for key,value in data.items():
                #    print('>>>',key,value)
                
                #print('-'*100)



    for media in collection:
        print(media['Tittel'])
        print(media['Anmeldt_del'])
        print('----------------------------------------------------')
    
    
if __name__ == '__main__':
    main()

 