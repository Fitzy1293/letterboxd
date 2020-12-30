#!/bin/env python3

'''
Letterboxd does not really have an API.
Test account:
    testfitzy1293
'''



import requests
import sys
import argparse
from bs4 import BeautifulSoup
from pprint import pprint
import json
from time import sleep, time

from rich.console import Console
from rich import print as rprint
from rich import pretty

parser = argparse.ArgumentParser(description='letterboxd args')
parser.add_argument('--user', '-u', dest='user', help='letterboxd.com user')
parser.add_argument('--reviews', '-r', dest='reviews', action="store_true", default=False, help='Gets reviews')
parser.add_argument('--testing', '-t', dest='testing', action='store_true', default=False, help='Testing flag - for development only')
parser.add_argument('--save-json', '-j', dest='json', action="store_true", default=False, help='Saves a JSON file of the reviews dictionary')
parser.add_argument('--save-html', '-w', dest='html', action="store_true", default=False, help='Saves an HTML document for easily viewing reviews')
parser.add_argument('--browser-open', '-b', dest='browserOpen', action="store_true", default=False, help='Opens saved HTML document in the browser')
parser.add_argument('--search', '-s', nargs='+', dest='search', default=())
args = parser.parse_args()

console = Console()
pretty.install()

def moviesOnSinglePage(url):
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    divs = soup.find_all("div", {'class': "poster film-poster really-lazy-load"})
    movieList = []
    for div in divs:
        findMovie = str(div).split('"')
        movie = [i.split('/film/')[1].replace('/', '') for i in findMovie if i.startswith('/film/')]
        movieList.append(movie[0])

    return movieList

def allUserMovies(user, base):
    page = 1
    totalMoviesList = []
    while True:
        url = f'{base}{page}'
        movies = moviesOnSinglePage(url)
        if len(movies) == 0:

            break
        for movie in movies:
            totalMoviesList.append(movie)
        page+=1

    return totalMoviesList


# Make a list of the pages of reviews. (Ex. /user/films/reviews/page/1 ... /user/films/reviews/page/5)
# Can use the previews of the reviews (before clicking more) to get review text for multiple movies.
# Doing it like this is faster than requesting each review individually even with the string manipulation needed.
def getReviewUrls(user):
    reviewsBaseUrl = f'https://letterboxd.com/{user}/films/reviews/'
    html_text = requests.get(reviewsBaseUrl).text
    soup = BeautifulSoup(html_text, 'html.parser')
    pageDiv = str(soup.find("div", {'class': "pagination"}))
    try:
        lastValidPage = int(pageDiv.split('/films/reviews/page/')[-1][0])
        return [f'{reviewsBaseUrl}page/{str(i)}' for i in range(1, lastValidPage + 1)]

    except ValueError:
        return [reviewsBaseUrl]


def getSingleReview(url=''):
    for possibleUrl in (url, url + '/1/'): # super-8 review had a an extra /1/ on the end
        soup = BeautifulSoup(requests.get(possibleUrl).text, 'html.parser')
        reviewDivHtmlStr = str(soup.find("div", {'class': "review body-text -prose -hero -loose"}))
        if not reviewDivHtmlStr  == 'None':
            return '<p>' + reviewDivHtmlStr.split('<div><p>')[-1].replace('</div>', '')

def getReviews(user):
    movieDelim = f'[red]{"=" * 80}'
    console.print(movieDelim)

    reviewUrls = getReviewUrls(user)

    reviewsText = {}
    for url in reviewUrls:
        lines = requests.get(url).text.splitlines()
        strippedLines = [line.strip() for line in lines]

        for line in strippedLines:
            if line[0:24] == '<li class="film-detail">':
                movie = line.split('data-film-slug="/film/')[1].split('/')[0]

                if args.search:
                    if not movie in args.search:
                        continue

                console.print(f'[cyan]movie: [bold blue]{movie}')
                reviewPreview = '<p>' + ''.join(line.split('<p>')[1:]).split(' </div>')[0]

                #If the full review text is in the preview, don't bother requesting another page.
                if not reviewPreview[-5] == '…':  #NOT THREE PERIODS - DIFFERENT UNICODE CHAR
                    console.print('\t[blue]Preview contains full review')
                    console.print('\t[blue]No need to request individual page')
                    console.print(movieDelim)

                    reviewsText[movie] = reviewPreview
                else:
                    movieReviewUrl = f'https://letterboxd.com/{user}/film/{movie}/'
                    console.print('\t[magenta]Preview contains partial review')
                    console.print(f'\t[magenta]Requesting: {movieReviewUrl}')
                    console.print(movieDelim)

                    reviewsText[movie] = getSingleReview(url=movieReviewUrl)
                    #sleep(.05)

    return reviewsText


def writeReviews(reviewsDict={}):
    user = reviewsDict['user']
    if not args.search:
        fname = f'{user}_all_reviews.html'

    else:
        fname = f'{user}_searched_reviews.html'
    rprint(f'html={fname}')

    with open(fname, 'w+') as f:
        f.write('<!DOCTYPE html>\n')
        f.write('<head>\n')
        f.write('</head>\n')
        f.write('<html>\n')
        f.write('<body>\n')

        f.write(f'<h1>{user} - letterboxd.com reviews </h1>\n<br>')

        for i, (movie, review) in enumerate(reviewsDict['reviews'].items()):
            htmlMovieTitle = movie.replace('-', ' ').title()
            f.write(f'<b>{i + 1}: {htmlMovieTitle}</b>\n<br>')
            f.write(f'{review}\n<br>')

        f.write('</body>\n')
        f.write('</html>\n')

    if args.browserOpen:
        from webbrowser import open_new_tab
        open_new_tab(fname)


def letterboxdRun(args):
    user = args.user
    baseUrl = f'https://letterboxd.com/{user}/films/'

    if args.reviews:
        fname = f'{user}_reviews.json'

        reviewsText = getReviews(user)

        outputDict = {'user': user, 'reviews': reviewsText}

        if args.html:
            writeReviews(outputDict)

        if args.json:
            rprint(f'json={fname}')
            jsonStr = json.dumps(outputDict, indent = 3)
            with open(fname, 'w+') as f:
                f.write(jsonStr)



def main():
    #argsDict = vars(args)
    console.print('[cyan]*Command line arguments* ')
    #rprint(f'\t{args}')
    #console.print('[blue]{')
    for k,v in vars(args).items():
        rprint(f'\t{k}={v}')
    print()

    console.print('[cyan]--Making requests to letterboxd.com--\n[red]This may take some time depending on how many reviews there are.\n')


    letterboxdRun(args)


if __name__ == '__main__':
    main()
