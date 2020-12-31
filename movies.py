#!/bin/env python3

'''
Letterboxd does not really have an API.
Test account:
    testfitzy1293
'''



import requests
import sys
import re
from bs4 import BeautifulSoup
from pprint import pprint
import json
from time import time
from time import sleep, time

# =======================================================================================================================================================================
# Global stuff (argparse stuff and rich console constructor).
# CL args and the console object from rich should be globals.
# Don't bother constructing console objects in every function.

import argparse
parser = argparse.ArgumentParser(description='letterboxd args')
parser.add_argument('--user', '-u', dest='user', help='letterboxd.com user')
parser.add_argument('--reviews', '-r', dest='reviews', action="store_true", default=False, help='Gets reviews')
parser.add_argument('--testing', '-t', dest='testing', action='store_true', default=False, help='Testing flag - for development only')
parser.add_argument('--save-json', '-j', dest='json', action="store_true", default=False, help='Saves a JSON file of the reviews dictionary')
parser.add_argument('--save-html', '-w', dest='html', action="store_true", default=False, help='Saves an HTML document for easily viewing reviews')
parser.add_argument('--browser-open', '-b', dest='browserOpen', action="store_true", default=False, help='Opens saved HTML document in the browser')
parser.add_argument('--search', '-s', nargs='+', dest='search', default=())
args = parser.parse_args()


from rich.console import Console
from rich import print as rprint
console = Console()
# =======================================================================================================================================================================

# Make a list of the pages of reviews. (Ex. /user/films/reviews/page/1 ... /user/films/reviews/page/5)
# Can use the previews of the reviews (before clicking more) to get review text for multiple movies, if the review is short enough.
# Doing it like this is faster than requesting each review individually .

def getReviewUrls(user):
    reviewsBaseUrl = f'https://letterboxd.com/{user}/films/reviews/'
    html_text = requests.get(reviewsBaseUrl).text
    soup = BeautifulSoup(html_text, 'html.parser')
    pageDiv = str(soup.find("div", {'class': "pagination"}))
    sleep(.05)
    try:
        lastValidPage = int(pageDiv.split('/films/reviews/page/')[-1].split('/')[0])
        print(lastValidPage)
        return [f'{reviewsBaseUrl}page/{str(i)}' for i in range(1, lastValidPage + 1)]

    except ValueError:

        return [reviewsBaseUrl]


def getSingleReview(url=''):
    for possibleUrl in (url, url + '/1/'): # super-8 review had a an extra /1/ on the end
        soup = BeautifulSoup(requests.get(possibleUrl).text, 'html.parser')
        reviewDivHtmlStr = str(soup.find("div", {'class': "review body-text -prose -hero -loose"}))
        sleep(.05)
        if not reviewDivHtmlStr  == 'None':
            return '<p>' + reviewDivHtmlStr.split('<div><p>')[-1].replace('</div>', '')



# Should probably make different functions for batch getting all movies and searching.
# Because args.search should only be checked once, not every time there's another movie review.
# But it was too easy to just throw that in and add a continue

def getReviews(user):
    movieDelim = f'[red]{"=" * 80}'
    look = f'/{user}/film/'
    reviewsText = {}

    if args.search:
        console.print(movieDelim)
        for url in [f'https://letterboxd.com/{user}/film/{movie}/' for movie in args.search]:
            movie = url.split('/film/')[-1][:-1]
            console.print(f'[cyan]movie: [bold blue]{movie}')
            console.print(f'\t[green]Searching')
            console.print(f'\t[green]Requesting: {url}')
            console.print(movieDelim)

            reviewsText[movie] = getSingleReview(url=url)
        return reviewsText



    reviewUrls = getReviewUrls(user)
    console.print('[cyan] Urls with multiple reviews')
    rprint(reviewUrls)
    print()

    console.print(movieDelim)
    for url in reviewUrls:
        console.print(f'[cyan]Requesting: [bold blue]{url}')
        start = time()
        response = requests.get(url)
        rprint(f'reponseTime={time() - start}')
        console.print(movieDelim)
        htmlText = response.text

        valuableStart = htmlText.find('<ul class="poster-list -p70 film-list clear film-details-list no-title">')
        valuableEnd = htmlText.find('</section>', valuableStart)
        smallStr = htmlText[valuableStart:valuableEnd]

        for line in [line for line in smallStr.splitlines() if line.strip()[10:24] =='"film-detail">']:


            shorterLine = line[line.find('<p>'):]

            movieSearch = re.search( fr'{look}.*?/', shorterLine).group()
            movie = re.sub(fr'{look}','', str(movieSearch))[:-1]

            console.print(f'[cyan]movie: [bold blue]{movie}')
            reviewPreview = shorterLine[:shorterLine.find('</div>')].strip()

            if '…' == reviewPreview[-5]: #NOT THREE PERIODS - DIFFERENT UNICODE CHAR
                movieReviewUrl = f'https://letterboxd.com/{user}/film/{movie}/'
                console.print('\t[magenta]Preview contains partial review')
                console.print(f'\t[magenta]Requesting: {movieReviewUrl}')
                console.print(movieDelim)

                reviewsText[movie] = getSingleReview(url=movieReviewUrl)

            else:
                console.print('\t[blue]Preview contains full review')
                console.print('\t[blue]No need to request individual page')
                console.print(movieDelim)

                reviewsText[movie] = reviewPreview



            sleep(.05)

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
        f.write('<html>\n')
        f.write('<head>\n')
        f.write('</head>\n')
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


def letterboxdRun():
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
            jsonStr = json.dumps(outputDict, indent=3)
            with open(fname, 'w+') as f:
                f.write(jsonStr)


if __name__ == '__main__':
    console.print('[cyan]*Command line arguments* ')
    for k,v in vars(args).items():
        rprint(f'\t{k}={v}')
    print()

    console.print('[cyan]--Making requests to letterboxd.com--\n[red]This may take some time depending on how many reviews there are.\n')
    letterboxdRun()
