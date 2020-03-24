#!/usr/bin/env python
# -*- coding: utf8 -*-

import requests
import requests.sessions
import argparse
import getpass
import sys
import re
import os
import json
from .download import download, DLException
from ._version import __version__



class Session:
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:39.0) Gecko/20100101 Firefox/39.0',
               'X-Requested-With': 'XMLHttpRequest',
               'Host': 'www.udemy.com',
               'Referer': 'https://www.ucl.udemy.com/join/login-popup'}

    def __init__(self):
        self.session = requests.sessions.Session()
        
    def set_auth_headers(self, access_token, client_id):
        self.headers['X-Udemy-Bearer-Token'] = access_token
        self.headers['X-Udemy-Client-Id'] = client_id

    def get(self, url):
        return self.session.get(url, headers=self.headers)

    def post(self, url, data):
        return self.session.post(url, data, headers=self.headers)


session = Session()


def get_csrf_token():
    response = session.get('https://www.ucl.udemy.com/join/login-popup')
    match = re.search("name=\'csrfmiddlewaretoken\' value=\'(.*)\'", response.text)
    return match.group(1)

def login(username, password):
    login_url = 'https://www.ucl.udemy.com/join/login-popup/?displayType=ajax&display_type=popup&showSkipButton=1&returnUrlAfterLogin=https%3A%2F%2Fwww.udemy.com%2F&next=https%3A%2F%2Fwww.udemy.com%2F&locale=en_US'
    csrf_token = get_csrf_token()
    payload = {'isSubmitted': 1, 'email': username, 'password': password,
               'displayType': 'ajax', 'csrfmiddlewaretoken': csrf_token}
    response = session.post(login_url, payload)

    access_token = response.cookies.get('access_token')
    client_id = response.cookies.get('client_id')
    session.set_auth_headers(access_token, client_id)

    response = response.text
    if 'error' in response:
        print(response)
        sys.exit(1)


def get_course_id(course_link):
    response = session.get(course_link)
    matches = re.search('data-courseid="(\d+)"', response.text, re.IGNORECASE)
    return matches.groups()[0] if matches else None


def parse_video_url(lecture_id, hd=False):
    '''A hacky way to find the json used to initalize the swf object player'''
    embed_url = 'https://www.ucl.udemy.com/embed/{0}'.format(lecture_id)
    html = session.get(embed_url).text

    data = re.search(r'\$\("#player"\).jwplayer\((.*?)\);.*</script>', html,
                     re.MULTILINE | re.DOTALL).group(1)
    video = json.loads(data)

    if 'playlist' in video and 'sources' in video['playlist'][0]:
        if hd:
            for source in video['playlist'][0]['sources']:
                if '720' in source['label'] or 'HD' in source['label']:
                    return source['file']

        # The 360p case and fallback if no HD version
        source = video['playlist'][0]['sources'][0]
        return source['file']
    else:
        print("Failed to parse video url")
        return None


def get_video_links(course_id, lecture_start, lecture_end, hd=False):
    course_url = 'https://www.ucl.udemy.com/api-1.1/courses/{0}/curriculum?fields[lecture]=@min,completionRatio,progressStatus&fields[quiz]=@min,completionRatio'.format(course_id)
    course_data = session.get(course_url).json()

    chapter = None
    video_list = []

    lecture_number = 1
    chapter_number = 0
    # A udemy course has chapters, each having one or more lectures
    for item in course_data:
        if item['__class'] == 'chapter':
            chapter = item['title']
            chapter_number += 1
        elif item['__class'] == 'lecture' and item['assetType'] == 'Video':
            lecture = item['title']
            if valid_lecture(lecture_number, lecture_start, lecture_end):
                try:
                    lecture_id = item['id']
                    video_url = parse_video_url(lecture_id, hd)
                    video_list.append({'chapter': chapter,
                                       'lecture': lecture,
                                       'video_url': video_url,
                                       'lecture_number': lecture_number,
                                       'chapter_number': chapter_number})
                except:
                    print('Cannot download lecture "%s"' % (lecture))
            lecture_number += 1
    return video_list


def valid_lecture(lecture_number, lecture_start, lecture_end):
    if lecture_start and lecture_end:
        return lecture_start <= lecture_number <= lecture_end
    elif lecture_start:
        return lecture_start <= lecture_number
    else:
        return lecture_number <= lecture_end


def sanitize_path(s):
    return "".join([c for c in s if c.isalpha() or c.isdigit() or c in ' .-_,']).rstrip()


def mkdir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_video(directory, filename, link):
    print('Downloading %s  ' % (filename.encode('utf-8')))
    previous_dir = os.getcwd()
    mkdir(directory)
    os.chdir(directory)
    try:
        download(link, filename)
    except DLException as e:
        print('Couldn\'t download this lecture: {0}'.format(e))
    os.chdir(previous_dir)
    print('\n'),

def udemy_dl(username, password, course_link, lecture_start, lecture_end, dest_dir=""):
    login(username, password)

    course_id = get_course_id(course_link)
    if not course_id:
        print('Failed to get course ID')
        return

    for video in get_video_links(course_id, lecture_start, lecture_end, hd=True):
        directory = '%02d %s' % (video['chapter_number'], video['chapter'])
        directory = sanitize_path(directory)

        if dest_dir:
            directory = os.path.join(dest_dir, directory)

        filename = '%03d %s.mp4' % (video['lecture_number'], video['lecture'])
        filename = sanitize_path(filename)

        get_video(directory, filename, video['video_url'])

    session.get('http://www.ucl.udemy.com/user/logout')


def is_integer(p):
    try:
        int(p)
        return True
    except ValueError:
        return False

def main():
    parser = argparse.ArgumentParser(description='Fetch all the videos for a udemy course')
    parser.add_argument('link', help='Link for udemy course', action='store')
    parser.add_argument('-u', '--username', help='Username/Email', default=None, action='store')
    parser.add_argument('-p', '--password', help='Password', default=None, action='store')
    parser.add_argument('--lecture-start', help='Lecture to start at (default is 1)', default=1, action='store')
    parser.add_argument('--lecture-end', help='Lecture to end at (default is last)', default=None, action='store')
    parser.add_argument('-o', '--output-dir', help='Output directory', default=None, action='store')
    parser.add_argument('-v', '--version', help='Display the version of udemy-dl and exit', action='version', version='%(prog)s {version}'.format(version=__version__))

    args = vars(parser.parse_args())

    username = args['username']
    password = args['password']
    link = args['link'].rstrip('/')
    lecture_start = args['lecture_start']
    lecture_end = args['lecture_end']

    if lecture_start is not None:
        if not is_integer(lecture_start) or int(lecture_start) <= 0:
            print('--lecture_start requires natural number argument')
            sys.exit(1)
        lecture_start = int(lecture_start)
    if lecture_end is not None:
        if not is_integer(lecture_end) or int(lecture_end) <= 0:
            print('--lecture_end requires natural number argument')
            sys.exit(1)
        lecture_end = int(lecture_end)
    
    if args['output_dir']:
        # Normalize the output path if specified
        output_dir = os.path.normpath(args['output_dir'])
    else:
        # Get output dir name from the URL
        output_dir = os.path.join(".", link.rsplit('/', 1)[1])

    if not username:
        try:
            username = raw_input("Username/Email: ")  # Python 2
        except NameError:
            username = input("Username/Email: ")  # Python 3

    if not password:
        password = getpass.getpass(prompt='Password: ')

    print('Downloading to: %s\n' % (os.path.abspath(output_dir)))

    udemy_dl(username, password, link, lecture_start, lecture_end, output_dir)


if __name__ == '__main__':
    main()
