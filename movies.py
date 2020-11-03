#!/bin/env python3

'''
Letterboxd does not really have an API.
'''



import requests
import sys
from bs4 import BeautifulSoup
from pprint import pprint

def moviesOnPage(url):
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    divs = soup.find_all("div", {'class': "poster film-poster really-lazy-load"})

    movieList = []
    for div in divs:
        findMovie = str(div).split('"')
        movie = [i.split('/film/')[1].replace('/', '') for i in findMovie if i.startswith('/film/')]
        movieList.append(movie[0])

    return movieList

def allMovies(user, base):
    page = 1
    allMovies = []
    while True:
        url = f'{base}{page}'
        movies = moviesOnPage(url)
        if len(movies) == 0:
            break
        for i in movies:
            allMovies.append(i)
        page+=1

    return allMovies

def getReviews(user, reviewMovies):
    reviewUrls = [f'https://letterboxd.com/{user}/film/{i}' for i in reviewMovies]
    reviewsText = {}
    for url in reviewUrls:
        movie = url.split('/')[-1]
        html_text = requests.get(url).text
        soup = BeautifulSoup(html_text, 'html.parser')
        divs = soup.find_all("meta", {'name': "description"})
        for div in divs:
            findReview = str(div).split('"')[1]
            reviewsText[movie] = findReview

    return reviewsText

userDict = {}

user = sys.argv[1]
baseUrl = f'https://letterboxd.com/{user}/films/'
bases = (f'{baseUrl}page/', f'{baseUrl}reviews/page/')
watched = allMovies(user, bases[0])
reviewsList = allMovies(user, bases[1])

userDict['user'] = user
userDict['watched'] = watched

reviewsText = getReviews(user, reviewsList)


userDict['reviews'] = reviewsText

pprint(userDict)
